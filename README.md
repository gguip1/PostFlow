# unofficial-velog-cli

Velog 글을 로컬 `.vcli` 저장소로 가져오고, 수정하고, 발행할 수 있게 돕는 CLI입니다.

`vcli`는 블로그 CMS가 아니라 Velog pull/push 어댑터입니다. 글 기획, 시리즈 관리, 외부 초안 정리는 사용자가 원하는 폴더에서 자유롭게 관리하고, 실제 Velog와 동기화되는 글만 `.vcli/posts`에서 관리합니다.

이 프로젝트는 Velog 공식 프로젝트가 아니며 Velog 또는 운영사와 제휴하거나
승인받은 도구가 아닙니다.

## 설치

Python 3.12 이상을 대상으로 하며 [uv](https://docs.astral.sh/uv/getting-started/installation/)가
필요합니다. macOS에서 Homebrew를 사용한다면 다음 명령으로 uv를 설치합니다.

```bash
brew install uv
```

저장소를 clone한 뒤 uv의 격리된 tool 환경에 설치합니다.

```bash
git clone https://github.com/gguip1/unofficial-velog-cli.git
cd unofficial-velog-cli
uv tool install .
```

`vcli` 명령을 찾지 못하면 uv의 실행 파일 경로를 셸에 추가한 뒤 터미널을
다시 시작합니다.

```bash
uv tool update-shell
```

그래도 현재 셸에서 명령을 찾지 못하면 다음처럼 uv tool 실행 경로를 직접
추가합니다.

```bash
export PATH="$(uv tool dir --bin):$PATH"
```

새 변경을 받은 뒤 설치된 도구를 갱신하려면 다음 명령을 실행합니다.

```bash
git pull --ff-only
uv tool install --reinstall .
```

에이전트 skill을 설치한 작업공간에서는 새 번들 버전으로 함께 갱신합니다.

```bash
cd /path/to/blog-workspace
vcli skill update
```

설치 후 어느 폴더에서든 `vcli`를 실행할 수 있습니다.

```bash
vcli --version
vcli --help
```

제거하려면 다음 명령을 실행합니다.

```bash
uv tool uninstall unofficial-velog-cli
```

## 개발

기여하려면 저장소를 fork한 뒤 uv로 개발 환경을 동기화합니다.

```bash
git clone https://github.com/gguip1/unofficial-velog-cli.git
cd unofficial-velog-cli
uv sync --locked --dev
uv run python -m unittest discover -s tests
```

도구를 editable 모드로 설치하면 저장소의 소스 변경이 설치된 `vcli`에 바로
반영됩니다.

```bash
uv tool install --editable .
```

의존성을 변경했다면 `uv lock`을 실행하고 `uv.lock`을 함께 커밋합니다.

## 빠른 시작

```bash
vcli init
vcli skill install
vcli login
vcli pull
vcli create my-velog-post --title "Velog 글 작성하기" --tags velog,cli
vcli status
vcli push my-velog-post
```

## 에이전트 skill

초기화된 블로그 작업공간에서 Codex와 Claude Code용 `vcli-manage-posts`
skill을 설치할 수 있습니다.

```bash
vcli skill install
vcli skill status
```

설치 위치는 다음과 같습니다.

```text
.agents/skills/vcli-manage-posts/SKILL.md
.claude/skills/vcli-manage-posts/SKILL.md
```

`vcli`는 작업공간의 루트 `AGENTS.md`와 `CLAUDE.md`를 만들거나 수정하지
않습니다. 블로그 문체, 독자, 주제 같은 사용자 지침은 해당 파일에서 별도로
관리할 수 있습니다.

설치된 skill을 수정하지 않았다면 다음 명령으로 안전하게 갱신하거나 제거할 수
있습니다.

```bash
vcli skill update
vcli skill uninstall
```

기존 파일이나 사용자가 수정한 파일은 자동으로 덮어쓰거나 삭제하지 않습니다.
의도적으로 교체해야 할 때만 `--force`를 사용합니다. Codex 또는 Claude 하나만
관리하려면 `--target codex` 또는 `--target claude`를 지정합니다.

## 기본 명령

| 명령어 | 설명 |
|--------|------|
| `vcli init` | 현재 폴더에 로컬 `.vcli` 저장소 생성 |
| `vcli login` | 현재 `.vcli` 저장소에 Velog 인증 저장 |
| `vcli pull` | Velog 글을 `.vcli/posts`로 가져오기 |
| `vcli create <slug>` | `.vcli/posts/<slug>`에 로컬 draft 생성 |
| `vcli list` | 로컬 글 목록과 계산된 상태 출력 |
| `vcli status` | `draft`/`modified`/`synced` 상태 확인 |
| `vcli check [slug]` | 글 파일과 registry 검증 |
| `vcli doctor` | `.vcli` 저장소와 인증 상태 점검 |
| `vcli push` | draft/modified 글을 선택해서 Velog에 반영 |
| `vcli push <slug>` | 특정 글 하나를 Velog에 발행 또는 수정 |
| `vcli image upload <path>` | 로컬 이미지를 Velog CDN에 업로드하고 URL 출력 |
| `vcli skill install` | 현재 작업공간에 Codex/Claude용 skill 설치 |
| `vcli skill status` | 설치된 skill의 `missing`/`current`/`outdated`/`conflict` 상태 확인 |
| `vcli skill update` | vcli가 관리하는 수정되지 않은 skill 갱신 |
| `vcli skill uninstall` | vcli가 관리하는 수정되지 않은 skill 제거 |

## 상태 모델

상태는 저장하지 않고 `.vcli/registry.yaml`과 현재 파일 hash로 계산합니다.

| 상태 | 의미 |
|------|------|
| `draft` | `velog_id`가 없어 아직 Velog에 올라가지 않은 로컬 글 |
| `modified` | `velog_id`가 있고 현재 파일 hash가 `last_synced_hash`와 다른 글 |
| `synced` | `velog_id`가 있고 현재 파일 hash가 `last_synced_hash`와 같은 글 |

글 생성/수정처럼 Velog 글에 쓰기 작업을 하는 명령은 `vcli push`입니다. 이미지는 `vcli image upload`로 별도 업로드하고, 출력된 URL을 본문에 직접 넣습니다.

## 로컬 저장소 구조

```text
project/
  .vcli/
    config.yaml
    registry.yaml
    uploads.yaml
    skills.yaml
    posts/
      <slug>/
        content.md
        meta.yaml
        images/
          mapping.json
  .agents/
    skills/vcli-manage-posts/SKILL.md
  .claude/
    skills/vcli-manage-posts/SKILL.md
```

Velog 인증 세션은 현재 vcli 저장소의 `.vcli/velog-auth.json`에 저장합니다.

`vcli init`은 명령을 실행한 현재 폴더에 `.vcli`를 만듭니다. 다른 경로를
초기화하려면 `vcli init --path <folder>`를 사용합니다. 이후 명령은 현재
폴더부터 상위 폴더 방향으로 가장 가까운 `.vcli/registry.yaml`을 찾아 해당
작업공간을 사용하므로, `.vcli/posts/<slug>` 같은 하위 폴더에서도 실행할 수
있습니다.

uv tool 환경에는 `vcli` 실행 파일과 Python 의존성만 설치됩니다. Velog 글,
registry, 이미지 업로드 기록과 인증 정보는 모두 사용자가 초기화한 작업공간의
`.vcli` 아래에 저장됩니다.

`skills.yaml`에는 vcli가 설치한 agent skill의 대상 경로와 설치 당시 hash만
기록합니다. 이를 이용해 사용자가 수정한 skill을 갱신이나 제거 과정에서
보호합니다.

## 이미지 업로드

`vcli`는 이미지를 본문에 자동 연결하지 않습니다. 로컬 이미지는 먼저 업로드한 뒤 출력된 URL을 `content.md`에 직접 넣습니다.

```bash
vcli image upload .vcli/posts/my-post/images/diagram.png
```

스크립트에서 결과를 파싱해야 하면 `--json`을 사용합니다.

```bash
vcli image upload .vcli/posts/my-post/images/diagram.png --json
```

업로드 기록은 `.vcli/uploads.yaml`에 저장합니다. `push`는 `mapping.json`으로 복원할 수 없는 로컬 이미지 경로가 본문에 남아 있으면 발행을 막습니다.

## 주의사항

- `create`와 파일 수정은 발행하지 않습니다.
- Velog에 실제로 쓰기 작업을 하는 명령은 `vcli push`입니다.
- `vcli push`는 동기화 병합이 아닙니다. 선택한 로컬 글 상태로 Velog 글을 덮어씁니다.
- `push` 전에 `vcli status`와 `vcli check <slug>`를 실행하세요.
- `push` 화면에서 로컬 글과 원격 Velog URL을 확인한 뒤 진행하세요.
- Velog 웹에서 글을 수정했다면 로컬 수정 전에 `vcli pull`로 먼저 가져오세요.
- 사용자 명시적 승인 전에는 `push`를 실행하지 마세요.
- `push --all`은 지원하지 않습니다.
- 새 로컬 이미지는 `vcli image upload <path>`로 업로드하고 출력된 URL을 본문에 넣어야 합니다.

## 보안 주의사항

`.vcli/`는 Git에 올리면 안 됩니다. 이 폴더에는 Velog 인증 세션, 가져온 글, 로컬 draft, 이미지 업로드 기록이 들어갈 수 있습니다.

특히 `.vcli/velog-auth.json`은 Velog 인증 정보입니다. 저장소에 커밋하지 마세요.

이 저장소의 `.gitignore`는 `.vcli/`를 무시하도록 설정되어 있습니다. `.gitignore`를 수정하더라도 `.vcli/`는 계속 무시해야 합니다.
