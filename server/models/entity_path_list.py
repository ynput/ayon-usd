"""Model for entity path list."""
from ayon_server.types import Field, OPModel


class ResolvedPair(OPModel):
    """Model for entity path list."""
    uri: str = Field(
        ...,
        title="Entity URI",
        description="Entity URI",
        example="ayon+entity://Project/assets/foo?product=modelMain&version=v002&representation=usd"
    )
    path: str = Field(
        ...,
        title="Resolved path")


class EntityPathList(OPModel):
    """Model for entity path list."""
    path_list: list[ResolvedPair] = Field(...)
