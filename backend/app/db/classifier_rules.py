from uuid import UUID

from sqlmodel import Session, col, select

from app.models.classifier_rule import ClassifierRule
from app.schemas.classifier_rule import ClassifierRuleCreate, ClassifierRuleUpdate


def list_rules_for_user(*, session: Session, user_id: UUID) -> list[ClassifierRule]:
    return list(
        session.exec(
            select(ClassifierRule)
            .where(ClassifierRule.user_id == user_id)
            .order_by(col(ClassifierRule.priority).asc())
            .order_by(col(ClassifierRule.id).asc())
        ).all()
    )


def get_rule_by_id(*, session: Session, rule_id: UUID, user_id: UUID) -> ClassifierRule | None:
    return session.exec(
        select(ClassifierRule)
        .where(ClassifierRule.id == rule_id)
        .where(ClassifierRule.user_id == user_id)
    ).first()


def create_rule(
    *,
    session: Session,
    user_id: UUID,
    data: ClassifierRuleCreate,
    representation: str,
) -> ClassifierRule:
    rule = ClassifierRule(
        user_id=user_id,
        name=data.name,
        expense_type_id=data.expense_type_id,
        priority=data.priority,
        is_active=data.is_active,
        representation=representation,
        cond_account_id=data.cond_account_id,
        cond_day_month=data.cond_day_month,
        cond_day_month_op=data.cond_day_month_op,
        cond_day_month_to=data.cond_day_month_to,
        cond_day_week=data.cond_day_week,
        cond_amount=data.cond_amount,
        cond_amount_op=data.cond_amount_op,
        cond_amount_to=data.cond_amount_to,
        cond_type=data.cond_type,
        cond_bank_category=data.cond_bank_category,
        cond_description=data.cond_description,
    )
    session.add(rule)
    session.flush()
    session.refresh(rule)
    return rule


def update_rule(
    *,
    session: Session,
    rule: ClassifierRule,
    data: ClassifierRuleUpdate,
    representation: str,
) -> ClassifierRule:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.representation = representation
    session.add(rule)
    session.flush()
    session.refresh(rule)
    return rule


def delete_rule(*, session: Session, rule: ClassifierRule) -> None:
    session.delete(rule)
    session.flush()
