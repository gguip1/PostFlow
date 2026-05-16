from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def install_skill(source: Path, destination_root: Path, label: str) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"source skill not found for {label}: {source}")

    destination_root.mkdir(parents=True, exist_ok=True)
    destination = destination_root / source.name

    if destination.exists():
        shutil.rmtree(destination)

    shutil.copytree(source, destination)
    print(f"[ok] Installed {source.name} to {label}: {destination}")


def find_skills(source_root: Path, skill_name: str | None, prefix: str) -> list[Path]:
    if not source_root.is_dir():
        raise FileNotFoundError(f"source skill root not found: {source_root}")

    if skill_name:
        return [source_root / skill_name]

    return sorted(
        path
        for path in source_root.iterdir()
        if path.is_dir() and path.name.startswith(prefix)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install repo-local vcli skills into global Codex and/or Claude skill directories."
    )
    parser.add_argument("--skill-name", default=None)
    parser.add_argument("--skill-prefix", default="vcli-")
    parser.add_argument("--target", choices=("both", "codex", "claude"), default="both")
    parser.add_argument(
        "--codex-skills-root",
        default=str(Path.home() / ".codex" / "skills"),
    )
    parser.add_argument(
        "--claude-skills-root",
        default=str(Path.home() / ".claude" / "skills"),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    source_root = repo_root / ".agents" / "skills"
    skill_dirs = find_skills(source_root, args.skill_name, args.skill_prefix)

    if args.target in ("both", "codex"):
        for skill_dir in skill_dirs:
            install_skill(
                skill_dir,
                Path(args.codex_skills_root).expanduser(),
                "Codex",
            )

    if args.target in ("both", "claude"):
        for skill_dir in skill_dirs:
            install_skill(
                skill_dir,
                Path(args.claude_skills_root).expanduser(),
                "Claude",
            )

    print("")
    print("Skill install complete.")
    print("If `vcli` is not on PATH yet, install the CLI separately in a global environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
