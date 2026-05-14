"""Shared schemas: pagination, error responses."""
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    size: int = 20


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: str | None = None
