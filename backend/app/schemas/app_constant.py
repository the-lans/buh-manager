from pydantic import BaseModel


class AppConstantRead(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


class AppConstantUpdate(BaseModel):
    value: str
