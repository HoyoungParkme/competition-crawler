"""노트북 페이지 서버. 대회 목록 페이지와 그 페이지가 읽고 쓰는 두 데이터 파일을 127.0.0.1에만 낸다.

CCR-INFRA-001 8.11 · CCR-API-001 3.3. 파이썬 표준 라이브러리와 git만 쓰고 배치 패키지를 불러오지
않는다(finish.py와 같다). 데이터는 원본(싱크독 서버 저장소)의 bare 사본에서 바로 읽으므로 CDN 캐시가
없다. 상태 파일 쓰기는 GitHub Contents API와 같은 모양이다 — 판(sha)이 맞을 때만 그 파일 하나를 바꾼
커밋을 만들어 원본에 push한다. 토큰은 원본에 닿는 git 명령에만 명령 줄 설정으로 주고, 찍지 않는다.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

LIST_FILE = "data/competitions.jsonl"
STATUS_FILE = "data/status.json"
DATA_PATHS = {f"/{LIST_FILE}": LIST_FILE, f"/{STATUS_FILE}": STATUS_FILE}
CONTENTS_PATH = f"/api/contents/{STATUS_FILE}"
FETCH_INTERVAL = 1.0  # 초. 읽을 때 원본을 받되 이보다 자주는 받지 않는다
PUSH_ATTEMPTS = 3
GIT_TIMEOUT = 60
MAX_BODY = 1024 * 1024
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".jsonl": "application/x-ndjson; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}


@dataclass(frozen=True)
class Blob:
    sha: str  # git 블롭 해시. GitHub Contents API의 sha와 같은 값이다
    data: bytes


@dataclass(frozen=True)
class Person:
    name: str
    email: str


class Conflict(Exception):
    """판이 어긋났다(409). 페이지가 최신 판을 다시 읽고 한 번 더 쓴다."""


class ShaRequired(Exception):
    """파일이 있는데 판(sha)을 주지 않았다(422)."""


class RemoteError(Exception):
    """원본에 닿지 못했거나 git이 실패했다(502)."""


class Mirror:
    """원본의 bare 사본. 작업 트리 없이 git 배관 명령으로 읽고 쓴다."""

    def __init__(self, path: Path, remote: str, token: str | None) -> None:
        self.path = path
        self.remote = remote
        self._auth: list[str] = []
        if token:
            basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
            self._auth = ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]
        self._fetched_at: float | None = None
        self._fetch_lock = threading.Lock()
        self._write_lock = threading.Lock()
        if not (path / "HEAD").is_file():
            path.mkdir(parents=True, exist_ok=True)
            self._git("init", "--quiet", "--bare")

    def _run(
        self,
        args: list[str],
        *,
        auth: bool = False,
        data: bytes | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        command = ["git", "-C", str(self.path), *(self._auth if auth else []), *args]
        try:
            return subprocess.run(
                command, input=data, capture_output=True, timeout=GIT_TIMEOUT, env=env, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            # 명령 줄에는 토큰이 있으므로 찍지 않는다
            raise RemoteError(f"git {args[0]}을 끝내지 못했다: {type(exc).__name__}") from exc

    def _git(self, *args: str, auth: bool = False, data: bytes | None = None, **env: str) -> str:
        done = self._run(
            list(args), auth=auth, data=data, env={**os.environ, **env} if env else None
        )
        if done.returncode != 0:
            raise RemoteError(f"git {args[0]} 실패: {done.stderr.decode(errors='replace')[-300:]}")
        return done.stdout.decode(errors="replace").strip()

    def refresh(self, force: bool = False) -> None:
        """CCR-MS-001#Mirror.refresh"""
        with self._fetch_lock:
            now = time.monotonic()
            if (
                not force
                and self._fetched_at is not None
                and now - self._fetched_at < FETCH_INTERVAL
            ):
                return
            refspec = "+refs/heads/main:refs/heads/main"
            self._git("fetch", "--quiet", "--no-tags", "--depth=1", self.remote, refspec, auth=True)
            self._fetched_at = time.monotonic()

    def read(self, file: str) -> Blob | None:
        """CCR-MS-001#Mirror.read"""
        found = self._run(["rev-parse", "--verify", "--quiet", f"refs/heads/main:{file}"])
        sha = found.stdout.decode().strip()
        if found.returncode != 0 or not sha:
            return None  # main이 아직 없거나 그 파일이 없다
        shown = self._run(["cat-file", "blob", sha])
        if shown.returncode != 0:
            raise RemoteError(f"{file}을 꺼내지 못했다")
        return Blob(sha=sha, data=shown.stdout)

    def _commit(self, file: str, data: bytes, message: str, author: Person) -> tuple[str, str]:
        blob = self._git("hash-object", "-w", "--stdin", data=data)
        parent = self._git("rev-parse", "--verify", "refs/heads/main")
        with tempfile.TemporaryDirectory() as tmp:
            index = str(Path(tmp) / "index")
            self._git("read-tree", parent, GIT_INDEX_FILE=index)
            self._git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{file}",
                GIT_INDEX_FILE=index,
            )
            tree = self._git("write-tree", GIT_INDEX_FILE=index)
        commit = self._git(
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            message,
            GIT_AUTHOR_NAME=author.name,
            GIT_AUTHOR_EMAIL=author.email,
            GIT_COMMITTER_NAME=author.name,
            GIT_COMMITTER_EMAIL=author.email,
        )
        return commit, blob

    def _push(self, commit: str) -> bool:
        done = self._run(["push", "--quiet", self.remote, f"{commit}:refs/heads/main"], auth=True)
        if done.returncode == 0:
            return True
        err = done.stderr.decode(errors="replace")
        if "rejected" in err or "non-fast-forward" in err or "fetch first" in err:
            return False  # 그사이 main이 움직였다(배치의 커밋 등)
        raise RemoteError(f"git push 실패: {err[-300:]}")

    def write(self, file: str, data: bytes, sha: str | None, message: str, author: Person) -> str:
        """CCR-MS-001#Mirror.write"""
        with self._write_lock:
            for _ in range(PUSH_ATTEMPTS):
                self.refresh(force=True)
                current = self.read(file)
                if current is not None and sha is None:
                    raise ShaRequired(f"{file}이 있는데 판(sha)이 없다")
                if (current.sha if current is not None else None) != sha:
                    raise Conflict(f"{file}의 판이 어긋났다")
                commit, blob = self._commit(file, data, message, author)
                if self._push(commit):
                    self._git("update-ref", "refs/heads/main", commit)
                    return blob
            raise RemoteError(f"{PUSH_ATTEMPTS}번 모두 올리지 못했다")


def allowed(host: str, origin: str | None, port: int, write: bool) -> bool:
    """CCR-MS-001#page_server.allowed"""
    hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}
    if host not in hosts:
        return False  # 다른 이름을 127.0.0.1로 돌린 요청(DNS rebinding)
    if write:
        return origin in {f"http://{h}" for h in hosts}  # 다른 사이트의 쓰기(CSRF)
    return True


class PageHandler(BaseHTTPRequestHandler):
    server_version = "ccr-page"

    def _reply(self, status: int, body: bytes, content_type: str, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self._reply(status, body, "application/json; charset=utf-8")

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json(status, {"message": message})

    def _guarded(self, write: bool) -> bool:
        port = self.server.server_address[1]
        if allowed(self.headers.get("Host", ""), self.headers.get("Origin"), port, write):
            return True
        self._error(HTTPStatus.FORBIDDEN, "이 주소로는 받지 않는다")
        return False

    def _fresh(self) -> None:
        mirror: Mirror = self.server.mirror  # type: ignore[attr-defined]
        try:
            mirror.refresh()
        except RemoteError as exc:
            # 원본에 닿지 못해도 마지막으로 받은 판은 보여 준다. 쓰기는 502로 드러난다
            self.log_message("원본을 받지 못했다: %s", exc)

    def do_GET(self) -> None:
        """http.server가 GET마다 부르는 자리. serve_get으로 넘긴다."""
        self.serve_get()

    def do_PUT(self) -> None:
        """http.server가 PUT마다 부르는 자리. serve_put으로 넘긴다."""
        self.serve_put()

    def serve_get(self) -> None:
        """CCR-MS-001#PageHandler.serve_get"""
        if not self._guarded(write=False):
            return
        mirror: Mirror = self.server.mirror  # type: ignore[attr-defined]
        path = unquote(urlsplit(self.path).path)
        if path in DATA_PATHS or path == CONTENTS_PATH:
            self._fresh()
            blob = mirror.read(DATA_PATHS.get(path, STATUS_FILE))
            if blob is None:
                self._error(HTTPStatus.NOT_FOUND, "아직 없다")
            elif path == CONTENTS_PATH:
                content = base64.b64encode(blob.data).decode()
                self._json(HTTPStatus.OK, {"sha": blob.sha, "content": content})
            else:
                self._reply(HTTPStatus.OK, blob.data, TYPES[Path(path).suffix])
            return
        dist: Path = self.server.dist  # type: ignore[attr-defined]
        target = (dist / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
        if not target.is_relative_to(dist.resolve()) or not target.is_file():
            self._error(HTTPStatus.NOT_FOUND, "없는 주소")
            return
        content_type = TYPES.get(target.suffix, "application/octet-stream")
        self._reply(HTTPStatus.OK, target.read_bytes(), content_type, cache="no-cache")

    def serve_put(self) -> None:
        """CCR-MS-001#PageHandler.serve_put"""
        if not self._guarded(write=True):
            return
        if unquote(urlsplit(self.path).path) != CONTENTS_PATH:
            self._error(HTTPStatus.NOT_FOUND, "쓸 수 있는 파일은 상태 파일 하나다")
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY:
            self._error(HTTPStatus.BAD_REQUEST, "본문이 없거나 너무 크다")
            return
        try:
            body = json.loads(self.rfile.read(length))
            message, sha = body["message"], body.get("sha")
            person = body.get("author") or body["committer"]
            author = Person(name=person["name"], email=person["email"])
            data = base64.b64decode("".join(body["content"].split()), validate=True)
            if not (isinstance(message, str) and message.strip()):
                raise ValueError("message")
            if not (sha is None or isinstance(sha, str)):
                raise ValueError("sha")
            if not (isinstance(author.name, str) and isinstance(author.email, str)):
                raise ValueError("author")
        except (ValueError, KeyError, TypeError, AttributeError, binascii.Error):
            self._error(HTTPStatus.BAD_REQUEST, "본문의 모양이 틀렸다")
            return
        mirror: Mirror = self.server.mirror  # type: ignore[attr-defined]
        try:
            new_sha = mirror.write(STATUS_FILE, data, sha, message, author)
        except Conflict as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
            return
        except ShaRequired as exc:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY, str(exc))
            return
        except RemoteError as exc:
            self.log_message("쓰기 실패: %s", exc)
            self._error(HTTPStatus.BAD_GATEWAY, "원본(싱크독)에 쓰지 못했다")
            return
        status = HTTPStatus.CREATED if sha is None else HTTPStatus.OK
        self._json(status, {"content": {"sha": new_sha}})


def _serve(port: int, mirror: Mirror, dist: Path) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), PageHandler)
    server.daemon_threads = True
    server.mirror = mirror  # type: ignore[attr-defined]
    server.dist = dist  # type: ignore[attr-defined]
    return server


def main() -> int:
    """CCR-MS-001#page_server.main"""
    env = os.environ
    remote = env.get("CCR_REMOTE")
    if not remote:
        print("환경 변수 CCR_REMOTE가 없다")
        return 1
    port = int(env.get("PAGE_PORT") or "8090")
    home = Path.home()
    dist = Path(env.get("PAGE_DIST") or Path(__file__).resolve().parents[1] / "frontend" / "dist")
    mirror_path = Path(env.get("PAGE_MIRROR") or home / ".local/share/ccr/page.git")
    mirror = Mirror(mirror_path, remote, env.get("CCR_TOKEN"))
    try:
        mirror.refresh(force=True)
    except RemoteError as exc:
        print(f"원본을 받지 못했다. 그래도 띄운다: {exc}")
    server = _serve(port, mirror, dist)
    print(f"페이지 서버 http://localhost:{port} — 정적 파일 {dist}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
