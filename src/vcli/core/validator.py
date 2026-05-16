from pathlib import Path

from pydantic import ValidationError

from vcli.core.registry import load_registry
from vcli.models import Meta
from vcli.utils.fs import read_yaml
from vcli.utils.paths import get_post_dir, get_posts_dir


class CheckResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "CheckResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def validate_post(root: Path, slug: str) -> CheckResult:
    result = CheckResult()
    post_dir = get_post_dir(root, slug)

    if not post_dir.exists():
        result.add_error(f"[{slug}] post directory is missing")
        return result

    content_path = post_dir / "content.md"
    if not content_path.exists():
        result.add_error(f"[{slug}] content.md is missing")

    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        result.add_error(f"[{slug}] meta.yaml is missing")
        return result

    try:
        meta = Meta(**read_yaml(meta_path))
    except ValidationError as error:
        for item in error.errors():
            field = ".".join(str(loc) for loc in item["loc"])
            result.add_error(f"[{slug}] meta.yaml invalid: {field}: {item['msg']}")
        return result

    if meta.slug != slug:
        result.add_error(
            f"[{slug}] meta.yaml slug does not match directory name: {meta.slug}"
        )
    if not meta.title:
        result.add_error(f"[{slug}] meta.yaml title is empty")

    return result


def validate_registry(root: Path) -> CheckResult:
    result = CheckResult()
    registry = load_registry(root)
    posts_dir = get_posts_dir(root)

    seen_slugs: set[str] = set()

    for entry in registry.posts:
        if entry.slug in seen_slugs:
            result.add_error(f"registry contains duplicate slug: {entry.slug}")
        seen_slugs.add(entry.slug)

        post_dir = posts_dir / entry.slug
        if not post_dir.exists():
            result.add_error(f"[{entry.slug}] registry entry points to a missing directory")
            continue

        meta_path = post_dir / "meta.yaml"
        if not meta_path.exists():
            result.add_error(f"[{entry.slug}] registry entry points to a missing meta.yaml")
            continue

        try:
            meta = Meta(**read_yaml(meta_path))
        except ValidationError as error:
            for item in error.errors():
                field = ".".join(str(loc) for loc in item["loc"])
                result.add_error(
                    f"[{entry.slug}] meta.yaml invalid: {field}: {item['msg']}"
                )
            continue

    if posts_dir.exists():
        for child in posts_dir.iterdir():
            if (
                child.is_dir()
                and (child / "meta.yaml").exists()
                and child.name not in seen_slugs
            ):
                result.add_warning(f"[{child.name}] post directory is missing from registry")

    return result


def validate_all(root: Path) -> CheckResult:
    result = CheckResult()
    posts_dir = get_posts_dir(root)

    result.merge(validate_registry(root))

    if posts_dir.exists():
        for child in sorted(posts_dir.iterdir()):
            if child.is_dir() and (child / "meta.yaml").exists():
                result.merge(validate_post(root, child.name))

    return result
