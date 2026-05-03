from pydantic import BaseModel


class CounterpartyCreate(BaseModel):
    name: str
    type: str = "STORE"


class CounterpartyRead(BaseModel):
    id: str
    name: str
    type: str

    model_config = {"from_attributes": True}
