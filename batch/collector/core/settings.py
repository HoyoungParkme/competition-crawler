"""설정과 실행 문맥.

조정값은 `batch/settings.toml`, 비밀값은 환경 변수로만 받는다(CCR-INFRA-001 4.1 · 5장).
실행 문맥은 워크플로 첫 스텝이 남긴 시작 시각과 실행 식별자에서 만든다(CCR-INFRA-001 8.1).
"""

from __future__ import annotations

import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from collector.shared.dates import kst_date_of

BATCH_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BATCH_DIR.parent


class RunModeError(Exception):
    """Actions 안에서 쓰기 여부 값이 `true`도 `false`도 아니다. 아무것도 하지 않고 실패한다."""


@dataclass(frozen=True)
class SourceSettings:
    timeout_seconds: float
    retries: int
    backoff_seconds: tuple[float, ...]
    retry_after_cap_seconds: float
    interval_seconds: float
    page_cap: int
    budget_seconds: float


@dataclass(frozen=True)
class JudgeSettings:
    model: str
    timeout_seconds: float
    retries: int
    concurrency: int
    max_output_tokens: int
    backoff_seconds: tuple[float, ...]


@dataclass(frozen=True)
class Settings:
    source: SourceSettings
    judge: JudgeSettings
    zero_count_days: int

    @classmethod
    def load(cls, env: Mapping[str, str], path: Path | None = None) -> Settings:
        """CCR-MS-001#Settings.load"""
        data = tomllib.loads((path or BATCH_DIR / "settings.toml").read_text(encoding="utf-8"))
        s, j = data["source"], data["judge"]
        model = (env.get("OPENAI_MODEL") or "").strip() or j["model"]
        return cls(
            source=SourceSettings(
                timeout_seconds=float(s["timeout_seconds"]),
                retries=int(s["retries"]),
                backoff_seconds=tuple(float(x) for x in s["backoff_seconds"]),
                retry_after_cap_seconds=float(s["retry_after_cap_seconds"]),
                interval_seconds=float(s["interval_seconds"]),
                page_cap=int(s["page_cap"]),
                budget_seconds=float(s["budget_seconds"]),
            ),
            judge=JudgeSettings(
                model=model,
                timeout_seconds=float(j["timeout_seconds"]),
                retries=int(j["retries"]),
                concurrency=int(j["concurrency"]),
                max_output_tokens=int(j["max_output_tokens"]),
                backoff_seconds=tuple(float(x) for x in j["backoff_seconds"]),
            ),
            zero_count_days=int(data["warning"]["zero_count_days"]),
        )


def _secret(env: Mapping[str, str], name: str) -> str | None:
    # 등록되지 않은 시크릿은 빈 문자열로 들어오므로 빈 값을 빠진 것으로 본다(CCR-INFRA-001 5장)
    value = (env.get(name) or "").strip()
    return value or None


@dataclass(frozen=True)
class Secrets:
    """비밀값 둘. 반드시 있어야 하는 것은 없다(CCR-UC-001 UC-A1 1d1)."""

    openai_api_key: str | None
    kaggle_api_token: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Secrets:
        """CCR-MS-001#Secrets.from_env"""
        return cls(
            openai_api_key=_secret(env, "OPENAI_API_KEY"),
            kaggle_api_token=_secret(env, "KAGGLE_API_TOKEN"),
        )

    def values(self) -> list[str]:
        """CCR-MS-001#Secrets.values"""
        return [v for v in (self.openai_api_key, self.kaggle_api_token) if v]


@dataclass(frozen=True)
class RunContext:
    """한 실행의 문맥. 기준일은 실행이 시작한 시각을 KST로 바꾼 날짜다(CCR-UC-001 0.1)."""

    run_id: str
    started_at: datetime
    base_date: date
    kind: str  # schedule · manual
    write: bool  # 목록에 쓰는 실행인가
    ignore_discards: bool
    ignore_discards_requested: bool
    in_actions: bool
    state_dir: Path
    state_from_main: bool  # 데이터 파일을 기본 브랜치 최신 판에서 꺼내 읽는가
    append_dir: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str], *, now: datetime | None = None) -> RunContext:
        """CCR-MS-001#RunContext.from_env"""
        in_actions = env.get("GITHUB_ACTIONS") == "true"
        dry_run_raw = env.get("DRY_RUN", "")
        if in_actions and dry_run_raw not in ("true", "false"):
            raise RunModeError(f"DRY_RUN 값이 true도 false도 아니다: {dry_run_raw!r}")
        # Actions 밖(개발자 PC)의 실행은 늘 목록에 쓰지 않는다(CCR-UC-001 UC-A1 1b5)
        write = in_actions and dry_run_raw == "false"

        started_raw = (env.get("RUN_STARTED_AT") or "").strip()
        if started_raw:
            started_at = datetime.fromisoformat(started_raw.replace("Z", "+00:00"))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
        else:
            started_at = now or datetime.now(UTC)
        base_date = kst_date_of(started_at)

        run_id = (
            env.get("RUN_ID") or ""
        ).strip() or f"local-{started_at.strftime('%Y%m%dT%H%M%S')}"
        kind = "schedule" if env.get("GITHUB_EVENT_NAME") == "schedule" else "manual"
        # 버림을 없는 것으로 보는 것은 목록에 쓰지 않는 실행에서만 뜻이 있다(CCR-INFRA-001 8.1)
        requested = env.get("IGNORE_DISCARDS") == "true"

        # 기본 브랜치에서 도는 Actions 실행은 시작할 때 받은 main이 곧 최신 판이다. 그 밖은
        # 작업 트리의 사본이 아니라 기본 브랜치 최신 판을 꺼내 읽는다(CCR-UC-001 UC-A1 1b7)
        if env.get("STATE_DIR"):
            state_dir, from_main = Path(env["STATE_DIR"]), False
        elif in_actions and env.get("GITHUB_REF") == "refs/heads/main":
            state_dir, from_main = REPO_ROOT / "data", False
        else:
            state_dir, from_main = Path(tempfile.mkdtemp(prefix="competition-state-")), True
        if env.get("APPEND_DIR"):
            append_dir = Path(env["APPEND_DIR"])
        elif env.get("RUNNER_TEMP"):
            append_dir = Path(env["RUNNER_TEMP"]) / "append"
        else:
            append_dir = Path(tempfile.gettempdir()) / "competition-crawler-append"
        return cls(
            run_id=run_id,
            started_at=started_at,
            base_date=base_date,
            kind=kind,
            write=write,
            ignore_discards=requested and not write,
            ignore_discards_requested=requested,
            in_actions=in_actions,
            state_dir=state_dir,
            state_from_main=from_main,
            append_dir=append_dir,
        )


def read_dotenv(path: Path) -> dict[str, str]:
    """CCR-MS-001#settings.read_dotenv

    로컬 실행용 `.env`. `이름=값` 줄만 읽는다. 없으면 빈 것(CCR-INFRA-001 4.1).
    """
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name:
            values[name] = value
    return values
