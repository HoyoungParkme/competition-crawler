---
doc_id: CCR-UI-001
type: UI
title: 화면 설계·와이어프레임 — AI 대회 수집기
status: draft
upstream: [CCR-UC-001]
---

# 화면 설계·와이어프레임 — AI 대회 수집기

## 0. 이 문서가 다루는 것

디자인 스킬이 만든 와이어프레임을 **그대로** 올린 시험 문서다. 배치 html은 디자인 캔버스의 아트보드 원문이고(`<style>`·`<script>` 포함), 요소 표·규칙은 두지 않았다 — 새 규약([[SYNC-STD-001]] 2.7)에서 필수는 배치 html 하나다.

## UI-1 대회 목록

| 항목 | 내용 |
|---|---|
| 경로 | `/` |
| 주 유스케이스 | [[CCR-UC-001#UC-A2]] |
| 진입 / 이탈 | 아침 배치가 끝난 뒤 사람이 연다 / 노션 행이나 실행 기록으로 |

### 배치
```html
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600&family=IBM+Plex+Sans+KR:wght@400;500&display=swap">
<style>
body{margin:0;font-family:"IBM Plex Sans KR",system-ui,sans-serif;background:#f4f2ec;color:#1d1c19}
a{color:#8a4b1f}a:hover{color:#5e3213}
.ccr-tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid #d9d4c6;background:#fbfaf6}
.ccr-tag.on{background:#1d1c19;color:#f4f2ec;border-color:#1d1c19}
</style>
</helmet>
<div data-el="0" style="width: 1280px; height: 800px; box-sizing: border-box; display: flex; flex-direction: column; background: #f4f2ec;">
  <header data-el="1" style="display: flex; align-items: center; gap: 24px; padding: 20px 40px; border-bottom: 1px solid #d9d4c6; background: #fbfaf6;">
    <span data-el="1.1" style="font-family: 'Noto Serif KR', serif; font-size: 22px; font-weight: 600;">AI 대회 수집기</span>
    <span data-el="1.2" style="font-size: 14px; color: #5f5b52;">오늘 08:50 실행 · 여섯 소스 중 6곳 성공 · 새 대회 7 · 버림 3 · 중복 41</span>
    <span style="flex-grow: 1;"></span>
    <a data-el="1.3" href="#run" style="font-size: 14px; text-decoration: none; padding: 10px 14px; border: 1px solid #d9d4c6; border-radius: 8px; background: #fbfaf6;">실행 기록</a>
  </header>
  <div style="display: flex; flex-grow: 1; min-height: 0;">
    <aside data-el="2" style="width: 280px; box-sizing: border-box; padding: 24px 24px; border-right: 1px solid #d9d4c6; display: flex; flex-direction: column; gap: 20px;">
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <span style="font-size: 12px; color: #5f5b52;">출처</span>
        <div data-el="2.1" style="display: flex; flex-wrap: wrap; gap: 6px;">
          <span class="ccr-tag on">전부</span><span class="ccr-tag">event-us</span><span class="ccr-tag">DACON</span><span class="ccr-tag">Kaggle</span><span class="ccr-tag">wevity</span><span class="ccr-tag">AI팩토리</span><span class="ccr-tag">콘테스트코리아</span>
        </div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <span style="font-size: 12px; color: #5f5b52;">관심 분야 판정</span>
        <div data-el="2.2" style="display: flex; flex-direction: column; gap: 6px; font-size: 14px;">
          <label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox" checked> 관심 분야</label>
          <label style="display: flex; align-items: center; gap: 8px;"><input type="checkbox"> 관심 아님(걸러진 것)</label>
        </div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <span style="font-size: 12px; color: #5f5b52;">접수마감</span>
        <div data-el="2.3" style="display: flex; flex-direction: column; gap: 6px; font-size: 14px;">
          <label style="display: flex; align-items: center; gap: 8px;"><input type="radio" name="due" checked> 열려 있음</label>
          <label style="display: flex; align-items: center; gap: 8px;"><input type="radio" name="due"> 7일 안에 마감</label>
          <label style="display: flex; align-items: center; gap: 8px;"><input type="radio" name="due"> 마감일 모름</label>
        </div>
      </div>
    </aside>
    <main data-el="3" style="flex-grow: 1; min-width: 0; display: flex; flex-direction: column; padding: 24px 40px; gap: 16px;">
      <div style="display: flex; align-items: baseline; gap: 16px;">
        <h1 data-el="3.1" style="margin: 0; font-family: 'Noto Serif KR', serif; font-size: 20px; font-weight: 600;">새로 들어온 대회 7</h1>
        <span data-el="3.2" style="font-size: 13px; color: #5f5b52;">노션 대회목록 DB에 오늘 등록된 것. 훑고 참가할 것을 고른다</span>
      </div>
      <table data-el="4" style="width: 100%; border-collapse: collapse; font-size: 14px; background: #fbfaf6; border: 1px solid #d9d4c6; border-radius: 8px;">
        <thead>
          <tr style="text-align: left; color: #5f5b52; font-size: 12px;">
            <th style="padding: 10px 12px; border-bottom: 1px solid #d9d4c6;">대회명</th>
            <th style="padding: 10px 12px; border-bottom: 1px solid #d9d4c6; width: 120px;">출처</th>
            <th style="padding: 10px 12px; border-bottom: 1px solid #d9d4c6; width: 110px;">접수시작</th>
            <th style="padding: 10px 12px; border-bottom: 1px solid #d9d4c6; width: 110px;">접수마감</th>
            <th style="padding: 10px 12px; border-bottom: 1px solid #d9d4c6; width: 120px;">분야 판정</th>
            <th style="padding: 10px 12px; border-bottom: 1px solid #d9d4c6; width: 90px;">노션</th>
          </tr>
        </thead>
        <tbody>
          <tr data-el="4.1">
            <td style="padding: 12px;"><a data-el="4.2" href="#detail" style="text-decoration: none; font-weight: 500;">2026 국립공원 위성 모니터링 AI 챌린지</a><div data-el="4.3" style="font-size: 12px; color: #5f5b52; margin-top: 2px;">원천 ID event-us:31820 · 같은 대회 DACON에도 있음</div></td>
            <td style="padding: 12px;"><span class="ccr-tag">event-us</span></td>
            <td style="padding: 12px;">2026-09-15</td>
            <td data-el="4.4" style="padding: 12px; font-weight: 500;">2026-10-06</td>
            <td data-el="4.5" style="padding: 12px;"><span class="ccr-tag on">관심</span></td>
            <td data-el="4.6" style="padding: 12px;"><a href="#notion" style="font-size: 13px;">열기</a></td>
          </tr>
          <tr>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><a href="#detail" style="text-decoration: none; font-weight: 500;">[대회명]</a><div style="font-size: 12px; color: #5f5b52; margin-top: 2px;">원천 ID [소스:ID]</div></td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><span class="ccr-tag">Kaggle</span></td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc; color: #5f5b52;">—</td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc; color: #5f5b52;">모름</td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><span class="ccr-tag on">관심</span></td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><a href="#notion" style="font-size: 13px;">열기</a></td>
          </tr>
          <tr>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><a href="#detail" style="text-decoration: none; font-weight: 500;">[대회명]</a><div style="font-size: 12px; color: #5f5b52; margin-top: 2px;">원천 ID [소스:ID] · AI팩토리 과제 3건을 하나로 묶음</div></td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><span class="ccr-tag">AI팩토리</span></td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;">[날짜]</td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;">[날짜]</td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc;"><span class="ccr-tag">관심 아님</span></td>
            <td style="padding: 12px; border-top: 1px solid #ebe7dc; color: #5f5b52;">미등록</td>
          </tr>
        </tbody>
      </table>
      <section id="run" data-el="5" style="margin-top: auto; display: flex; gap: 24px; padding: 14px 16px; border: 1px solid #d9d4c6; border-radius: 8px; background: #fbfaf6; font-size: 13px;">
        <span data-el="5.1" style="font-weight: 500;">오늘 실행 기록</span>
        <span data-el="5.2">가져옴 51 · 필수 값 없어 버림 3 · 마감 지남 0 · 이미 앎 41 · 관심 아님 0 · 노션 등록 7</span>
        <span style="flex-grow: 1;"></span>
        <a data-el="5.3" href="#log" style="font-size: 13px;">소스별로 보기</a>
      </section>
    </main>
  </div>
</div>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":1280,"height":800}}'>
class Component extends DCLogic {
  renderVals() { return {}; }
}
</script>
```

## 미결사항

- [ ] 이 화면을 실제로 만들지, 노션 DB 뷰로 갈음할지 — [[CCR-PRD-001#R8]]이 「확인할 수 있다」까지만 요구한다
