from pydantic import BaseModel, Field


class VelogConfig(BaseModel):
    username: str = ""


class Settings(BaseModel):
    default_visibility: str = "public"
    default_status: str = "draft"


class Config(BaseModel):
    version: int = 1
    posts_dir: str = "posts"
    velog: VelogConfig = Field(default_factory=VelogConfig)
    settings: Settings = Field(default_factory=Settings)
