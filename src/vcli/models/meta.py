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
            raise ValueError(f"slug는 앞뒤 공백 없는 비어 있지 않은 문자열이어야 합니다: {value!r}")
        return value

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        if value not in {"public", "private"}:
            raise ValueError("visibility는 public 또는 private이어야 합니다.")
        return value
