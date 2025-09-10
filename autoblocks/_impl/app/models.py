"""App models for Autoblocks API."""

from pydantic import BaseModel
from pydantic import ConfigDict


class App(BaseModel):
    """App model representing an application."""

    id: str
    name: str
    slug: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")
