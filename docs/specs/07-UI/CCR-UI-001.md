---
doc_id: CCR-UI-001
type: UI
title: 화면 설계·와이어프레임 — 대회 목록 페이지
status: draft
upstream: [CCR-PRD-001, CCR-UC-001, CCR-INFRA-001, CCR-DOM-001]
---

# 화면 설계·와이어프레임 — 대회 목록 페이지

## 0. 이 문서가 다루는 것

사람이 마주하는 화면은 대회 목록 페이지 하나다([[CCR-PRD-001#R10]] · [[CCR-INFRA-001#C14]]). 배치가 저장소에 올린 목록 파일을 보여 주고, 사람이 상태를 바꾸거나 대회를 지우면 상태 파일에 커밋한다. 화면은 둘이다. 목록(UI-1)과, 그 위에 뜨는 설정 대화상자(UI-2)다. 검색·자유 정렬·통계·손으로 추가하기는 두지 않는다([[CCR-PRD-001]] 2장).

와이어프레임은 클로드의 Artifact Design 캔버스에서 1280×800 아트보드로 그렸고, 그 html을 아래 배치 블록에 그대로 옮겼다. 캔버스: https://claude.ai/artifact/UyUFTESag4eF8X3ZyYCjRr (비공개). 배치 블록의 `data-el` 번호가 요소 표의 `#`이다. 표 안의 대회 이름과 날짜는 예시이고, 실측이 없는 값은 `[대회명]`처럼 자리만 잡았다.

정하지 않는 것: 데이터 파일의 필드 이름(ERD), 저장소 API의 모양(API 명세), 컴포넌트와 파일 이름(클래스 명세).

## 1. 유스케이스 대응

| 유스케이스 | 화면 |
|---|---|
| [[CCR-UC-001#UC-A2]] 새로 들어온 대회를 훑고 참가할 것을 고른다 | UI-1 |
| [[CCR-UC-001#UC-H1]] 페이지에서 상태를 바꾸거나 대회를 지운다 | UI-1 |
| [[CCR-UC-001#UC-H2]] 페이지에 토큰을 넣거나 지운다 | UI-2 |

## 2. 화면 목록

| 화면 | 경로 | 한 줄 목적 |
|---|---|---|
| UI-1 대회 목록 | `/` (`https://hoyoungparkme.github.io/competition-crawler/`) | 마감일 순 목록을 보고, 상태를 바꾸고, 관심 없는 대회를 지운다 |
| UI-2 설정 대화상자 | `/`(UI-1 위에 뜸) | 저장소에 쓸 GitHub 토큰을 넣거나 지운다 |

## UI-1 대회 목록

| 항목 | 내용 |
|---|---|
| 경로 | `/` |
| 주 유스케이스 | [[CCR-UC-001#UC-A2]] · [[CCR-UC-001#UC-H1]] |
| 진입 / 이탈 | 주소를 열면 바로 이 화면 / 없음. 링크(7.2)는 새 창으로 열리고, 설정(6)은 이 화면 위에 UI-2를 띄운다 |
| 읽는 것 | 기본 브랜치의 `data/competitions.jsonl`·`data/status.json`([[CCR-INFRA-001]] 6.4) |
| 쓰는 것 | `data/status.json`만. 상태 셀렉트(7.4)·지우기(7.5)·되살리기(9.1)가 커밋한다([[CCR-INFRA-001]] 8.11) |

### 배치
```html
<style>
body{margin:0;font-family:"IBM Plex Sans KR",system-ui,sans-serif;background:#f4f2ec;color:#1d1c19}
a{color:#1f5f6b}a:hover{color:#143f47}
.cc-top{display:flex;align-items:center;gap:16px;padding:0 0 16px;border-bottom:1px solid #d9d5cb}
.cc-top h1{margin:0;font-size:22px;font-weight:600;letter-spacing:-0.01em}
.cc-sub{font-size:13px;color:#5c594f}
.cc-btn{font:inherit;font-size:14px;padding:9px 14px;border-radius:8px;border:1px solid #c9c4b7;background:#fff;color:#1d1c19;cursor:pointer;min-height:40px}
.cc-btn.primary{background:#1f5f6b;border-color:#1f5f6b;color:#fff}
.cc-btn.ghost{border-color:transparent;background:transparent;color:#5c594f}
.cc-sel{font:inherit;font-size:14px;padding:8px 10px;border-radius:8px;border:1px solid #c9c4b7;background:#fff;color:#1d1c19;min-height:40px}
.cc-bar{display:flex;align-items:center;gap:12px;padding:14px 0}
.cc-bar label{font-size:13px;color:#5c594f;display:flex;align-items:center;gap:6px}
.cc-tbl{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9d5cb;border-radius:10px;overflow:hidden}
.cc-tbl th{font-size:12px;font-weight:600;color:#5c594f;text-align:left;padding:10px 14px;background:#faf9f5;border-bottom:1px solid #d9d5cb}
.cc-tbl td{padding:12px 14px;border-bottom:1px solid #eceae3;font-size:14px;vertical-align:middle}
.cc-tbl tr:last-child td{border-bottom:0}
.cc-due{font-variant-numeric:tabular-nums;white-space:nowrap}
.cc-due.soon{color:#a13f1d;font-weight:600}
.cc-src{display:inline-block;font-size:12px;padding:2px 8px;border-radius:999px;background:#ecebe4;color:#3f3d36}
.cc-note{font-size:12px;color:#7a766b;margin-top:4px}
.cc-state{font:inherit;font-size:13px;padding:6px 8px;border-radius:8px;border:1px solid #c9c4b7;background:#fff;min-height:36px}
.cc-state.s1{background:#e6eef0;border-color:#9fbcc3}
.cc-state.s2{background:#e3ecdd;border-color:#8fae82}
.cc-fold{margin-top:16px;border:1px dashed #c9c4b7;border-radius:10px;padding:12px 14px;display:flex;align-items:center;gap:12px;font-size:14px;color:#5c594f;background:#faf9f5}
.cc-foot{display:flex;justify-content:space-between;align-items:center;padding-top:14px;font-size:12px;color:#7a766b}
.cc-toast{display:inline-flex;align-items:center;gap:8px;font-size:13px;padding:6px 12px;border-radius:8px;background:#fff7e6;border:1px solid #e3c98a;color:#5b4200}
</style>
<style>
body{margin:0;font-family:"IBM Plex Sans KR",system-ui,sans-serif;background:#f4f2ec;color:#1d1c19}
a{color:#1f5f6b}a:hover{color:#143f47}
.cc-btn{font:inherit;font-size:14px;padding:9px 14px;border-radius:8px;border:1px solid #c9c4b7;background:#fff;color:#1d1c19;cursor:pointer;min-height:40px}
.cc-btn.primary{background:#1f5f6b;border-color:#1f5f6b;color:#fff}
.cc-card{background:#fff;border:1px solid #d9d5cb;border-radius:10px;padding:16px 18px;display:flex;flex-direction:column;gap:10px}
.cc-cap{font-size:12px;color:#7a766b;text-transform:none;letter-spacing:.02em}
.cc-empty{text-align:center;padding:36px 16px;color:#5c594f;font-size:14px;line-height:1.6;border:1px dashed #c9c4b7;border-radius:10px;background:#faf9f5}
.cc-alert{display:flex;align-items:center;gap:10px;font-size:13px;padding:10px 12px;border-radius:8px}
.cc-alert.warn{background:#fff7e6;border:1px solid #e3c98a;color:#5b4200}
.cc-alert.err{background:#fbe9e4;border:1px solid #d9a898;color:#6b2412}
.cc-alert.info{background:#e6eef0;border:1px solid #9fbcc3;color:#163e46}
.cc-alert .sp{flex-grow:1}
.cc-row{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid #eceae3;border-radius:8px;font-size:14px;background:#fff}
.cc-state{font:inherit;font-size:13px;padding:6px 8px;border-radius:8px;border:1px solid #c9c4b7;background:#fff;min-height:36px}
</style>
<style>
.var{font:12px/1.4 system-ui,sans-serif;color:#7a766b;margin:20px 0 6px;padding-top:12px;border-top:1px solid #d9d5cb}
.cc-board{background:#f4f2ec;padding:24px 28px;border:1px solid #d9d5cb;border-radius:12px;display:flex;flex-direction:column;gap:10px}
</style>
<div data-el="0" style="width: 100%; max-width: 1280px; min-height: 800px; box-sizing: border-box; padding: 32px 40px; display: flex; flex-direction: column; gap: 0; background: #f4f2ec;">
  <header class="cc-top" data-el="1">
    <div style="display: flex; flex-direction: column; gap: 4px;">
      <h1 data-el="1.1">대회 목록</h1>
      <span class="cc-sub" data-el="1.2">마감일 순 · 2026-09-29 09:12 갱신 · 열린 대회 5</span>
    </div>
    <div style="flex-grow: 1;"></div>
    <span class="cc-toast" data-el="8"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>저장 중…</span>
    <button class="cc-btn ghost" data-el="2" type="button">새로 고침</button>
    <button class="cc-btn" data-el="6" type="button" aria-label="설정">설정</button>
  </header>

  <div class="cc-bar" data-el="3">
    <label>출처 <select class="cc-sel" data-el="3.1"><option>전체</option><option>event-us</option><option>DACON</option><option>Kaggle</option><option>wevity</option><option>AI팩토리</option><option>콘테스트코리아</option></select></label>
    <label>상태 <select class="cc-sel" data-el="3.2"><option>전체</option><option>시작 전</option><option>진행 중</option><option>제출</option><option>완료</option></select></label>
    <label><input type="checkbox" data-el="3.3"> 마감 지남·지운 대회 보기</label>
  </div>

  <table class="cc-tbl" data-el="7">
    <thead>
      <tr><th style="width: 120px;">마감</th><th>대회명</th><th style="width: 130px;">출처</th><th style="width: 110px;">수집일</th><th style="width: 130px;">상태</th><th style="width: 80px;"></th></tr>
    </thead>
    <tbody>
      <tr>
        <td class="cc-due soon" data-el="7.1">10-06 (D-7)</td>
        <td><a href="https://aifactory.space/" data-el="7.2">2026 국립공원 위성 모니터링 AI 챌린지</a><div class="cc-note" data-el="7.6">위성 영상 AI 분석 경진대회</div></td>
        <td><span class="cc-src" data-el="7.3">AI팩토리</span></td>
        <td class="cc-due">09-16</td>
        <td><select class="cc-state s2" data-el="7.4"><option>시작 전</option><option selected>진행 중</option><option>제출</option><option>완료</option></select></td>
        <td><button class="cc-btn ghost" data-el="7.5" type="button">지우기</button></td>
      </tr>
      <tr>
        <td class="cc-due">10-14</td>
        <td><a href="#">[대회명]</a><div class="cc-note">[판별 근거 한 줄]</div></td>
        <td><span class="cc-src">event-us</span></td>
        <td class="cc-due">09-29</td>
        <td><select class="cc-state"><option selected>시작 전</option><option>진행 중</option><option>제출</option><option>완료</option></select></td>
        <td><button class="cc-btn ghost" type="button">지우기</button></td>
      </tr>
      <tr>
        <td class="cc-due">10-31</td>
        <td><a href="#">[대회명]</a><div class="cc-note">[판별 근거 한 줄]</div></td>
        <td><span class="cc-src">DACON</span></td>
        <td class="cc-due">09-29</td>
        <td><select class="cc-state"><option selected>시작 전</option><option>진행 중</option><option>제출</option><option>완료</option></select></td>
        <td><button class="cc-btn ghost" type="button">지우기</button></td>
      </tr>
      <tr>
        <td class="cc-due">11-20</td>
        <td><a href="#">[Competition title]</a><div class="cc-note">[판별 근거 한 줄]</div></td>
        <td><span class="cc-src">Kaggle</span></td>
        <td class="cc-due">09-27</td>
        <td><select class="cc-state s1"><option>시작 전</option><option>진행 중</option><option selected>제출</option><option>완료</option></select></td>
        <td><button class="cc-btn ghost" type="button">지우기</button></td>
      </tr>
      <tr>
        <td class="cc-due">—</td>
        <td><a href="#">[대회명 · 마감일 없음]</a><div class="cc-note">[판별 근거 한 줄]</div></td>
        <td><span class="cc-src">wevity</span></td>
        <td class="cc-due">09-28</td>
        <td><select class="cc-state"><option selected>시작 전</option><option>진행 중</option><option>제출</option><option>완료</option></select></td>
        <td><button class="cc-btn ghost" type="button">지우기</button></td>
      </tr>
    </tbody>
  </table>

  <div class="cc-fold" data-el="9">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"></path></svg>
    <span>마감 지난 대회 12 · 지운 대회 3 — 접혀 있음. 펼치면 아래에 이어진다</span>
  </div>

  <div style="flex-grow: 1;"></div>
  <div class="cc-foot" data-el="1.3">
    <span>목록은 배치가 매일 08:50에 올리고, 상태는 이 페이지가 저장소에 저장한다</span>
    <span>HoyoungParkme/competition-crawler · main</span>
  </div>
</div>

<div class="var">빈 상태 (10) — 배치가 아직 한 번도 돌지 않았거나 목록 파일이 없을 때</div>
<div class="cc-board">
<div class="cc-empty" data-el="10">아직 대회가 없습니다.<br>배치가 매일 08:50에 저장소에 목록을 올립니다. 첫 실행 뒤 다시 열어 주세요.</div>
</div>

<div class="var">토큰 없음 (11) — 상태를 바꾸려 눌렀는데 토큰이 없을 때</div>
<div class="cc-board">
<div class="cc-alert warn" data-el="11">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4m0 4h.01M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0z"></path></svg>
      <span>저장하려면 GitHub 토큰이 필요합니다. 읽기는 그대로 됩니다.</span>
      <span class="sp"></span>
      <button class="cc-btn primary" type="button" data-el="11.1">설정 열기</button>
    </div>
    <div class="cc-row"><span style="width: 90px; color: #7a766b;">10-14</span><a href="#" style="flex-grow: 1;">[대회명]</a><select class="cc-state" disabled><option>시작 전</option></select></div>
</div>

<div class="var">저장 중 (8) — 셀렉트를 바꾼 직후. 화면은 먼저 바뀌고 커밋이 끝나면 표시가 사라진다</div>
<div class="cc-board">
<div class="cc-alert info">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>
      <span>저장 중… data/status.json에 커밋하고 있습니다</span>
    </div>
    <div class="cc-row"><span style="width: 90px; color: #7a766b;">10-06</span><a href="#" style="flex-grow: 1;">2026 국립공원 위성 모니터링 AI 챌린지</a><select class="cc-state" style="background: #e3ecdd; border-color: #8fae82;"><option>진행 중</option></select></div>
</div>

<div class="var">저장 실패 (12) — 판이 어긋나 한 번 다시 썼는데도 안 됐거나, 토큰이 거절됐을 때. 값은 바꾸기 전으로 되돌린다</div>
<div class="cc-board">
<div class="cc-alert err" data-el="12">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"></circle><path d="M15 9l-6 6m0-6 6 6"></path></svg>
      <span>저장하지 못했습니다 (401). 토큰이 만료됐거나 권한이 없습니다. 값을 이전으로 되돌렸습니다.</span>
      <span class="sp"></span>
      <button class="cc-btn" type="button" data-el="12.1">설정 열기</button>
      <button class="cc-btn primary" type="button" data-el="12.2">다시 시도</button>
    </div>
    <div class="cc-row"><span style="width: 90px; color: #7a766b;">10-06</span><a href="#" style="flex-grow: 1;">2026 국립공원 위성 모니터링 AI 챌린지</a><select class="cc-state"><option>시작 전</option></select></div>
</div>

<div class="var">접힌 구역을 펼쳤을 때 (9) — 마감 지난 대회와 지운 대회. 지운 대회는 되살리기 버튼이 있다</div>
<div class="cc-board">
<div class="cc-row" style="opacity: .75;"><span style="width: 90px; color: #7a766b;">09-18 지남</span><a href="#" style="flex-grow: 1;">2026 Big Data 활용 대회</a><span style="font-size: 12px; color: #7a766b;">event-us</span><select class="cc-state"><option>완료</option></select><button class="cc-btn" type="button">지우기</button></div>
    <div class="cc-row" style="opacity: .75;"><span style="width: 90px; color: #7a766b;">09-30</span><a href="#" style="flex-grow: 1; text-decoration: line-through;">2026 AI 창업 경진대회</a><span style="font-size: 12px; color: #7a766b;">event-us · 지움</span><button class="cc-btn" type="button" data-el="9.1">되살리기</button></div>
</div>

```

### 요소
| # | 이름 | 종류 | 보여주는 것 | 누르면 |
|---|---|---|---|---|
| 1 | 머리 | 영역 | 제목(1.1)과 요약 줄(1.2: 정렬 기준 · 마지막 갱신 시각 · 열린 대회 수), 바닥 줄(1.3: 데이터가 어디서 오는지) | — |
| 2 | 새로 고침 | 버튼 | — | 두 파일을 다시 읽는다. raw 캐시를 피하는 쿼리를 붙인다([[CCR-INFRA-001]] 6.4) |
| 3 | 거르기 줄 | 영역 | 출처(3.1)·상태(3.2) 셀렉트와 「마감 지남·지운 대회 보기」(3.3) | 바꾸면 표(7)가 곧바로 걸러진다. 저장소에는 쓰지 않고 브라우저에만 기억한다 |
| 6 | 설정 | 버튼 | 토큰이 없으면 「설정」 옆에 점을 찍어 알린다 | UI-2를 띄운다 |
| 7 | 목록 표 | 표 | 접수마감일 오름차순. 마감일 없는 대회는 맨 뒤. 열: 마감(7.1) · 대회명(7.2)과 판별 근거(7.6) · 출처(7.3) · 수집일 · 상태(7.4) · 지우기(7.5) | — |
| 7.1 | 마감 | 글 | `MM-DD`와 남은 날(D-n). 7일 안이면 강조 | — |
| 7.2 | 대회명 | 링크 | 목록 항목의 대회명. Kaggle은 영문 그대로 | 상세 링크를 새 창으로 연다 |
| 7.3 | 출처 | 칩 | 소스 이름 여섯 가운데 하나 | — |
| 7.4 | 상태 | 셀렉트 | `시작 전` · `진행 중` · `제출` · `완료`. 상태 파일에 값이 없으면 `시작 전`. 값에 따라 배경색이 다르다 | 고르는 즉시 화면이 바뀌고 저장 중(8)이 뜬다. 커밋이 끝나면 사라진다([[CCR-UC-001#UC-H1]]) |
| 7.5 | 지우기 | 버튼 | — | 그 줄이 목록에서 사라지고 접힌 구역(9)으로 간다. 상태 파일에 감춤으로 커밋한다. 목록 파일은 그대로다 |
| 7.6 | 판별 근거 | 글 | 목록 항목의 판별 근거 한 줄. 회색 작은 글 | — |
| 8 | 저장 중 | 표시 | 커밋하는 동안 머리에 뜬다. 여럿을 빨리 바꾸면 하나씩 차례로 보낸다 | — |
| 9 | 접힌 구역 | 영역 | 마감 지난 대회 수와 지운 대회 수. 3.3을 켜거나 여기를 누르면 표 아래에 이어진다. 지운 대회에는 되살리기(9.1) | 펼치기·접기 |
| 9.1 | 되살리기 | 버튼 | 지운 대회의 줄에만 | 감춤을 풀어 원래 자리로 돌려보낸다. 상태 파일에 커밋한다 |
| 10 | 빈 상태 | 글 | 목록 파일이 없거나 비었을 때 표 대신 | — |
| 11 | 토큰 없음 | 알림 | 7.4·7.5·9.1을 눌렀는데 토큰이 없을 때. 화면은 바꾸지 않는다 | 「설정 열기」(11.1)가 UI-2를 띄운다 |
| 12 | 저장 실패 | 알림 | 커밋이 끝내 실패했을 때. 값을 바꾸기 전으로 되돌린 뒤 뜬다. 응답 코드와 짧은 이유 | 「다시 시도」(12.2)는 최신 판을 다시 읽고 같은 바꿈을 다시 보낸다. 「설정 열기」(12.1)는 UI-2 |

### 규칙
- 정렬은 접수마감일 오름차순 하나뿐이다. 마감일이 없는 대회는 맨 뒤에 둔다([[CCR-PRD-001#R10]]). 사용자가 정렬을 바꾸는 장치는 두지 않는다.
- 마감이 지난 대회와 지운 대회는 기본으로 접혀 있고(9), 3.3을 켜면 표 아래에 이어진다. 접힌 구역의 줄은 흐리게 그린다.
- 상태 파일에 값이 없는 대회는 `시작 전`으로 보이고, 감추지 않은 것으로 본다([[CCR-DOM-001#Status]]).
- 상태를 바꾸거나 지우면 **화면을 먼저 바꾸고** 커밋한다. 판이 어긋나면(409·422) 최신 상태 파일을 다시 읽고 이번 바꿈만 얹어 한 번 더 쓴다. 그래도 실패하면 값을 되돌리고 12를 띄운다([[CCR-UC-001#UC-H1]] 4a · 4b).
- 커밋 메시지는 페이지가 만든다. `status: <대회명> → <상태>` 꼴이다([[CCR-INFRA-001]] 8.11).
- 토큰이 없으면 읽기는 그대로 되고, 쓰는 조작을 하면 11이 뜬다. 화면 값은 바꾸지 않는다([[CCR-UC-001#UC-A2]] 4b).
- 목록에 없는 식별자의 상태 값은 무시한다([[CCR-INFRA-001]] 6.2).
- 페이지는 외부 스크립트를 싣지 않는다. 폰트는 Google Fonts `css2` 링크 하나다([[CCR-INFRA-001]] 5.6).
- 요청 주소·콘솔 로그에 토큰을 싣지 않는다([[CCR-INFRA-001]] 5.8).

### 시나리오
**S-1 아침에 훑고 상태를 바꾼다** — [[CCR-UC-001#UC-A2]] · [[CCR-SCN-001#S8]]
1. 페이지를 연다. 두 파일을 읽어 표(7)를 마감일 순으로 그린다.
2. 수집일이 오늘인 줄을 훑고, 관심 가는 대회의 링크(7.2)를 새 창으로 연다.
3. 상태(7.4)를 `진행 중`으로 고른다. 화면이 바뀌고 저장 중(8)이 떴다 사라진다.
4. 관심 없는 대회는 지우기(7.5)를 누른다. 줄이 사라지고 접힌 구역(9)의 수가 하나 는다.

**S-2 토큰 없이 처음 연다** — [[CCR-UC-001#UC-A2]] 4b · [[CCR-UC-001#UC-H2]]
1. 표는 보인다. 상태(7.4)를 바꾸려 하면 토큰 없음(11)이 뜨고 값은 그대로다.
2. 「설정 열기」로 UI-2를 띄워 토큰을 넣는다.
3. 돌아와 다시 고르면 저장된다.

**S-3 다른 기기가 먼저 썼다** — [[CCR-UC-001#UC-H1]] 4a
1. 상태를 바꾼다. 커밋이 판 어긋남으로 거절된다.
2. 페이지가 최신 상태 파일을 다시 읽고 이번 바꿈만 얹어 다시 쓴다. 사용자는 저장 중(8)이 조금 길어진 것만 본다.
3. 그래도 실패하면 값을 되돌리고 저장 실패(12)를 띄운다.

## UI-2 설정 대화상자

| 항목 | 내용 |
|---|---|
| 경로 | `/` (UI-1 위에 뜬다. 주소는 바뀌지 않는다) |
| 주 유스케이스 | [[CCR-UC-001#UC-H2]] |
| 진입 / 이탈 | UI-1의 설정(6)·토큰 없음(11.1)·저장 실패(12.1)에서 / 닫기(20.7)·저장(20.4) 뒤 UI-1로 |
| 쓰는 것 | 브라우저 `localStorage`의 토큰. 저장소에는 아무것도 쓰지 않는다 |

### 배치
```html
<style>
body{margin:0;font-family:"IBM Plex Sans KR",system-ui,sans-serif;background:#f4f2ec;color:#1d1c19}
a{color:#1f5f6b}a:hover{color:#143f47}
.cc-btn{font:inherit;font-size:14px;padding:9px 14px;border-radius:8px;border:1px solid #c9c4b7;background:#fff;color:#1d1c19;cursor:pointer;min-height:40px}
.cc-btn.primary{background:#1f5f6b;border-color:#1f5f6b;color:#fff}
.cc-btn.ghost{border-color:transparent;background:transparent;color:#5c594f}
.cc-btn.danger{color:#8f2f16;border-color:#d9b1a3}
.cc-dim{position:absolute;inset:0;background:rgba(29,28,25,.42);display:flex;align-items:center;justify-content:center}
.cc-dlg{width:560px;background:#fff;border:1px solid #c9c4b7;border-radius:14px;padding:24px 28px;box-shadow:0 20px 50px rgba(0,0,0,.18);display:flex;flex-direction:column;gap:16px}
.cc-dlg h2{margin:0;font-size:18px;font-weight:600}
.cc-dlg p{margin:0;font-size:14px;line-height:1.55;color:#3f3d36}
.cc-dlg ol{margin:0;padding-left:20px;font-size:13px;line-height:1.6;color:#3f3d36}
.cc-in{font:inherit;font-size:14px;padding:10px 12px;border-radius:8px;border:1px solid #c9c4b7;width:100%;box-sizing:border-box;min-height:44px}
.cc-lbl{font-size:13px;color:#5c594f;display:flex;flex-direction:column;gap:6px}
.cc-ok{display:inline-flex;align-items:center;gap:8px;font-size:13px;padding:6px 12px;border-radius:8px;background:#e3ecdd;border:1px solid #8fae82;color:#25451b}
.cc-ghosttbl{opacity:.55;filter:saturate(.6)}
.cc-ghosttbl div{height:44px;border-bottom:1px solid #eceae3;background:#fff}
</style>
<div data-el="0" style="width: 100%; max-width: 1280px; min-height: 800px; box-sizing: border-box; position: relative; background: #f4f2ec; overflow: hidden;">
  <div style="padding: 32px 40px; display: flex; flex-direction: column; gap: 14px;">
    <div style="font-size: 22px; font-weight: 600;">대회 목록</div>
    <div class="cc-ghosttbl" style="border: 1px solid #d9d5cb; border-radius: 10px; overflow: hidden; display: flex; flex-direction: column;">
      <div style="background: #faf9f5;"></div><div></div><div></div><div></div><div></div><div></div>
    </div>
  </div>
  <div class="cc-dim">
    <div class="cc-dlg" role="dialog" aria-labelledby="cc-dlg-title" data-el="20">
      <div style="display: flex; align-items: center; gap: 12px;">
        <h2 id="cc-dlg-title" data-el="20.1">설정 — 저장소 토큰</h2>
        <div style="flex-grow: 1;"></div>
        <span class="cc-ok" data-el="20.6"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12l4 4 10-10"></path></svg>토큰 있음 · 쓰기 가능</span>
      </div>
      <p>상태를 바꾸거나 대회를 지우면 이 페이지가 저장소의 <code>data/status.json</code>에 커밋합니다. 그러려면 GitHub 토큰이 필요하고, 토큰은 이 브라우저에만 저장됩니다.</p>
      <ol data-el="20.2">
        <li>GitHub → Settings → Developer settings → <strong>Fine-grained tokens</strong> → Generate new token</li>
        <li>Repository access: <strong>Only select repositories</strong> → HoyoungParkme/competition-crawler</li>
        <li>Permissions → Repository → <strong>Contents: Read and write</strong>. 그 밖은 두지 않음. 만료 기한을 둠</li>
      </ol>
      <label class="cc-lbl">토큰
        <input class="cc-in" type="password" placeholder="github_pat_…" data-el="20.3" autocomplete="off">
      </label>
      <div style="display: flex; gap: 10px; align-items: center;">
        <button class="cc-btn danger" type="button" data-el="20.5">이 브라우저에서 토큰 지우기</button>
        <div style="flex-grow: 1;"></div>
        <button class="cc-btn ghost" type="button" data-el="20.7">닫기</button>
        <button class="cc-btn primary" type="button" data-el="20.4">확인하고 저장</button>
      </div>
    </div>
  </div>
</div>
```

### 요소
| # | 이름 | 종류 | 보여주는 것 | 누르면 |
|---|---|---|---|---|
| 20 | 대화상자 | 대화상자 | UI-1을 흐리게 덮는다. 바깥을 누르거나 Esc로 닫힌다 | — |
| 20.1 | 제목 | 글 | 「설정 — 저장소 토큰」 | — |
| 20.2 | 만드는 법 | 글 | GitHub에서 fine-grained 토큰을 만드는 세 단계. 저장소는 이 저장소 하나, 권한은 Contents 읽기·쓰기만, 만료 기한을 둘 것([[CCR-INFRA-001]] 5.8) | — |
| 20.3 | 토큰 입력 | 입력(password) | 붙여 넣는 칸. 값은 가려 보인다. 자동 완성 끔 | — |
| 20.4 | 확인하고 저장 | 버튼 | — | 토큰으로 상태 파일을 한 번 읽어 본다. 읽히면 `localStorage`에 두고 닫는다. 안 읽히면 이유(401·403·404)를 칸 아래에 보이고 저장하지 않는다([[CCR-UC-001#UC-H2]] 4a) |
| 20.5 | 토큰 지우기 | 버튼 | 토큰이 있을 때만 | `localStorage`에서 지운다. 페이지는 읽기만 되는 상태로 돌아간다. GitHub 쪽 폐기는 사용자가 한다 |
| 20.6 | 토큰 상태 | 표시 | 「토큰 있음 · 쓰기 가능」 또는 「토큰 없음 · 읽기만」. 값은 보여 주지 않는다 | — |
| 20.7 | 닫기 | 버튼 | — | 바꾼 것 없이 닫는다 |

### 규칙
- 토큰 값은 한 번 넣은 뒤 다시 보여 주지 않는다. 있음·없음만 보인다([[CCR-UC-001#UC-H2]] 1).
- 저장 전에 반드시 상태 파일을 읽어 검증한다. 검증에 실패한 값은 저장하지 않는다.
- 토큰은 `localStorage`에만 둔다. 쿠키·주소·콘솔에 두지 않는다([[CCR-INFRA-001]] 5.8).
- 대화상자를 여는 동안 UI-1의 조작은 막는다.

### 시나리오
**S-4 토큰을 넣는다** — [[CCR-UC-001#UC-H2]]
1. 20.2대로 GitHub에서 토큰을 만든다.
2. 20.3에 붙여 넣고 20.4를 누른다. 검증이 지나면 20.6이 「토큰 있음」으로 바뀌고 닫힌다.

**S-5 샌 것 같아 바꾼다** — [[CCR-UC-001#UC-H2]] 5a
1. GitHub에서 옛 토큰을 폐기하고 새로 만든다.
2. UI-2를 열어 20.3에 새 값을 넣고 20.4. 옛 값은 덮인다.

## 3. 공통 틀

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap">
<style>
  body{margin:0;font-family:"IBM Plex Sans KR",system-ui,sans-serif;background:#f4f2ec;color:#1d1c19}
  a{color:#1f5f6b}a:hover{color:#143f47}
</style>
```

색은 셋이다. 바탕 `#f4f2ec`, 글 `#1d1c19`, 강조 `#1f5f6b`(링크·주 버튼). 상태 셀렉트의 배경은 `진행 중` `#e3ecdd`, `제출` `#e6eef0`, 그 밖은 흰색이다. 알림은 경고 `#fff7e6`, 실패 `#fbe9e4`, 안내 `#e6eef0`. 글꼴은 IBM Plex Sans KR 하나이고, 본문 14px · 표 머리 12px · 제목 22px. 누르는 것은 최소 높이 40px이다. 값은 `frontend/src/styles.css`에 토큰으로 옮기고 컴포넌트에 직접 쓰지 않는다([[CCR-INFRA-001]] 4장).

## 4. 화면 흐름

```mermaid
flowchart LR
    UI1[UI-1 대회 목록] -->|설정 6 · 토큰 없음 11.1 · 저장 실패 12.1| UI2[UI-2 설정 대화상자]
    UI2 -->|저장 20.4 · 닫기 20.7| UI1
    UI1 -->|대회명 7.2| EXT([상세 페이지 · 새 창])
```

## 5. 미결사항

- [ ] 표를 폰 폭에서 어떻게 접을지. 사용자는 PC로 아침에 여는 것을 전제로 그렸다([[CCR-RFQ-001]] 4장). 폰에서 열면 가로 스크롤로 둔다
- [ ] 여럿을 빨리 바꿀 때 커밋을 하나씩 보낼지, 잠깐 모아 한 커밋으로 보낼지. 지금은 하나씩이다
- [ ] 접힌 구역(9)에 마감 지난 대회가 수백 건 쌓였을 때 펼친 화면을 나눌지. 목록 파일을 덜어내는 문제([[CCR-INFRA-001]] 9장)와 함께 본다
