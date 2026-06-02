import re

from pydantic import BaseModel, field_serializer, field_validator

from app.constants import CounterpartyType
from app.utils.ids import unscope_user_id

_INN_RE = re.compile(r"^\d{10}(\d{2})?$")
_KPP_RE = re.compile(r"^\d{9}$")


def _validate_inn(value: str | None) -> str | None:
    if value is not None and not _INN_RE.match(value):
        raise ValueError("ИНН должен содержать 10 или 12 цифр")
    return value


def _validate_kpp(value: str | None) -> str | None:
    if value is not None and not _KPP_RE.match(value):
        raise ValueError("КПП должен содержать 9 цифр")
    return value


class CounterpartyCreate(BaseModel):
    name: str
    type: CounterpartyType = CounterpartyType.STORE
    inn: str | None = None
    kpp: str | None = None

    @field_validator("inn")
    @classmethod
    def validate_inn(cls, v: str | None) -> str | None:
        return _validate_inn(v)

    @field_validator("kpp")
    @classmethod
    def validate_kpp(cls, v: str | None) -> str | None:
        return _validate_kpp(v)


class CounterpartyUpdate(BaseModel):
    name: str | None = None
    type: CounterpartyType | None = None
    inn: str | None = None
    kpp: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str:
        if v is None or not v.strip():
            raise ValueError("name не может быть пустым или null")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: CounterpartyType | None) -> CounterpartyType:
        if v is None:
            raise ValueError("type не может быть null")
        return v

    @field_validator("inn")
    @classmethod
    def validate_inn(cls, v: str | None) -> str | None:
        return _validate_inn(v)

    @field_validator("kpp")
    @classmethod
    def validate_kpp(cls, v: str | None) -> str | None:
        return _validate_kpp(v)


class CounterpartyRead(BaseModel):
    id: str
    name: str
    type: str
    inn: str | None
    kpp: str | None

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, value: str) -> str:
        return unscope_user_id(value) or value
