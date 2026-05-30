from typing import TypeVar

from fastapi import HTTPException, status

T = TypeVar("T")


def get_or_404[T](obj: T | None, detail: str = "Not found.") -> T:
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return obj
