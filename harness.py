# ============================================================
# 사전 설치 필요:
#   pip install playwright
#   playwright install chromium
# ============================================================

import os
import json
import anthropic
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
MAX_RETRIES = 3

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def call_claude(system: str, user: str, max_tokens: int) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return next(b.text for b in response.content if b.type == "text")


# ─────────────────────────────────────────
# 1단계: Planner
# ─────────────────────────────────────────
PLANNER_SYSTEM = """너는 소프트웨어 기획자야.
팁 계산기 HTML 앱 기획서를 아래 기능을 포함해서 작성해:
1. 결제 금액 입력 (id='billInput', 숫자만, 음수 불가, 단위: 원₩)
2. 팁 비율 버튼 1개 (id='btn10', 10% 고정)
3. 인원수 입력 (id='peopleInput', 1~20명)
4. 팁 금액 결과 표시 (id='tipAmount', 원₩, 1000단위 콤마)
5. 총 결제 금액 표시 (id='totalAmount', 원₩, 1000단위 콤마)
6. 1인당 분담 금액 표시 (id='perPerson', 원₩, 1000단위 콤마)
7. 초기화 버튼 (id='resetBtn')
- 모든 금액은 원화(₩) 표기, 1000단위마다 콤마
- 기술 스택: 순수 HTML/CSS/JavaScript 단일 파일
- 입력이 적으니 UI는 작고 세련되게
- 500자 이내로 간결하게 작성."""


def run_planner() -> str:
    print("[1/4] Planner 실행 중...")
    result = call_claude(
        system=PLANNER_SYSTEM,
        user="팁 계산기 HTML 앱 기획서를 작성해줘.",
        max_tokens=500,
    )
    print("[1/4] Planner 완료 ✓")
    return result


# ─────────────────────────────────────────
# 2단계: Generator
# ─────────────────────────────────────────
GENERATOR_SYSTEM = """너는 감각 있는 프론트엔드 개발자야.
기획서를 받아 HTML 단일 파일을 만들어.

[필수 규칙 - HTML id]
Playwright 테스트가 아래 id로 요소를 찾으니 정확히 사용할 것:
- 결제 금액 입력: id='billInput'
- 10% 팁 버튼: id='btn10'
- 인원수 입력: id='peopleInput'
- 팁 금액 결과: id='tipAmount'
- 총 결제 금액 결과: id='totalAmount'
- 1인당 분담금 결과: id='perPerson'
- 초기화 버튼: id='resetBtn'

[필수 규칙 - 계산 로직]
결제금액 100,000원, 팁 10%, 인원 2명 입력 시:
→ tipAmount: 10,000 포함
→ totalAmount: 110,000 포함
→ perPerson: 55,000 포함
모든 금액은 ₩ 기호와 1000단위 콤마 적용 (예: ₩110,000)

[필수 규칙 - UI/UX]
- 입력 항목이 2개뿐이니 카드 전체 크기를 작고 아담하게 만들 것
  (max-width: 360px 이하 권장)
- 고상하고 세련된 이모지/아이콘 활용:
  예) 🧾 결제금액, 👥 인원수, 💰 팁 금액, 🧮 합계, 👤 1인당, 🔄 초기화
- 버튼·카드에 부드러운 그림자와 hover 효과 적용
- 컬러는 차분한 다크 네이비 또는 딥 그린 계열 포인트 색상 사용
- 폰트는 system-ui 또는 'Pretendard' fallback

[필수 규칙 - 코드 품질]
- JavaScript 코드 절대 생략·축약 금지
- 모든 함수와 이벤트 리스너 완전히 구현
- 입력값 바뀔 때마다 즉시 결과 업데이트
- 순수 HTML만 출력, 마크다운 코드블록 없이 출력

[이전 테스트 실패 피드백이 있는 경우]
실패한 테스트를 반드시 수정하고 같은 실수 반복 금지."""


def run_generator(plan: str, feedback: dict = None, prev_code: str = None, attempt: int = 1) -> str:
    print(f"[2/4] Generator 실행 중... (시도 {attempt}/{MAX_RETRIES})")

    if feedback and prev_code:
        failed = "\n".join(f"- {t}" for t in feedback.get("failed_tests", []))
        suggestion = feedback.get("suggestion", "")
        user_msg = (
            f"아래 기획서를 바탕으로 팁 계산기 HTML 앱을 수정해줘.\n\n"
            f"기획서:\n{plan}\n\n"
            f"이전 코드:\n{prev_code}\n\n"
            f"실패한 테스트 항목 (반드시 수정):\n{failed}\n\n"
            f"개선 방향: {suggestion}"
        )
    else:
        user_msg = (
            f"아래 기획서를 바탕으로 팁 계산기 HTML 앱을 만들어줘.\n\n"
            f"기획서:\n{plan}"
        )

    result = call_claude(
        system=GENERATOR_SYSTEM,
        user=user_msg,
        max_tokens=4000,
    )
    print("[2/4] Generator 완료 ✓ → HTML 저장")
    return result


# ─────────────────────────────────────────
# HTML 추출 및 저장
# ─────────────────────────────────────────
def extract_html(code: str) -> str:
    if "```html" in code:
        start = code.index("```html") + 7
        try:
            end = code.index("```", start)
            return code[start:end].strip()
        except ValueError:
            return code[start:].strip()
    if "```" in code:
        start = code.index("```") + 3
        try:
            end = code.index("```", start)
            return code[start:end].strip()
        except ValueError:
            return code[start:].strip()
    return code.strip()


def save_html(html: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)


# ─────────────────────────────────────────
# 3단계: Playwright 테스트
# ─────────────────────────────────────────
def run_playwright_tests() -> list[dict]:
    print("[3/4] Playwright 테스트 실행 중...")
    results = []
    abs_path = os.path.abspath(OUTPUT_FILE)
    file_url = f"file://{abs_path}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # ── 테스트 1: 기본 계산 검증 ──────────────────
        # 100,000원 / 10% / 2명 → 팁 10,000 / 합계 110,000 / 1인당 55,000
        try:
            page.goto(file_url)
            page.wait_for_load_state("domcontentloaded")

            page.fill("#billInput", "100000")
            page.click("#btn10")
            page.fill("#peopleInput", "2")
            page.wait_for_timeout(300)

            tip_text   = page.text_content("#tipAmount")   or ""
            total_text = page.text_content("#totalAmount") or ""
            per_text   = page.text_content("#perPerson")   or ""

            # 콤마 포함된 숫자로 검증
            passed = (
                "10,000" in tip_text
                and "110,000" in total_text
                and "55,000" in per_text
            )
            detail = (
                f"tipAmount='{tip_text.strip()}' (기대: 10,000 포함), "
                f"totalAmount='{total_text.strip()}' (기대: 110,000 포함), "
                f"perPerson='{per_text.strip()}' (기대: 55,000 포함)"
            )
            results.append({"test_name": "기본 계산 검증", "passed": passed, "detail": detail})
        except Exception as e:
            results.append({"test_name": "기본 계산 검증", "passed": False, "detail": str(e)})

        # ── 테스트 2: 10% 버튼 동작 확인 ──────────────
        # btn10 클릭 후 결과가 즉시 업데이트되는지 확인
        try:
            page.goto(file_url)
            page.wait_for_load_state("domcontentloaded")

            page.fill("#billInput", "50000")
            page.fill("#peopleInput", "1")
            page.click("#btn10")
            page.wait_for_timeout(300)

            tip_text   = page.text_content("#tipAmount")   or ""
            total_text = page.text_content("#totalAmount") or ""

            # 50,000 * 10% = 5,000 / 합계 55,000
            passed = "5,000" in tip_text and "55,000" in total_text
            detail = (
                f"btn10 클릭 후 tipAmount='{tip_text.strip()}' (기대: 5,000 포함), "
                f"totalAmount='{total_text.strip()}' (기대: 55,000 포함)"
            )
            results.append({"test_name": "10% 버튼 동작 확인", "passed": passed, "detail": detail})
        except Exception as e:
            results.append({"test_name": "10% 버튼 동작 확인", "passed": False, "detail": str(e)})

        # ── 테스트 3: 초기화 버튼 확인 ────────────────
        try:
            page.goto(file_url)
            page.wait_for_load_state("domcontentloaded")

            page.fill("#billInput", "200000")
            page.click("#btn10")
            page.wait_for_timeout(200)
            page.click("#resetBtn")
            page.wait_for_timeout(200)

            bill_val = page.input_value("#billInput")
            tip_text = page.text_content("#tipAmount") or ""

            bill_cleared = bill_val in ("", "0")
            tip_cleared  = "20,000" not in tip_text and "200,000" not in tip_text
            passed = bill_cleared and tip_cleared
            detail = (
                f"초기화 후 billInput='{bill_val}' (기대: 비어있음 or 0), "
                f"tipAmount='{tip_text.strip()}' (기대: 초기화됨)"
            )
            results.append({"test_name": "초기화 버튼 확인", "passed": passed, "detail": detail})
        except Exception as e:
            results.append({"test_name": "초기화 버튼 확인", "passed": False, "detail": str(e)})

        browser.close()

    print("[3/4] 테스트 결과:")
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(f"      {icon} {r['test_name']}")

    return results


# ─────────────────────────────────────────
# 4단계: Evaluator
# ─────────────────────────────────────────
EVALUATOR_SYSTEM = """너는 QA 엔지니어야.
Playwright가 실제 브라우저에서 테스트한 결과를 받아
PASS/FAIL을 판정해.

[판정 규칙]
- 테스트 3개 중 하나라도 passed: false이면 → FAIL
- 테스트 3개 모두 passed: true이면 → PASS

반드시 아래 JSON 형식으로만 응답:
{
  "verdict": "PASS" 또는 "FAIL",
  "failed_tests": ["실패한 테스트 이름 목록, 없으면 빈 배열"],
  "suggestion": "다음 시도에서 고쳐야 할 것 한 줄 요약"
}
다른 텍스트나 마크다운 없이 JSON만 출력할 것."""


def parse_evaluator_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "verdict": "FAIL",
            "failed_tests": ["Evaluator JSON 파싱 실패"],
            "suggestion": "Evaluator가 올바른 JSON을 반환하지 않았습니다.",
        }


def run_evaluator(test_results: list[dict], attempt: int = 1) -> dict:
    print(f"[4/4] Evaluator 판정 중... (시도 {attempt}/{MAX_RETRIES})")
    test_summary = json.dumps(test_results, ensure_ascii=False, indent=2)
    raw = call_claude(
        system=EVALUATOR_SYSTEM,
        user=f"아래는 Playwright 테스트 결과야. PASS/FAIL을 판정해줘.\n\n{test_summary}",
        max_tokens=500,
    )
    return parse_evaluator_response(raw)


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    plan = run_planner()

    code = None
    qa_result = None
    feedback = None
    test_results = None
    total_attempts = 0

    for attempt in range(1, MAX_RETRIES + 1):
        total_attempts = attempt

        code = run_generator(plan, feedback=feedback, prev_code=code, attempt=attempt)
        html = extract_html(code)
        save_html(html)

        test_results = run_playwright_tests()

        qa_result = run_evaluator(test_results, attempt=attempt)
        verdict = qa_result.get("verdict", "FAIL")

        if verdict == "PASS":
            print("[4/4] 결과: PASS → 완료 ✓")
            break
        else:
            failed = qa_result.get("failed_tests", [])
            if attempt < MAX_RETRIES:
                print(f"[4/4] 결과: FAIL → 재시도")
            else:
                print("[4/4] 결과: FAIL → 최대 재시도 초과, 마지막 결과 저장")
            if failed:
                print(f"      실패 항목: {failed}")
            feedback = qa_result

    print()
    print("================================")
    print(f"📋 기획서: {plan}")
    print("--------------------------------")
    print("🧪 Playwright 테스트 결과:")
    for r in (test_results or []):
        icon = "✅" if r["passed"] else "❌"
        print(f"   {icon} {r['test_name']}")
    print("--------------------------------")
    print("🔍 Evaluator 판정:")
    print(f"   verdict   : {qa_result.get('verdict')}")
    print(f"   총 시도   : {total_attempts}회")
    print("--------------------------------")
    print(f"💾 저장 완료: {OUTPUT_FILE}")
    print("================================")


if __name__ == "__main__":
    main()
