from uuid import UUID

ID_SCOPE_SEPARATOR = ":"


def scope_user_id(*, user_id: UUID, public_id: str) -> str:
    return f"{user_id}{ID_SCOPE_SEPARATOR}{public_id}"


def unscope_user_id(scoped_id: str | None) -> str | None:
    if scoped_id is None:
        return None
    if ID_SCOPE_SEPARATOR not in scoped_id:
        return scoped_id
    _, public_id = scoped_id.split(ID_SCOPE_SEPARATOR, 1)
    return public_id
