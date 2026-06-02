from uuid import UUID

from sqlmodel import Session, desc, select

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
    session.commit()
    session.refresh(rate)
    return rate


def get_latest_rates(*, session: Session, user_id: UUID) -> list[ExchangeRate]:
    all_rates = session.exec(
        select(ExchangeRate)
        .where(ExchangeRate.user_id == user_id)
        .order_by(desc(ExchangeRate.recorded_at))
    ).all()

    # Keep only the latest record per currency pair
    seen: set[tuple[str, str]] = set()
    result: list[ExchangeRate] = []
    for rate in all_rates:
        key = (rate.base_currency, rate.quote_currency)
        if key not in seen:
            seen.add(key)
            result.append(rate)
    return result
