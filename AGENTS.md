# unofficial-velog-cli

Velog 글 발행용 agent-first CLI.

## 목적

- AI agent가 Velog 글을 안전하게 가져오고 수정하고 발행할 수 있게 한다.
- `vcli`는 블로그 CMS가 아니라 Velog pull/push 어댑터다.
- 글쓰기 흐름, 시리즈 기획, 외부 문서 정리는 `vcli`가 소유하지 않는다.
- 실제 Velog와 동기화되는 publish 대상은 현재 폴더의 로컬 `.vcli` 저장소다.

## 로컬 `.vcli` 저장소 규칙

- `vcli init`은 현재 폴더에 `.vcli/`를 만든다.
- `.vcli/posts/<slug>/content.md`와 `.vcli/posts/<slug>/meta.yaml`이 실제 push 대상이다.
- `.vcli/registry.yaml`은 Velog 글과 로컬 글의 연결 정보만 관리한다.
- 루트의 `series/`, `drafts/`, 기타 문서 폴더는 사용자가 자유롭게 관리하며 `vcli`가 강제하지 않는다.
- Velog 인증은 전역 `~/.vcli/velog-auth.json`에 둔다.
- 전역 `~/.vcli/blog`를 기본 글 저장소처럼 사용하지 않는다.

## 공개 명령

| 명령어 | 설명 |
|--------|------|
| `vcli init` | 현재 폴더에 로컬 `.vcli` 저장소 생성 |
| `vcli login` | Velog 인증 저장 |
| `vcli pull` | Velog 글 전체를 `.vcli/posts`로 가져오기 |
| `vcli create` | `.vcli/posts`에 로컬 draft 생성 |
| `vcli list` | 로컬 글 목록과 계산된 상태 출력 |
| `vcli status` | `draft`/`modified`/`synced` 상태 출력 |
| `vcli check [slug]` | 글 파일과 registry 검증 |
| `vcli doctor` | `.vcli` 저장소와 인증 상태 점검 |
| `vcli push` | draft/modified 글을 선택해서 Velog에 반영 |
| `vcli push <slug>` | 특정 글 하나를 Velog에 발행 또는 수정 |

## 상태 모델

상태는 저장하지 않고 `.vcli/registry.yaml`과 현재 파일 hash로 계산한다.

| 상태 | 의미 |
|------|------|
| `draft` | `velog_id`가 없어 아직 Velog에 올라가지 않은 로컬 글 |
| `modified` | `velog_id`가 있고 현재 파일 hash가 `last_synced_hash`와 다른 글 |
| `synced` | `velog_id`가 있고 현재 파일 hash가 `last_synced_hash`와 같은 글 |

`ready` 상태는 새 모델에서 사용하지 않는다.

## Registry 규칙

`.vcli/registry.yaml`은 최소한 다음 값을 관리한다.

```yaml
version: 1
posts:
  - slug: my-post
    velog_id: abc-123
    url: https://velog.io/@me/my-post
    last_synced_hash: 9f1a...
    last_synced_at: "2026-05-16T12:00:00Z"
```

- `slug`: `.vcli/posts/<slug>`와 연결되는 로컬 식별자
- `velog_id`: Velog 글 id. 없으면 draft로 계산한다.
- `url`: 발행된 Velog URL
- `last_synced_hash`: 마지막 pull 또는 push 성공 시점의 `content.md + meta.yaml` hash
- `last_synced_at`: 마지막 pull 또는 push 성공 시각

## 이미지 규칙

- `pull`은 원격 이미지 URL을 `.vcli/posts/<slug>/images/`로 다운로드할 수 있다.
- `content.md`에는 `./images/...` 로컬 경로를 쓴다.
- 원본 URL 매핑은 `.vcli/posts/<slug>/images/mapping.json`에 저장한다.
- `push`는 `mapping.json`을 읽어 기존 로컬 이미지 경로를 원격 URL로 복원한다.
- 새 로컬 이미지 업로드는 초기 범위가 아니다.

## Agent 작업 규칙

- 새 글 요청을 받으면 파일을 직접 만들기보다 `vcli create`를 우선 사용한다.
- Velog 원본을 가져와야 하면 `vcli pull`을 사용한다.
- 작업 전후에는 `vcli status`로 `draft`/`modified`/`synced` 상태를 확인한다.
- 사용자 명시적 승인 전에는 절대 `vcli push`를 실행하지 않는다.
- `vcli push --all`은 초기 모델에서 사용하지 않는다.
- `pull`은 `modified` 로컬 글을 덮어쓰면 안 된다.
- `push`만 Velog에 쓰기 작업을 하는 명령이다.

## Deprecated

- `vcli ready`
- `vcli publish`
- `vcli sync`
- `vcli root set/show`
- `vcli workspace set/show/clear`
