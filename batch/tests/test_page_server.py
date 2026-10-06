"""노트북 페이지 서버(CCR-INFRA-001 8.11 · CCR-API-001 3.3)를 로컬 bare 저장소를 원본으로 삼아 띄워 본다."""

from __future__ import annotations

import base64
import http.client
import json
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

import page_server
from page_server import Mirror

AUTHOR = {"name": "Hoyoung Park", "email": "HoyoungParkme@users.noreply.github.com"}
STATUS = '{\n  "DACON:1": {\n    "hidden": false,\n    "status": "done"\n  }\n}\n'


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def seed(tmp_path: Path, *, status: bool = True) -> Path:
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "--quiet", "--bare", "-b", "main", str(remote))
    work = tmp_path / "seed"
    git(tmp_path, "clone", "--quiet", str(remote), str(work))
    (work / "data").mkdir()
    (work / "data" / "competitions.jsonl").write_text('{"id": "DACON:1"}\n', encoding="utf-8")
    if status:
        (work / "data" / "status.json").write_text(STATUS, encoding="utf-8")
    git(work, "add", ".")
    git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "seed")
    git(work, "push", "--quiet", "origin", "HEAD:main")
    return remote


class Page:
    def __init__(self, port: int, remote: Path, mirror: Mirror) -> None:
        self.port, self.remote, self.mirror = port, remote, mirror

    def request(
        self,
        method: str,
        path: str,
        body: object = None,
        *,
        host: str | None = None,
        origin: str | None = "same",
    ) -> tuple[int, dict, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        headers = {"Host": host or f"localhost:{self.port}"}
        if origin == "same":
            headers["Origin"] = f"http://localhost:{self.port}"
        elif origin is not None:
            headers["Origin"] = origin
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        response = conn.getresponse()
        payload = response.read()
        conn.close()
        return response.status, dict(response.getheaders()), payload

    def put_status(
        self, text: str, sha: str | None, message: str = "status: 대회 1 → 참가"
    ) -> tuple:
        body: dict = {
            "message": message,
            "content": base64.b64encode(text.encode()).decode(),
            "author": AUTHOR,
            "committer": AUTHOR,
        }
        if sha is not None:
            body["sha"] = sha
        return self.request("PUT", "/api/contents/data/status.json", body)


def start(tmp_path: Path, remote: Path) -> Iterator[Page]:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>대회 목록</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    mirror = Mirror(tmp_path / "page.git", str(remote), "tok-secret")
    server = page_server._serve(0, mirror, dist)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield Page(server.server_address[1], remote, mirror)
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def page(tmp_path: Path) -> Iterator[Page]:
    yield from start(tmp_path, seed(tmp_path))


def blob_sha(remote: Path, file: str = "data/status.json") -> str:
    return git(remote, "rev-parse", f"main:{file}")


def test_reads_both_data_files_from_main_without_cache(page: Page) -> None:
    status, headers, body = page.request("GET", "/data/competitions.jsonl")
    assert (status, body) == (200, b'{"id": "DACON:1"}\n')
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Type"].startswith("application/x-ndjson")
    status, _, body = page.request("GET", "/data/status.json?t=1")
    assert (status, body.decode()) == (200, STATUS)


def test_contents_gives_the_blob_sha_and_base64(page: Page) -> None:
    status, _, body = page.request("GET", "/api/contents/data/status.json")
    got = json.loads(body)
    assert status == 200
    assert got["sha"] == blob_sha(page.remote)
    assert base64.b64decode(got["content"]).decode() == STATUS


def test_write_with_the_right_sha_makes_one_commit_of_that_file(page: Page) -> None:
    before = git(page.remote, "rev-parse", "main")
    new = STATUS.replace("done", "joined")
    status, _, body = page.put_status(new, blob_sha(page.remote))
    assert status == 200
    assert json.loads(body) == {"content": {"sha": blob_sha(page.remote)}}
    assert git(page.remote, "rev-parse", "main~1") == before
    assert git(page.remote, "show", "main:data/status.json") + "\n" == new
    log = git(page.remote, "log", "-1", "--format=%an <%ae>|%cn|%s", "main")
    assert log == f"{AUTHOR['name']} <{AUTHOR['email']}>|{AUTHOR['name']}|status: 대회 1 → 참가"
    changed = git(page.remote, "show", "--name-only", "--format=", "main").split()
    assert changed == ["data/status.json"]  # 목록 파일은 건드리지 않는다
    # 곧바로 보인다 — CDN 캐시가 없다
    assert page.request("GET", "/data/status.json")[2].decode() == new


def test_stale_sha_is_409_and_missing_sha_is_422(page: Page) -> None:
    head = git(page.remote, "rev-parse", "main")
    assert page.put_status("{}\n", "0" * 40)[0] == 409
    assert page.put_status("{}\n", None)[0] == 422
    assert git(page.remote, "rev-parse", "main") == head  # 아무것도 올리지 않았다


def test_first_write_creates_the_file(tmp_path: Path) -> None:
    for page in start(tmp_path, seed(tmp_path, status=False)):
        assert page.request("GET", "/api/contents/data/status.json")[0] == 404
        assert page.request("GET", "/data/status.json")[0] == 404
        status, _, body = page.put_status("{}\n", None)
        assert status == 201
        assert json.loads(body)["content"]["sha"] == blob_sha(page.remote)


def test_reapplies_when_the_batch_pushed_in_between(page: Page, tmp_path: Path) -> None:
    """배치가 그사이 데이터 커밋을 올리면 push가 거절된다. 다시 받아 같은 판 위에 다시 얹는다."""
    other = tmp_path / "batch"
    git(tmp_path, "clone", "--quiet", str(page.remote), str(other))
    real = page.mirror._push
    calls: list[str] = []

    def racing(commit: str) -> bool:
        if not calls:  # 첫 push 직전에 배치가 끼어든다
            (other / "data" / "competitions.jsonl").write_text("{}\n", encoding="utf-8")
            git(other, "-c", "user.name=b", "-c", "user.email=b@b", "commit", "-qam", "batch")
            git(other, "push", "--quiet", "origin", "HEAD:main")
        calls.append(commit)
        return real(commit)

    page.mirror._push = racing  # type: ignore[method-assign]
    status, _, _ = page.put_status(STATUS.replace("done", "joined"), blob_sha(page.remote))
    assert status == 200
    assert len(calls) == 2
    subjects = git(page.remote, "log", "-3", "--format=%s", "main").splitlines()
    assert subjects == ["status: 대회 1 → 참가", "batch", "seed"]


def test_host_and_origin_guard(page: Page) -> None:
    assert page.request("GET", "/data/status.json", host="evil.example:8090")[0] == 403
    assert page.request("GET", "/", host=f"evil.example:{page.port}")[0] == 403
    assert page.request("GET", "/data/status.json", host=f"127.0.0.1:{page.port}")[0] == 200
    body = {"message": "x", "content": "e30K", "author": AUTHOR}
    path = "/api/contents/data/status.json"
    assert page.request("PUT", path, body, origin="http://evil.example")[0] == 403
    assert page.request("PUT", path, body, origin=None)[0] == 403


def test_allowed_rules() -> None:
    assert page_server.allowed("localhost:8090", None, 8090, write=False)
    assert page_server.allowed("127.0.0.1:8090", "http://127.0.0.1:8090", 8090, write=True)
    assert not page_server.allowed("localhost:8091", None, 8090, write=False)
    assert not page_server.allowed("localhost:8090", "http://localhost:5173", 8090, write=True)
    assert not page_server.allowed("localhost:8090", None, 8090, write=True)


def test_static_files_and_bad_requests(page: Page) -> None:
    status, headers, body = page.request("GET", "/")
    assert status == 200 and "대회 목록" in body.decode()
    assert headers["Content-Type"].startswith("text/html")
    assert page.request("GET", "/assets/app.js")[0] == 200
    assert page.request("GET", "/../origin.git/HEAD")[0] == 404
    assert page.request("GET", "/nope.html")[0] == 404
    assert page.request("PUT", "/api/contents/data/competitions.jsonl", {"x": 1})[0] == 404
    path = "/api/contents/data/status.json"
    assert page.request("PUT", path, {"message": "x", "content": "@@", "author": AUTHOR})[0] == 400
    assert page.request("PUT", path, {"content": "e30K", "author": AUTHOR})[0] == 400


def test_remote_down_shows_the_last_copy_and_refuses_writes(page: Page) -> None:
    sha = blob_sha(page.remote)
    assert page.request("GET", "/data/status.json")[0] == 200
    shutil.rmtree(page.remote)
    status, _, body = page.request("GET", "/data/status.json")
    assert (status, body.decode()) == (200, STATUS)  # 마지막으로 받은 판
    status, _, body = page.put_status("{}\n", sha)
    assert status == 502
    assert b"tok-secret" not in body
