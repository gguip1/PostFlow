from pydantic import BaseModel, Field


class UploadEntry(BaseModel):
    local_path: str
    url: str
    sha256: str
    post_slug: str | None = None
    uploaded_at: str


class UploadRegistry(BaseModel):
    version: int = 1
    uploads: list[UploadEntry] = Field(default_factory=list)
