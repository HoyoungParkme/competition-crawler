"""배치의 입구.

`python -m collector`로 하루치를 돌리고, `python -m collector collect`로 수집만 해 본다.

워크플로는 가상환경의 파이썬을 `exec`로 띄워 끊을 때 오는 신호를 이 프로세스가 받게 한다
(CCR-INFRA-001 8.1). 첫 신호에는 새 요청을 멈추고, 두 번째 신호에는 하던 호출도 끊는다.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
from datetime import UTC, datetime

from collector.core.logging import register_actions_masks, setup_logging
from collector.core.settings import (
    REPO_ROOT,
    RunContext,
    RunModeError,
    Secrets,
    Settings,
    read_dotenv,
)
from collector.domains.collect.adapters.aifactory import AiFactorySource
from collector.domains.collect.adapters.contestkorea import ContestKoreaSource
from collector.domains.collect.adapters.dacon import DaconSource
from collector.domains.collect.adapters.eventus import EventUsSource
from collector.domains.collect.adapters.kaggle import KaggleSource
from collector.domains.collect.adapters.wevity import WevitySource
from collector.domains.collect.ports import Source
from collector.domains.collect.service import CollectService
from collector.domains.list.crud import ListCrud
from collector.domains.list.service import ListService
from collector.domains.record.crud import RecordCrud
from collector.domains.record.models import RunResult
from collector.domains.record.service import RecordService
from collector.domains.screen.adapters.openai_judge import OpenAiJudge
from collector.domains.screen.service import ScreenService
from collector.infra.http import Stopped
from collector.run.pipeline import Pipeline, Services
from collector.shared.dates import kst_date_of

log = logging.getLogger("collector")

EXIT_FAILURE = 1
EXIT_RUN_MODE = 2
EXIT_STOPPED = 130


def _environment() -> dict[str, str]:
    env = dict(os.environ)
    if env.get("GITHUB_ACTIONS") != "true":
        # 로컬 실행만 `.env`를 읽는다. 이미 있는 환경 변수가 이긴다(CCR-INFRA-001 4.1)
        for name, value in read_dotenv(REPO_ROOT / ".env").items():
            env.setdefault(name, value)
    return env


def _install_signals(stop: threading.Event) -> None:
    def handle(signum: int, frame: object) -> None:
        if stop.is_set():
            raise Stopped()  # 두 번째 신호. 막혀 있는 호출도 끊는다
        stop.set()

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)


def sources_of(secrets: Secrets) -> list[Source]:
    """CCR-MS-001#__main__.sources_of"""
    return [
        EventUsSource(),
        DaconSource(),
        KaggleSource(secrets.kaggle_api_token),
        WevitySource(),
        AiFactorySource(),
        ContestKoreaSource(),
    ]


def run_batch(env: dict[str, str], stop: threading.Event) -> int:
    """CCR-MS-001#__main__.run_batch"""
    ctx = RunContext.from_env(env)
    settings = Settings.load(env)
    secrets = Secrets.from_env(env)
    collect = CollectService(settings.source, sources_of(secrets), stop)
    listing = ListService(ListCrud(ctx.state_dir, ctx.append_dir), write=ctx.write)
    crud = RecordCrud(
        ctx.state_dir, ctx.append_dir, export_from=REPO_ROOT if ctx.state_from_main else None
    )
    record = RecordService(crud, write=ctx.write, run_id=ctx.run_id, base_date=ctx.base_date)
    judge = (
        OpenAiJudge(settings.judge, secrets.openai_api_key, stop)
        if secrets.openai_api_key
        else None
    )
    screen = ScreenService(
        record,
        base_date=ctx.base_date,
        ignore_discards=ctx.ignore_discards,
        judge=judge,
        concurrency=settings.judge.concurrency,
        stop=stop,
    )
    log.info("판별 모델 %s", settings.judge.model)
    line = Pipeline(
        ctx, settings, Services(collect.collect_all, listing, record, screen), stop
    ).run()
    return 0 if line.result is RunResult.SUCCESS else EXIT_FAILURE


def run_collect(env: dict[str, str], stop: threading.Event, only: str | None, show: bool) -> int:
    """CCR-MS-001#__main__.run_collect

    수집만 한다. OpenAI를 부르지 않고 파일에 아무것도 쓰지 않는다(CCR-UC-001 UC-A3 진단용).
    """
    settings = Settings.load(env)
    secrets = Secrets.from_env(env)
    sources = [
        s for s in sources_of(secrets) if only is None or str(s.name).lower() == only.lower()
    ]
    if not sources:
        print(f"소스 이름을 모른다: {only}", file=sys.stderr)
        return EXIT_FAILURE
    started = (env.get("RUN_STARTED_AT") or "").strip()
    moment = (
        datetime.fromisoformat(started.replace("Z", "+00:00")) if started else datetime.now(UTC)
    )
    base_date = kst_date_of(moment)
    results = CollectService(settings.source, sources, stop).collect_all(base_date)
    for result in results:
        status = f"실패({result.failure}: {result.detail})" if result.failure else "성공"
        print(
            f"{result.source}\t{status}\t수집 {result.collected}"
            f"\t정규화 뒤 {result.normalized}\t탈락 {result.dropped}"
        )
        if show:
            for c in sorted(
                result.competitions, key=lambda c: (c.deadline or datetime.max.date(), c.title)
            ):
                dates = f"{c.start_date or '-'}~{c.deadline or '-'}"
                print(f"  {c.source_id}\t{dates}\t{c.title}\t{c.link}")
    return 0 if any(r.failure is None for r in results) else EXIT_FAILURE


def main(argv: list[str] | None = None) -> int:
    """CCR-MS-001#__main__.main"""
    parser = argparse.ArgumentParser(prog="collector", description="AI·개발 대회 일배치")
    sub = parser.add_subparsers(dest="command")
    collect = sub.add_parser(
        "collect", help="수집만 해 본다. OpenAI를 부르지 않고 아무것도 쓰지 않는다"
    )
    collect.add_argument("--source", help="이 소스만(예: wevity)")
    collect.add_argument("--show", action="store_true", help="대회를 한 줄씩 찍는다")
    args = parser.parse_args(argv)

    env = _environment()
    secrets = Secrets.from_env(env)
    if env.get("GITHUB_ACTIONS") == "true":
        register_actions_masks(secrets.values())  # 어떤 출력보다 먼저(CCR-INFRA-001 5.4)
    setup_logging(secrets.values())
    stop = threading.Event()
    _install_signals(stop)
    try:
        if args.command == "collect":
            return run_collect(env, stop, args.source, args.show)
        return run_batch(env, stop)
    except RunModeError as exc:
        log.error("%s. 아무것도 하지 않고 끝낸다", exc)
        return EXIT_RUN_MODE
    except Stopped:
        # 줄은 마무리 단계가 중단으로 쓴다. 판별 스레드를 기다리지 않고 곧바로 끝낸다
        log.warning("신호를 받아 멈췄다. 실행 요약 줄은 쓰지 않는다")
        logging.shutdown()
        sys.stdout.flush()
        os._exit(EXIT_STOPPED)
    except Exception:
        # 줄을 남기지 않고 멈춘다. 마무리 단계가 중단으로 쓴다(CCR-UC-001 UC-A1 *a)
        log.exception("예상하지 못한 오류로 멈췄다")
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())
