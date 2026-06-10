"""Model for entity path list."""
from pydantic import validator
from ayon_server.types import OPModel, Field

class ResolvedPair(OPModel):
    """Model for entity path list."""
    uri: str = Field(
        ...,
        title="Entity URI",
        description="Entity URI",
        example="ayon+entity://Project/assets/foo?product=modelMain&version=v002&representation=usd"  # noqa: E501
    )
    path: str = Field(
        ...,
        title="Resolved path",)

class EntityPathList(OPModel):
    """Model for entity path list."""
    path_list: list[ResolvedPair] = Field(...)
