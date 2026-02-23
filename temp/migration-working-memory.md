# Migration Working Memory

## 작업 목표
1. `research/` 폴더 생성
2. `action-plans/` 폴더 생성 + 기존 plan 파일 마이그레이션

## 프로젝트 현황 (탐색 결과)

### 루트 구조
- CLAUDE.md, README.md, TEST-PLAN.md, LICENSE, .gitignore
- .claude/, .claude-plugin/ (플러그인 코드)
- _archive/ (이전 세션 아카이브)
- temp/ (18개 작업 파일)
- tmp/ (1개 파일)
- on_notification.wav, on_stop.wav (사운드 파일)

### Plan 관련 파일 목록
| 파일 | 위치 | 성격 | 분류 | 이동 대상 |
|------|------|------|------|-----------|
| TEST-PLAN.md | 루트 | 테스트 실행 계획 (P0/P1/P2) | 활성 plan | action-plans/ |
| MASTER-PLAN.md | temp/ | 문서화 작업 마스터 플랜 | 완료된 plan | action-plans/_done/ |
| phase2-doc-restructure-plan.md | temp/ | 문서 구조조정 실행 계획 | 완료된 plan | action-plans/_done/ |

### 비-plan 파일 (이동 대상 아님)
- temp/FINAL-REPORT.md: 보고서 (plan이 아님)
- temp/phase1-*.md: 분석 결과물
- temp/phase2-gap-analysis.md, phase2-best-practices.md, phase2-user-scenarios.md: 분석
- temp/phase3-*.md: 변경 로그 / 리뷰
- temp/phase4-*.md, phase5-*.md, phase6-*.md: 검증 결과
- tmp/phase2-best-practices.md: 분석 (중복)

### Plan 파일 Frontmatter 결정
| 파일 | status | progress |
|------|--------|----------|
| TEST-PLAN.md → test-plan.md | not-started | 미시작. P0~P2 테스트 항목 정의 완료, 구현 미시작 |
| MASTER-PLAN.md → doc-enhancement-master-plan.md | done | 6단계 문서화 프로젝트 완료 (FINAL-REPORT.md 참고) |
| phase2-doc-restructure-plan.md → doc-restructure-plan.md | done | Phase 3에서 실행 완료 |

### 참조 업데이트 필요 파일
- CLAUDE.md: TEST-PLAN.md 참조 (line 75)
- README.md: 확인 필요
- 기타: grep으로 전수 확인 필요

## 자가비판

### 의문점
1. TEST-PLAN.md는 kebab-case로 이름 변경? → YES, 규칙상 kebab-case 필수
2. temp/의 비-plan 파일은 어떻게? → 사용자가 지시하지 않음, 그대로 둠
3. _archive/의 MASTER-PLAN.md는? → 아카이브 안에 있으므로 건드리지 않음

### 리스크
- TEST-PLAN.md를 이동하면 CLAUDE.md의 참조가 깨짐 → 반드시 업데이트
- README.md에도 TEST-PLAN.md 참조가 있을 수 있음 → 확인 필요

## 변경 추적

### 생성된 디렉토리/파일
| 경로 | 설명 |
|------|------|
| `research/` | 빈 디렉토리 (.gitkeep) |
| `action-plans/` | 실행 계획 관리 디렉토리 |
| `action-plans/README.md` | 시스템 규칙 문서 |
| `action-plans/_done/.gitkeep` | 완료된 계획 디렉토리 |
| `action-plans/_ref/.gitkeep` | 참고/역사적 문서 디렉토리 |
| `action-plans/test-plan.md` | TEST-PLAN.md에서 마이그레이션 (status: not-started) |
| `action-plans/_done/doc-enhancement-master-plan.md` | temp/MASTER-PLAN.md에서 마이그레이션 (status: done) |
| `action-plans/_done/doc-restructure-plan.md` | temp/phase2-doc-restructure-plan.md에서 마이그레이션 (status: done) |

### 삭제된 파일
| 경로 | 사유 |
|------|------|
| `TEST-PLAN.md` | action-plans/test-plan.md로 이동 |
| `temp/MASTER-PLAN.md` | action-plans/_done/doc-enhancement-master-plan.md로 이동 |
| `temp/phase2-doc-restructure-plan.md` | action-plans/_done/doc-restructure-plan.md로 이동 |

### 수정된 파일
| 파일 | 변경 내용 |
|------|-----------|
| `CLAUDE.md` (line 75) | TEST-PLAN.md → action-plans/test-plan.md 참조 업데이트 |
| `CLAUDE.md` (line 77+) | Action Plans 섹션 추가 |
| `README.md` (line 121) | TEST-PLAN.md → action-plans/test-plan.md 참조 업데이트 |
| `.claude/skills/deepscan/docs/SECURITY.md` (line 311) | ../../../TEST-PLAN.md → ../../../../action-plans/test-plan.md 참조 업데이트 |
| `action-plans/test-plan.md` (line 10) | SECURITY.md 링크 상대 경로 수정 (.claude → ../.claude) |

### 변경하지 않은 파일 (의도적)
- `temp/` 내 나머지 파일들: 역사적 작업 산출물, TEST-PLAN.md 참조 포함하지만 수정하지 않음
- `tmp/phase2-best-practices.md`: 마찬가지로 역사적 산출물
- `_archive/` 내 파일들: 아카이브이므로 건드리지 않음

## 검증 결과

### 검증 1: 구조 검증 (23/23 PASS)
- 디렉토리 구조, 원본 삭제, frontmatter, 파일명, .gitignore 전부 통과

### 검증 2: 참조 검증 (5/5 PASS)
- 깨진 참조 없음, 새 참조 정상, CLAUDE.md 섹션 정상, README.md 정상, 상호 참조 정상

### 추가 수정 사항
- test-plan.md 내 SECURITY.md 상대 경로 수정 (action-plans/에서 root로의 상대 경로 보정)

---
