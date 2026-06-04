import json
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, col, select

from app.models.reconciliation_report import ReconciliationReportRecord


def save_report(
    *,
    session: Session,
    user_id: UUID,
    report_data: dict[str, Any],
) -> ReconciliationReportRecord:
    record = ReconciliationReportRecord(
        user_id=user_id,
        report_json=json.dumps(report_data, default=str),
    )
    session.add(record)
    session.flush()
    session.refresh(record)
    return record


def get_last_report(
    *,
    session: Session,
    user_id: UUID,
) -> dict[str, Any] | None:
    record = session.exec(
        select(ReconciliationReportRecord)
        .where(ReconciliationReportRecord.user_id == user_id)
        .order_by(col(ReconciliationReportRecord.generated_at).desc())
    ).first()
    if record is None:
        return None
    return cast("dict[str, Any]", json.loads(record.report_json))
