from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from collector.core.settings import (
    REPO_ROOT,
    RunContext,
    RunModeError,
    Secrets,
    Settings,
    read_dotenv,
)

ACTIONS = {
    "GITHUB_ACTIONS": "true",
    "RUN_STARTED_AT": "2026-09-26T23:50:12Z",
    "RUN_ID": "123-1",
    "GITHUB_EVENT_NAME": "schedule",
    "GITHUB_REF": "refs/heads/main",
    "RUNNER_TEMP": "/tmp/runner",
}


def test_scheduled_run_on_main_writes() -> None:
    ctx = RunContext.from_env({**ACTIONS, "DRY_RUN": "false"})
    assert ctx.write is True
    assert ctx.base_date == date(2026, 9, 27)
    assert ctx.kind == "schedule"
    assert ctx.run_id == "123-1"
    assert ctx.state_dir == REPO_ROOT / "data"
    assert ctx.state_from_main is False
    assert ctx.append_dir == Path("/tmp/runner/append")


@pytest.mark.parametrize("value", ["", "True", "1", "yes"])
def test_broken_dry_run_value_in_actions_does_nothing(value: str) -> None:
    with pytest.raises(RunModeError):
        RunContext.from_env({**ACTIONS, "DRY_RUN": value})


def test_outside_actions_never_writes_and_reads_main_state() -> None:
    ctx = RunContext.from_env({"DRY_RUN": "false"}, now=datetime(2026, 9, 27, 0, 0, tzinfo=UTC))
    assert ctx.write is False
    assert ctx.state_from_main is True
    assert ctx.run_id.startswith("local-")


def test_branch_run_reads_main_state() -> None:
    ctx = RunContext.from_env({**ACTIONS, "DRY_RUN": "true", "GITHUB_REF": "refs/heads/feat/x"})
    assert ctx.write is False
    assert ctx.state_from_main is True


def test_ignore_discards_only_when_not_writing() -> None:
    writing = RunContext.from_env({**ACTIONS, "DRY_RUN": "false", "IGNORE_DISCARDS": "true"})
    assert writing.ignore_discards is False
    assert writing.ignore_discards_requested is True
    preview = RunContext.from_env({**ACTIONS, "DRY_RUN": "true", "IGNORE_DISCARDS": "true"})
    assert preview.ignore_discards is True


def test_manual_kind() -> None:
    ctx = RunContext.from_env(
        {**ACTIONS, "DRY_RUN": "true", "GITHUB_EVENT_NAME": "workflow_dispatch"}
    )
    assert ctx.kind == "manual"


def test_empty_secrets_count_as_missing() -> None:
    secrets = Secrets.from_env({"KAGGLE_API_TOKEN": "  ", "OPENAI_API_KEY": "k"})
    assert secrets.kaggle_api_token is None
    assert secrets.values() == ["k"]
    assert Secrets.from_env({}).values() == []  # 반드시 있어야 하는 시크릿은 없다


def test_settings_file_loads_and_model_can_be_overridden() -> None:
    settings = Settings.load({})
    assert settings.source.page_cap == 20
    assert settings.source.budget_seconds == 120
    assert settings.judge.concurrency == 4
    assert settings.zero_count_days == 3
    assert Settings.load({"OPENAI_MODEL": "gpt-5.6-luna"}).judge.model == "gpt-5.6-luna"
    assert Settings.load({"OPENAI_MODEL": " "}).judge.model == settings.judge.model


def test_read_dotenv(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# 주석\nKAGGLE_API_TOKEN='abc'\nexport OPENAI_MODEL=gpt-6-luna\nEMPTY=\nbroken line\n",
        encoding="utf-8",
    )
    assert read_dotenv(env) == {
        "KAGGLE_API_TOKEN": "abc",
        "OPENAI_MODEL": "gpt-6-luna",
        "EMPTY": "",
    }
    assert read_dotenv(tmp_path / "없음") == {}
