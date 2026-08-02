# Changelog

이 프로젝트의 주요 변경 사항을 이 문서에 기록합니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르며,
버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## Unreleased

### Added

- 저장된 refresh token을 이용한 Velog 인증 자동 갱신
- Codex와 Claude Code 작업공간에 공용 `vcli-manage-posts` skill을 안전하게
  설치, 확인, 갱신, 제거하는 `vcli skill` 명령

### Changed

- GraphQL 및 이미지 업로드 요청에서 회전된 인증 쿠키를 로컬 인증 파일에 반영

### Security

- 인증 파일을 원자적으로 저장하고 소유자만 읽고 쓸 수 있도록 `0600` 권한 적용

## 0.1.0 - 2026-03-30

- 최초 개발 버전
