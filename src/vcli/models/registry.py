from datetime import datetime

from pydantic import BaseModel, Field

from vcli.models.meta import PostStatus, Visibility


class ProviderInfo(BaseModel):
    name: str
    post_id: str | None = None
    url: str | None = None


class RegistryEntry(BaseModel):
    slug: str
    velog_id: str | None = None
    url: str | None = None
    last_synced_hash: str | None = None
    last_synced_at: str | None = None
    id: str | None = Field(default=None, exclude=True)
    directory: str | None = Field(default=None, exclude=True)
    title: str | None = Field(default=None, exclude=True)
    status: PostStatus | None = Field(default=None, exclude=True)
    visibility: Visibility | None = Field(default=None, exclude=True)
    series: str | None = None
    provider: ProviderInfo | None = Field(default=None, exclude=True)
    last_published_at: datetime | None = Field(default=None, exclude=True)


class Registry(BaseModel):
    version: int = 1
    posts: list[RegistryEntry] = Field(default_factory=list)
