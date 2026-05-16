from pydantic import BaseModel, Field, field_validator


class Meta(BaseModel):
    title: str
    slug: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    visibility: str = "public"
    series: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError(f"slug must be a non-empty trimmed string: {value!r}")
        return value

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        if value not in {"public", "private"}:
            raise ValueError("visibility must be public or private")
        return value
