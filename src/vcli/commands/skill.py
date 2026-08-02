from enum import Enum

import typer

from vcli.core.skills import (
    SkillConflictError,
    SkillStatus,
    get_skill_statuses,
    install_skill,
    resolve_targets,
    uninstall_skill,
    update_skill,
)
from vcli.core.workspace import find_workspace_root
from vcli.utils import logger


class SkillTarget(str, Enum):
    all = "all"
    codex = "codex"
    claude = "claude"


skill_app = typer.Typer(
    help="현재 vcli 작업공간에 에이전트 skill을 관리합니다.",
    no_args_is_help=True,
)


def _targets(target: SkillTarget) -> tuple[str, ...]:
    return resolve_targets(target.value)


def _root_or_exit():
    try:
        return find_workspace_root()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        raise typer.Exit(1) from exc


def _run_or_exit(operation):
    try:
        return operation()
    except (SkillConflictError, OSError) as exc:
        logger.error(str(exc))
        raise typer.Exit(1) from exc


def _show_statuses(statuses: list[SkillStatus]) -> None:
    for status in statuses:
        logger.info(f"{status.target}: {status.state} ({status.path})")


@skill_app.command(name="install")
def install(
    target: SkillTarget = typer.Option(
        SkillTarget.all,
        "--target",
        help="설치 대상: all, codex, claude",
        case_sensitive=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="기존 또는 충돌한 skill 파일을 강제로 교체",
    ),
) -> None:
    """번들된 vcli skill을 현재 작업공간에 설치합니다."""
    root = _root_or_exit()
    statuses = _run_or_exit(
        lambda: install_skill(root, _targets(target), force=force)
    )
    _show_statuses(statuses)
    logger.success("vcli agent skill을 설치했습니다.")


@skill_app.command(name="status")
def status(
    target: SkillTarget = typer.Option(
        SkillTarget.all,
        "--target",
        help="확인 대상: all, codex, claude",
        case_sensitive=False,
    ),
) -> None:
    """설치된 vcli skill 상태를 확인합니다."""
    root = _root_or_exit()
    _show_statuses(get_skill_statuses(root, _targets(target)))


@skill_app.command(name="update")
def update(
    target: SkillTarget = typer.Option(
        SkillTarget.all,
        "--target",
        help="갱신 대상: all, codex, claude",
        case_sensitive=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="사용자가 수정한 skill 파일도 강제로 교체",
    ),
) -> None:
    """vcli가 관리하는 skill을 현재 번들 버전으로 갱신합니다."""
    root = _root_or_exit()
    statuses = _run_or_exit(
        lambda: update_skill(root, _targets(target), force=force)
    )
    _show_statuses(statuses)
    logger.success("vcli agent skill을 갱신했습니다.")


@skill_app.command(name="uninstall")
def uninstall(
    target: SkillTarget = typer.Option(
        SkillTarget.all,
        "--target",
        help="제거 대상: all, codex, claude",
        case_sensitive=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="사용자가 수정한 관리 대상 skill 파일도 강제로 삭제",
    ),
) -> None:
    """vcli가 설치한 skill을 현재 작업공간에서 제거합니다."""
    root = _root_or_exit()
    statuses = _run_or_exit(
        lambda: uninstall_skill(root, _targets(target), force=force)
    )
    _show_statuses(statuses)
    logger.success("vcli agent skill을 제거했습니다.")
