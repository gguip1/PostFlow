from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml

from vcli.core.workspace import workspace_dir
from vcli.utils.fs import read_yaml


SKILL_NAME = "vcli-manage-posts"
MANIFEST_VERSION = 1
TARGET_PATHS = {
    "codex": Path(".agents/skills") / SKILL_NAME / "SKILL.md",
    "claude": Path(".claude/skills") / SKILL_NAME / "SKILL.md",
}
_BUNDLED_SKILL_PARTS = (
    "resources",
    "skills",
    SKILL_NAME,
    "SKILL.md",
)


class SkillConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillStatus:
    target: str
    path: Path
    state: str


def skill_manifest_path(root: Path) -> Path:
    return workspace_dir(root) / "skills.yaml"


def bundled_skill_bytes() -> bytes:
    resource = resources.files("vcli").joinpath(*_BUNDLED_SKILL_PARTS)
    return resource.read_bytes()


def bundled_skill_hash() -> str:
    return _hash_bytes(bundled_skill_bytes())


def resolve_targets(target: str) -> tuple[str, ...]:
    if target == "all":
        return tuple(TARGET_PATHS)
    if target not in TARGET_PATHS:
        raise ValueError(f"지원하지 않는 skill target입니다: {target}")
    return (target,)


def get_skill_statuses(root: Path, targets: tuple[str, ...]) -> list[SkillStatus]:
    root = root.resolve()
    manifest = _load_manifest(root)
    bundle_hash = bundled_skill_hash()
    return [
        SkillStatus(
            target=target,
            path=root / TARGET_PATHS[target],
            state=_target_state(root, target, manifest, bundle_hash),
        )
        for target in targets
    ]


def install_skill(
    root: Path, targets: tuple[str, ...], *, force: bool = False
) -> list[SkillStatus]:
    root = root.resolve()
    _validate_target_parents(root, targets)
    bundle = bundled_skill_bytes()
    bundle_hash = _hash_bytes(bundle)
    manifest = _load_manifest(root)

    blockers: list[str] = []
    for target in targets:
        path = root / TARGET_PATHS[target]
        state = _target_state(root, target, manifest, bundle_hash)
        can_adopt = (
            path.exists()
            and not path.is_symlink()
            and _recorded_hash(manifest, target) is None
            and _hash_file(path) == bundle_hash
        )
        if state in {"outdated", "conflict"} and not can_adopt and not force:
            blockers.append(f"{target} ({state}): {path}")

    if blockers:
        details = "\n".join(f"- {blocker}" for blocker in blockers)
        raise SkillConflictError(
            "기존 skill 파일을 덮어쓰지 않았습니다. "
            "갱신은 `vcli skill update`, 강제 교체는 `--force`를 사용하세요.\n"
            f"{details}"
        )

    for target in targets:
        path = root / TARGET_PATHS[target]
        if not path.exists() or _hash_file(path) != bundle_hash:
            _atomic_write(path, bundle)
        _record_install(manifest, root, target, bundle_hash)

    _write_manifest(root, manifest)
    return get_skill_statuses(root, targets)


def update_skill(
    root: Path, targets: tuple[str, ...], *, force: bool = False
) -> list[SkillStatus]:
    root = root.resolve()
    _validate_target_parents(root, targets)
    bundle = bundled_skill_bytes()
    bundle_hash = _hash_bytes(bundle)
    manifest = _load_manifest(root)

    blockers = [
        status
        for status in get_skill_statuses(root, targets)
        if status.state == "conflict" and _recorded_hash(manifest, status.target)
    ]
    if blockers and not force:
        details = "\n".join(
            f"- {status.target} (conflict): {status.path}" for status in blockers
        )
        raise SkillConflictError(
            "사용자가 수정한 skill 파일을 덮어쓰지 않았습니다. "
            "강제 교체하려면 `--force`를 사용하세요.\n"
            f"{details}"
        )

    for target in targets:
        recorded = _recorded_hash(manifest, target)
        if recorded is None:
            continue
        path = root / TARGET_PATHS[target]
        if not path.exists() or _hash_file(path) != bundle_hash:
            _atomic_write(path, bundle)
        _record_install(manifest, root, target, bundle_hash)

    _write_manifest(root, manifest)
    return get_skill_statuses(root, targets)


def uninstall_skill(
    root: Path, targets: tuple[str, ...], *, force: bool = False
) -> list[SkillStatus]:
    root = root.resolve()
    _validate_target_parents(root, targets)
    manifest = _load_manifest(root)
    bundle_hash = bundled_skill_hash()

    blockers: list[SkillStatus] = []
    for target in targets:
        if _recorded_hash(manifest, target) is None:
            continue
        state = _target_state(root, target, manifest, bundle_hash)
        if state == "conflict":
            blockers.append(
                SkillStatus(target, root / TARGET_PATHS[target], state)
            )

    if blockers and not force:
        details = "\n".join(
            f"- {status.target} (conflict): {status.path}" for status in blockers
        )
        raise SkillConflictError(
            "사용자가 수정한 skill 파일을 삭제하지 않았습니다. "
            "강제 삭제하려면 `--force`를 사용하세요.\n"
            f"{details}"
        )

    for target in targets:
        if _recorded_hash(manifest, target) is None:
            continue
        path = root / TARGET_PATHS[target]
        if path.exists() or path.is_symlink():
            path.unlink()
            _remove_empty_skill_directory(path.parent)
        _remove_record(manifest, target)

    _write_manifest(root, manifest)
    return get_skill_statuses(root, targets)


def _target_state(
    root: Path, target: str, manifest: dict, bundle_hash: str
) -> str:
    path = root / TARGET_PATHS[target]
    if _has_unsafe_parent(root, path) or path.is_symlink():
        return "conflict"
    if path.exists() and not path.is_file():
        return "conflict"
    if not path.exists():
        return "missing"

    current_hash = _hash_file(path)
    recorded_hash = _recorded_hash(manifest, target)
    if recorded_hash is None:
        return "conflict"
    if current_hash == bundle_hash:
        return "current"
    if current_hash == recorded_hash:
        return "outdated"
    return "conflict"


def _load_manifest(root: Path) -> dict:
    path = skill_manifest_path(root)
    if not path.exists():
        return {"version": MANIFEST_VERSION, "skills": {}}

    data = read_yaml(path)
    if not isinstance(data, dict):
        return {"version": MANIFEST_VERSION, "skills": {}}
    data.setdefault("version", MANIFEST_VERSION)
    if not isinstance(data.get("skills"), dict):
        data["skills"] = {}
    return data


def _skill_targets(manifest: dict) -> dict:
    skills = manifest.setdefault("skills", {})
    skill = skills.setdefault(SKILL_NAME, {})
    targets = skill.setdefault("targets", {})
    if not isinstance(targets, dict):
        targets = {}
        skill["targets"] = targets
    return targets


def _recorded_hash(manifest: dict, target: str) -> str | None:
    skills = manifest.get("skills")
    if not isinstance(skills, dict):
        return None
    skill = skills.get(SKILL_NAME)
    if not isinstance(skill, dict):
        return None
    targets = skill.get("targets")
    if not isinstance(targets, dict):
        return None
    record = targets.get(target)
    if not isinstance(record, dict):
        return None
    installed_hash = record.get("installed_hash")
    return installed_hash if isinstance(installed_hash, str) else None


def _record_install(
    manifest: dict, root: Path, target: str, installed_hash: str
) -> None:
    path = root / TARGET_PATHS[target]
    _skill_targets(manifest)[target] = {
        "path": path.relative_to(root).as_posix(),
        "installed_hash": installed_hash,
    }


def _remove_record(manifest: dict, target: str) -> None:
    targets = _skill_targets(manifest)
    targets.pop(target, None)
    if targets:
        return
    skills = manifest.get("skills")
    if isinstance(skills, dict):
        skills.pop(SKILL_NAME, None)


def _write_manifest(root: Path, manifest: dict) -> None:
    path = skill_manifest_path(root)
    if not manifest.get("skills"):
        path.unlink(missing_ok=True)
        return
    content = yaml.safe_dump(
        manifest,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).encode("utf-8")
    _atomic_write(path, content)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _remove_empty_skill_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def _validate_target_parents(root: Path, targets: tuple[str, ...]) -> None:
    unsafe: list[Path] = []
    for target in targets:
        path = root / TARGET_PATHS[target]
        target_is_directory = (
            path.exists() and not path.is_file() and not path.is_symlink()
        )
        if _has_unsafe_parent(root, path) or target_is_directory:
            unsafe.append(path)

    if unsafe:
        details = "\n".join(f"- {path}" for path in unsafe)
        raise SkillConflictError(
            "심볼릭 링크나 파일/디렉터리 충돌이 있는 skill 설치 경로에는 "
            "쓰지 않습니다.\n"
            f"{details}"
        )


def _has_unsafe_parent(root: Path, path: Path) -> bool:
    current = root
    for part in path.relative_to(root).parts[:-1]:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            return True
    return False


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())
