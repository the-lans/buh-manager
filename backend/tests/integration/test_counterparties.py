from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.models.counterparty import Counterparty
from app.models.user import User
from app.utils.ids import scope_user_id


def _cp_payload(
    name: str = "Магазин Тест",
    type_: str = "STORE",
    inn: str | None = None,
    kpp: str | None = None,
) -> dict:
    data: dict = {"name": name, "type": type_}
    if inn is not None:
        data["inn"] = inn
    if kpp is not None:
        data["kpp"] = kpp
    return data


@pytest.mark.asyncio
async def test_list_counterparties_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get("/api/v1/counterparties", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_counterparty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="ООО Ромашка", inn="1234567890", kpp="123456789"),  # noqa: RUF001
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "ООО Ромашка"  # noqa: RUF001
    assert data["inn"] == "1234567890"
    assert data["kpp"] == "123456789"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_counterparty_without_inn(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="Ларёк"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["inn"] is None
    assert data["kpp"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("inn", "kpp"),
    [
        ("123", None),  # INN слишком короткий
        ("12345678901234", None),  # INN слишком длинный
        ("12345678ab", None),  # INN не цифры
        (None, "12345"),  # KPP слишком короткий
        (None, "1234567890"),  # KPP слишком длинный
    ],
)
async def test_create_counterparty_invalid_inn_kpp(
    client: AsyncClient,
    auth_headers: dict[str, str],
    inn: str | None,
    kpp: str | None,
) -> None:
    resp = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(inn=inn, kpp=kpp),
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_counterparty_duplicate_inn_returns_existing(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    first = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="Первый", inn="1234567890"),
        headers=auth_headers,
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="Второй", inn="1234567890"),
        headers=auth_headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first_id


@pytest.mark.asyncio
async def test_update_counterparty(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="Старое имя"),
        headers=auth_headers,
    )
    assert create.status_code == 201
    cp_id = create.json()["id"]

    resp = await client.put(
        f"/api/v1/counterparties/{cp_id}",
        json={"name": "Новое имя", "inn": "123456789012"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Новое имя"
    assert data["inn"] == "123456789012"


@pytest.mark.asyncio
async def test_update_counterparty_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.put(
        "/api/v1/counterparties/nonexistent-slug",
        json={"name": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_counterparty(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session: Session,
    test_user: User,
) -> None:
    create = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="Удалить меня"),
        headers=auth_headers,
    )
    assert create.status_code == 201
    cp_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/counterparties/{cp_id}", headers=auth_headers)
    assert resp.status_code == 204

    stored = session.exec(
        select(Counterparty).where(
            Counterparty.id == scope_user_id(user_id=test_user.id, public_id=cp_id)
        )
    ).first()
    assert stored is None


@pytest.mark.asyncio
async def test_delete_counterparty_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.delete(
        "/api/v1/counterparties/nonexistent-slug",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_counterparties_returns_all(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    for name in ("Альфа", "Бета", "Гамма"):
        await client.post(
            "/api/v1/counterparties",
            json=_cp_payload(name=name),
            headers=auth_headers,
        )

    resp = await client.get("/api/v1/counterparties", headers=auth_headers)
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert {"Альфа", "Бета", "Гамма"} <= names


@pytest.mark.asyncio
async def test_delete_counterparty_used_in_receipt_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    cp = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name="Привязанный магазин"),
        headers=auth_headers,
    )
    cp_id = cp.json()["id"]

    fn = str(uuid4().int)[:10]
    fd = str(uuid4().int)[:6]
    fpd = str(uuid4().int)[:10]
    await client.post(
        "/api/v1/receipts",
        json={
            "paid_at": "2024-05-01T10:00:00",
            "total_amount": 500.0,
            "fn": fn,
            "fd": fd,
            "fpd": fpd,
            "counterparty_id": cp_id,
            "items": [{"name": "Товар", "quantity": "1", "price": "500", "amount": "500"}],
        },
        headers=auth_headers,
    )

    resp = await client.delete(f"/api/v1/counterparties/{cp_id}", headers=auth_headers)
    assert resp.status_code == 409
    assert "чеках" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_counterparty_used_in_transaction_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    cp_name = "Транзакционный контрагент"
    cp = await client.post(
        "/api/v1/counterparties",
        json=_cp_payload(name=cp_name),
        headers=auth_headers,
    )
    cp_id = cp.json()["id"]

    # Create an account
    acc_resp = await client.post(
        "/api/v1/accounts",
        json={"bank": "TestBank", "account_number": "40817810000099999999"},
        headers=auth_headers,
    )
    acc_id = acc_resp.json()["id"]

    # Create transaction referencing the counterparty via name (counterparty_name triggers find-or-create)
    tx_resp = await client.post(
        "/api/v1/transactions",
        json={
            "account_id": acc_id,
            "occurred_at": "2024-05-01T10:00:00",
            "amount": -100.0,
            "type": "EXPENSE",
            "counterparty_name": cp_name,
        },
        headers=auth_headers,
    )
    assert tx_resp.status_code == 201
    assert tx_resp.json()["counterparty_id"] == cp_id

    resp = await client.delete(f"/api/v1/counterparties/{cp_id}", headers=auth_headers)
    assert resp.status_code == 409
    assert "транзакциях" in resp.json()["detail"]
