"""노션 `대회목록`에 닿는 호출만 둔다(CCR-API-001 3.3).

행과 컬럼을 읽고 만드는 네 호출뿐이다. 기존 행을 고치거나 지우는 호출은 두지 않는다
(CCR-PRD-001 R6 · CCR-DOM-001 4.2 규칙 3).
"""

from __future__ import annotations

from typing import Any

from collector.infra.notion import NotionFailure, NotionHttp, WriteResponse

PAGE_SIZE = 100


class NotionCrud:
    def __init__(self, http: NotionHttp, data_source_id: str) -> None:
        self._http = http
        self._id = data_source_id

    def query_pages(self) -> list[dict[str, Any]]:
        """모든 행. 거르거나 정렬하지 않는다. 다 읽지 못했으면 NotionFailure."""
        pages: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": PAGE_SIZE}
            if cursor:
                body["start_cursor"] = cursor
            data = self._http.read("POST", f"/v1/data_sources/{self._id}/query", json=body)
            status = (data.get("request_status") or {}).get("type")
            if status == "incomplete":
                raise NotionFailure("질의 결과가 다 오지 않았다(request_status incomplete)")
            results = data.get("results")
            if not isinstance(results, list):
                raise NotionFailure("results가 배열이 아니다")
            pages.extend(r for r in results if isinstance(r, dict))
            cursor = data.get("next_cursor")
            if not data.get("has_more") or not cursor:
                return pages

    def get_data_source(self) -> dict[str, Any]:
        return self._http.read("GET", f"/v1/data_sources/{self._id}")

    def add_properties(self, properties: dict[str, Any]) -> None:
        """없는 컬럼만 보낸다. 있는 컬럼을 보내면 그 설정이 바뀐다(CCR-API-001 PATCH)."""
        self._http.write("PATCH", f"/v1/data_sources/{self._id}", json={"properties": properties})

    def create_page(self, properties: dict[str, Any]) -> WriteResponse:
        parent = {"type": "data_source_id", "data_source_id": self._id}
        return self._http.write("POST", "/v1/pages", json={"parent": parent, "properties": properties})
