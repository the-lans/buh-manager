from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> None:
        self.skip = skip
        self.limit = limit
