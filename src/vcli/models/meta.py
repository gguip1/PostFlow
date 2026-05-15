from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PostStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    published = "published"


class Visibility(str, Enum):
    public = "public"
    private = "private"


class Meta(BaseModel):
    title: str
    slug: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    visibility: Visibility = Visibility.public
    series: str | None = None
    model_config = ConfigDict(extra="allow")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError(f"slug must be a non-empty trimmed string: {value!r}")
        return value
