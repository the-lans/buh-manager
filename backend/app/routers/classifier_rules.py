from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlmodel import Session

from app.constants import ApiKeyScope, AuditEntityType, ChangedBy
from app.database import get_session
from app.db.accounts import get_account_by_id
from app.db.classifier_rules import (
    create_rule,
    delete_rule,
    get_rule_by_id,
    list_rules_for_user,
    update_rule,
)
from app.db.expense_types import get_expense_type_by_id
from app.db.transactions import get_transactions_for_user
from app.dependencies.auth import get_current_user, require_scope
from app.models.classifier_rule import ClassifierRule
from app.models.user import User
from app.schemas.classifier_rule import (
    ClassifierRuleApplyRequest,
    ClassifierRuleApplyResult,
    ClassifierRuleCreate,
    ClassifierRuleRead,
    ClassifierRuleUpdate,
    has_at_least_one_condition,
)
from app.schemas.transaction import TransactionFilters
from app.services.audit import audit_create, audit_delete, audit_update
from app.services.classifier import apply_rules, generate_representation
from app.utils.http import get_or_404

router = APIRouter(prefix="/classifier-rules", tags=["classifier-rules"])

_APPLY_BATCH_SIZE = 1_000


def _resolve_representation(
    data: ClassifierRuleCreate | ClassifierRuleUpdate,
    session: Session,
    user_id: UUID,
) -> str:
    account_label: str | None = None
    if data.cond_account_id is not None:
        account = get_account_by_id(session=session, account_id=data.cond_account_id, user_id=user_id)
        if account:
            account_label = f"{account.bank} ***{account.account_number[-4:]}"
    return generate_representation(
        cond_account_id=data.cond_account_id,
        account_label=account_label,
        cond_day_month=data.cond_day_month,
        cond_day_month_op=data.cond_day_month_op,
        cond_day_week=data.cond_day_week,
        cond_amount=data.cond_amount,
        cond_amount_op=data.cond_amount_op,
        cond_type=data.cond_type,
        cond_bank_category=data.cond_bank_category,
        cond_description=data.cond_description,
    )


def _merge_rule_update(rule: ClassifierRule, data: ClassifierRuleUpdate) -> ClassifierRuleUpdate:
    update_data = data.model_dump(exclude_unset=True)
    return ClassifierRuleUpdate(
        cond_account_id=update_data.get("cond_account_id", rule.cond_account_id),
        cond_day_month=update_data.get("cond_day_month", rule.cond_day_month),
        cond_day_month_op=update_data.get("cond_day_month_op", rule.cond_day_month_op),
        cond_day_week=update_data.get("cond_day_week", rule.cond_day_week),
        cond_amount=update_data.get("cond_amount", rule.cond_amount),
        cond_amount_op=update_data.get("cond_amount_op", rule.cond_amount_op),
        cond_type=update_data.get("cond_type", rule.cond_type),
        cond_bank_category=update_data.get("cond_bank_category", rule.cond_bank_category),
        cond_description=update_data.get("cond_description", rule.cond_description),
    )


def _ensure_rule_account_belongs_to_user(
    *,
    session: Session,
    user_id: UUID,
    cond_account_id: UUID | None,
) -> None:
    if cond_account_id is None:
        return
    account = get_account_by_id(session=session, account_id=cond_account_id, user_id=user_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )


@router.get(
    "",
    response_model=list[ClassifierRuleRead],
    dependencies=[Depends(require_scope(ApiKeyScope.READ_CLASSIFIER_RULES))],
)
def list_classifier_rules(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ClassifierRuleRead]:
    rules = list_rules_for_user(session=session, user_id=current_user.id)
    return [ClassifierRuleRead.model_validate(r) for r in rules]


@router.post(
    "",
    response_model=ClassifierRuleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_CLASSIFIER_RULES))],
)
def create_classifier_rule(
    data: ClassifierRuleCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ClassifierRuleRead:
    et = get_or_404(
        get_expense_type_by_id(session=session, expense_type_id=data.expense_type_id, user_id=current_user.id),
        "Expense type not found.",
    )
    data = data.model_copy(update={"expense_type_id": et.id})
    _ensure_rule_account_belongs_to_user(
        session=session,
        user_id=current_user.id,
        cond_account_id=data.cond_account_id,
    )
    representation = _resolve_representation(data, session, current_user.id)
    rule = create_rule(session=session, user_id=current_user.id, data=data, representation=representation)
    audit_create(
        session=session,
        entity_type=AuditEntityType.CLASSIFIER_RULE,
        entity_id=rule.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        after={"name": rule.name, "priority": rule.priority},
    )
    session.commit()
    session.refresh(rule)
    return ClassifierRuleRead.model_validate(rule)


@router.put(
    "/{rule_id}",
    response_model=ClassifierRuleRead,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_CLASSIFIER_RULES))],
)
def update_classifier_rule(
    rule_id: UUID,
    data: ClassifierRuleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ClassifierRuleRead:
    rule = get_or_404(
        get_rule_by_id(session=session, rule_id=rule_id, user_id=current_user.id),
        "Classifier rule not found.",
    )
    if data.expense_type_id is not None:
        et = get_or_404(
            get_expense_type_by_id(session=session, expense_type_id=data.expense_type_id, user_id=current_user.id),
            "Expense type not found.",
        )
        data = data.model_copy(update={"expense_type_id": et.id})
    try:
        effective_conditions = _merge_rule_update(rule, data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    if not has_at_least_one_condition(
        effective_conditions.cond_account_id,
        effective_conditions.cond_day_month,
        effective_conditions.cond_day_week,
        effective_conditions.cond_amount,
        effective_conditions.cond_type,
        effective_conditions.cond_bank_category,
        effective_conditions.cond_description,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Необходимо указать хотя бы одно условие.",
        )
    _ensure_rule_account_belongs_to_user(
        session=session,
        user_id=current_user.id,
        cond_account_id=effective_conditions.cond_account_id,
    )
    representation = _resolve_representation(effective_conditions, session, current_user.id)
    before = {"name": rule.name, "priority": rule.priority}
    rule = update_rule(session=session, rule=rule, data=data, representation=representation)
    audit_update(
        session=session,
        entity_type=AuditEntityType.CLASSIFIER_RULE,
        entity_id=rule.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before=before,
        after={"name": rule.name, "priority": rule.priority},
    )
    session.commit()
    return ClassifierRuleRead.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_CLASSIFIER_RULES))],
)
def delete_classifier_rule(
    rule_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    rule = get_or_404(
        get_rule_by_id(session=session, rule_id=rule_id, user_id=current_user.id),
        "Classifier rule not found.",
    )
    audit_delete(
        session=session,
        entity_type=AuditEntityType.CLASSIFIER_RULE,
        entity_id=rule.id,
        changed_by=ChangedBy.USER,
        user_id=current_user.id,
        before={"name": rule.name, "priority": rule.priority},
    )
    delete_rule(session=session, rule=rule)
    session.commit()


@router.post(
    "/apply",
    response_model=ClassifierRuleApplyResult,
    dependencies=[Depends(require_scope(ApiKeyScope.WRITE_CLASSIFIER_RULES))],
)
def apply_classifier_rules(
    data: ClassifierRuleApplyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ClassifierRuleApplyResult:
    rules = list_rules_for_user(session=session, user_id=current_user.id)
    active_rules = [r for r in rules if r.is_active]

    filters = TransactionFilters(
        start_date=data.start_date,
        end_date=data.end_date,
        account_id=None,
        type=None,
        reconciled_status=None,
        import_status=None,
    )
    updated_count = 0
    offset = 0
    while True:
        transactions = get_transactions_for_user(
            session=session,
            user_id=current_user.id,
            filters=filters,
            skip=offset,
            limit=_APPLY_BATCH_SIZE,
        )
        if not transactions:
            break

        for tx in transactions:
            matched_et_id = apply_rules(active_rules, tx)
            if matched_et_id is not None and matched_et_id != tx.expense_type_id:
                tx.expense_type_id = matched_et_id
                session.add(tx)
                updated_count += 1

        offset += len(transactions)

    session.commit()
    return ClassifierRuleApplyResult(updated_count=updated_count)
