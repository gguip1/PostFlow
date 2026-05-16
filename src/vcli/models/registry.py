from pydantic import BaseModel, Field


class RegistryEntry(BaseModel):
    slug: str
    velog_id: str | None = None
    url: str | None = None
    last_synced_hash: str | None = None
    last_synced_at: str | None = None


class Registry(BaseModel):
    version: int = 1
    posts: list[RegistryEntry] = Field(default_factory=list)
