"""Offset/limit pagination helpers with hard caps."""
from __future__ import annotations

from fastapi import Query
from pydantic import BaseModel, Field


class PageParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


def page_params(limit: int = Query(default=20, ge=1, le=100),
                offset: int = Query(default=0, ge=0)) -> PageParams:
    return PageParams(limit=limit, offset=offset)
