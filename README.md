# unofficial-velog-cli

AI 에이전트가 Velog 글을 로컬 `.vcli` 저장소에서 가져오고, 수정하고, 발행할 수 있게 돕는 CLI입니다.

`vcli`는 블로그 CMS가 아니라 Velog pull/push 어댑터입니다. 글 기획, 시리즈 관리, 외부 초안 정리는 사용자가 원하는 폴더에서 자유롭게 관리하고, 실제 Velog와 동기화되는 글만 `.vcli/posts`에서 관리합니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows PowerShell:

```powershell
.venv\Scripts\activate
pip install -e .
```

## 빠른 시작

```bash
vcli init
vcli login
vcli pull
vcli create ai-velog-workflow --title "AI로 쓰는 Velog 워크플로우" --tags velog,cli
vcli status
vcli push ai-velog-workflow
```

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
    posts/
      <slug>/
        content.md
        meta.yaml
        images/
          mapping.json
```

Velog 인증 세션은 현재 vcli 저장소의 `.vcli/velog-auth.json`에 저장합니다.

## 이미지 업로드

`vcli`는 이미지를 본문에 자동 연결하지 않습니다. 로컬 이미지는 먼저 업로드한 뒤 출력된 URL을 `content.md`에 직접 넣습니다.

```bash
vcli image upload .vcli/posts/my-post/images/diagram.png
```

에이전트가 파싱해야 하면 `--json`을 사용합니다.

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
