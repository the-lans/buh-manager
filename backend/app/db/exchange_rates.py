from uuid import UUID

from sqlalchemy import and_, func
from sqlmodel import Session, select

from app.models.exchange_rate import ExchangeRate
from app.schemas.exchange_rate import ExchangeRateCreate
from app.utils.dt import utcnow


def create_exchange_rate(
    *, session: Session, user_id: UUID, data: ExchangeRateCreate
) -> ExchangeRate:
    rate = ExchangeRate(
        user_id=user_id,
        base_currency=data.base_currency,
        quote_currency=data.quote_currency,
        rate=data.rate,
        recorded_at=data.recorded_at or utcnow(),
    )
    session.add(rate)
    session.flush()
    session.refresh(rate)
    return rate


def get_latest_rates(*, session: Session, user_id: UUID) -> list[ExchangeRate]:
    """Return the single most recent exchange rate record for each currency pair."""
    latest_per_pair = (
        select(
            ExchangeRate.base_currency,
            ExchangeRate.quote_currency,
            func.max(ExchangeRate.recorded_at).label("max_at"),
        )
        .where(ExchangeRate.user_id == user_id)
        .group_by(ExchangeRate.base_currency, ExchangeRate.quote_currency)
        .subquery()
    )
    return list(
        session.exec(
            select(ExchangeRate)
            .join(
                latest_per_pair,
                and_(
                    ExchangeRate.base_currency == latest_per_pair.c.base_currency,  # type: ignore[arg-type]
                    ExchangeRate.quote_currency == latest_per_pair.c.quote_currency,  # type: ignore[arg-type]
                    ExchangeRate.recorded_at == latest_per_pair.c.max_at,  # type: ignore[arg-type]
                ),
            )
            .where(ExchangeRate.user_id == user_id)
        ).all()
    )
