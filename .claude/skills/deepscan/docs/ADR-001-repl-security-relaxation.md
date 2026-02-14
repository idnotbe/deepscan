# ADR-001: REPL Security Restriction Relaxation

## Status
**Accepted** (2026-01-21)

## Context

DeepScan REPL의 초기 보안 설계는 매우 보수적이었습니다:
- 21개의 AST 노드만 허용 (화이트리스트 방식)
- Lambda, List Comprehension 등 함수형 기능 차단
- 키워드 인자 사용 불가

이로 인해 실용적인 코드 분석이 불가능했습니다:
```python
# 불가능했던 코드들
[x for x in results if x > 0]          # ListComp 차단
filter(lambda x: x > 0, results)       # Lambda 차단
sorted(data, reverse=True)             # keyword 차단
```

## Decision

### 허용하기로 결정한 항목

| AST 노드 | 용도 | 허용 근거 |
|----------|------|----------|
| `ast.ListComp` | `[x for x in y]` | 데이터 필터링/변환에 필수 |
| `ast.DictComp` | `{k: v for ...}` | 딕셔너리 생성에 필요 |
| `ast.SetComp` | `{x for x in y}` | 중복 제거에 유용 |
| `ast.GeneratorExp` | `(x for x in y)` | 메모리 효율적 순회 |
| `ast.comprehension` | for 루프 부분 | 컴프리헨션 내부 구조 |
| `ast.Lambda` | `lambda x: x` | 고차 함수 사용에 필수 |
| `ast.arguments` | 람다 파라미터 | Lambda 작동에 필요 |
| `ast.arg` | 개별 인자 | Lambda 작동에 필요 |
| `ast.keyword` | `func(key=val)` | 키워드 인자 사용에 필수 |

| Builtin | 용도 | 허용 근거 |
|---------|------|----------|
| `dir()` | 네임스페이스 검사 | 디버깅에 유용, 부작용 없음 |
| `vars()` | 변수 확인 | 디버깅에 유용 |
| `hasattr()` | 속성 존재 확인 | getattr 없이 안전하게 확인 |
| `callable()` | 호출 가능 여부 | 타입 검사에 유용 |
| `id()` | 객체 ID | 디버깅에 유용 |

### 여전히 차단하는 항목 (의도적)

#### 1. 코드 실행 우회 방지 (Critical)

| 패턴/노드 | 차단 이유 |
|----------|----------|
| `getattr()` | 런타임에 동적으로 속성 접근 가능 → 모든 정적 분석 우회 가능 |
| `setattr()` | 객체 속성 변조 가능 |
| `delattr()` | 객체 속성 삭제 가능 |
| `exec()` | 임의 코드 실행 |
| `eval()` | 임의 표현식 평가 |
| `compile()` | 코드 객체 생성 |
| `__import__()` | 모듈 동적 임포트 |

**getattr이 위험한 이유:**
```python
# 문자열 결합으로 모든 패턴 검사 우회 가능
attr = "__cla" + "ss__"
getattr(obj, attr)  # → obj.__class__ 접근 성공
```

#### 2. 모듈 시스템 접근 차단

| AST 노드 | 차단 이유 |
|----------|----------|
| `ast.Import` | 외부 모듈 로드 (os, subprocess 등) |
| `ast.ImportFrom` | 특정 모듈에서 임포트 |

#### 3. 함수/클래스 정의 차단

| AST 노드 | 차단 이유 |
|----------|----------|
| `ast.FunctionDef` | 복잡한 로직 숨김 가능 |
| `ast.AsyncFunctionDef` | 비동기 함수 정의 |
| `ast.ClassDef` | 클래스 정의로 메타프로그래밍 가능 |

#### 4. 스코프 탈출 차단

| AST 노드 | 차단 이유 |
|----------|----------|
| `ast.Global` | 전역 변수 접근 |
| `ast.Nonlocal` | 외부 스코프 변수 접근 |

#### 5. Dunder 속성 접근 차단

| 패턴 | 차단 이유 |
|------|----------|
| `__class__` | 객체의 클래스 접근 → 메타클래스 조작 |
| `__bases__` | 상속 체인 접근 |
| `__subclasses__` | 하위 클래스 열거 → 취약한 클래스 탐색 |
| `__globals__` | 전역 네임스페이스 접근 |
| `__code__` | 함수 바이트코드 접근 |
| `__builtins__` | 내장 함수 딕셔너리 접근 |

**Dunder 접근이 위험한 이유 (Python Jail Escape):**
```python
# 클래식한 샌드박스 탈출 기법
().__class__.__bases__[0].__subclasses__()[X]  # → 위험한 클래스 접근
```

## Security Architecture

### 다단계 방어 체계

```
User Input (code)
     ↓
[Layer 1] FORBIDDEN_PATTERNS (정규식)
     │ - __import__, exec, eval, getattr 등
     ↓
[Layer 2] AST Node Whitelist
     │ - 허용된 노드만 통과
     ↓
[Layer 3] Dangerous Attribute Check
     │ - __로 시작하는 속성 차단
     ↓
[Layer 4] Safe Namespace
     │ - SAFE_BUILTINS만 제공
     ↓
[Layer 5] Resource Limits
     │ - 5초 타임아웃
     │ - (메모리 제한: 현재 미구현, Phase 8 예정)
     ↓
Execution
```

### DoS 방어

Lambda와 Comprehension은 DoS 공격에 사용될 수 있습니다:
```python
[x for x in range(10**9)]  # 메모리 폭발
```

이는 **Layer 5 (Resource Limits)**에서 방어합니다:
- CPU 타임아웃: 5초 (기본값)
- 메모리 관리: GC 트리거 (500MB 임계값) - 애플리케이션 레벨
- 프로세스 격리: SafeREPLExecutor

> **Note**: 하드 메모리 제한 (cgroups/rlimit)은 현재 미구현입니다.
> 프로덕션 배포 시 Docker `--memory` 플래그 사용을 권장합니다.
> See [SECURITY.md](./SECURITY.md) §3.3 for details.

## Consequences

### 긍정적
- 실용적인 코드 분석 가능
- 함수형 프로그래밍 패턴 사용 가능
- 데이터 필터링/변환 편리

### 부정적
- 공격 표면 증가 (9개 AST 노드 추가)
- DoS 위험 증가 (리소스 제한으로 완화)

### 중립적
- 보안 테스트 범위 확대 필요
- 문서화 유지보수 필요

## References

- [Python AST documentation](https://docs.python.org/3/library/ast.html)
- [Python Jail Escape techniques](https://book.hacktricks.xyz/generic-methodologies-and-resources/python/bypass-python-sandboxes)
- [ReDoS prevention](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-21 | Claude | Initial decision - relaxed REPL restrictions |
