"""Live Stage B diagnostic. Run with a Playwright Python environment and Chromium."""
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import Error, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "review-runs/policy-retry"
URL = json.loads((ROOT / "regulatory-change-impact-brief/references/routes.json").read_bytes())["POLICY"]
URL += "#5bcbdfef18004bcf8cd2d6f32125c9ff"
PANE = """() => {
 const els=[document.scrollingElement,...document.querySelectorAll('main,div,section')];
 return els.filter(e=>{const r=e.getBoundingClientRect();return r.width>400&&r.height>250&&r.top<innerHeight&&r.bottom>0&&e.scrollHeight>e.clientHeight+4&&(e===document.scrollingElement||/auto|scroll|overlay/.test(getComputedStyle(e).overflowY))})
 .sort((a,b)=>(b.clientWidth*b.clientHeight)-(a.clientWidth*a.clientHeight))[0]||document.scrollingElement;
}"""


def normal(s):
    return " ".join(s.split())


def trial(engine, refs):
    browser = engine.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800}, accept_downloads=False)
    http_errors = Counter()
    page.on("response", lambda r: http_errors.update([str(r.status)]) if r.status >= 400 else None)
    matches = {r["section"]: {"heading": False, "passage": False, "paired": False} for r in refs}
    result = dict(started_at=datetime.now(timezone.utc).isoformat(), matches=matches,
                  browser_version=browser.version, reached_bottom=False, passed=False)
    positions = set()

    def sample(phase):
        if http_errors["429"]:
            raise ValueError("HTTP 429 rate limit; stop this trial and skip further sessions")
        if page.url.split("#")[0] != URL.split("#")[0]:
            raise ValueError("Unexpected destination")
        body = normal(page.locator("body").inner_text(timeout=5000))
        title = page.title()
        if re.search(r"checking your browser|verify you are human|access denied|just a moment", title+" "+body[:400], re.I):
            raise ValueError("Denial or challenge")
        if "internal polic" not in title.lower():
            return False
        for r in refs:
            heading, needle = r["section"], normal(r["passage"])
            m = matches[heading]
            m["heading"] |= heading.casefold() in body.casefold()
            start = body.find(needle)
            if start >= 0:
                m.setdefault("first_seen", phase)
                m["passage"] = True
                # The selected full passage and its heading must occur together.
                if normal(body[:start]).casefold().endswith(heading.casefold()):
                    m["paired"] = True
                actual = body[start:start+len(needle)]
                m["observed_sha256"] = hashlib.sha256(actual.encode()).hexdigest()
        return True

    try:
        response = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        result["document_status"] = response.status if response else None
        if not response or response.status >= 400 or response.headers.get("cf-mitigated") == "challenge":
            raise ValueError("Document unavailable or challenged")
        for _ in range(30):
            if sample("initial") and matches["Internal AI-use policy"]["passage"]:
                break
            page.wait_for_timeout(500)
        pane = page.evaluate_handle(PANE)
        pane.evaluate("e=>e.scrollTo(0,0)")
        page.wait_for_timeout(400)
        stable = 0
        for _ in range(100):
            sample("scroll")
            y, h, total = pane.evaluate("e=>[e.scrollTop,e.clientHeight,e.scrollHeight]")
            positions.add(round(y))
            stable = stable+1 if y+h >= total-2 else 0
            if stable >= 6:
                result["reached_bottom"] = True
                break
            pane.evaluate("e=>e.scrollBy(0,Math.max(150,e.clientHeight*0.65))")
            page.wait_for_timeout(750)
        result["passed"] = result["reached_bottom"] and all(m["paired"] for m in matches.values())
    except ValueError as e:
        result["error"] = str(e)
    except Error as e:
        result["error"] = type(e).__name__
    finally:
        browser.close()
    result.update(scroll_positions=len(positions), http_errors=dict(http_errors))
    return result


if __name__ == "__main__":
    refs = [json.loads(f.read_bytes()) for f in sorted(CAPTURES.glob("policy-selection-*.json"))]
    if len(refs) != 4 or len({r["section"] for r in refs}) != 4:
        raise SystemExit("Expected the four distinct reviewed Edge selections")
    with sync_playwright() as p:
        trials = []
        for _ in range(2):
            result = trial(p.chromium, refs)
            trials.append(result)
            print(json.dumps(result), flush=True)
            if "error" in result:
                break
    dest = ROOT / "review-runs/playwright-probe"
    dest.mkdir(exist_ok=True, parents=True)
    path = dest / datetime.now(timezone.utc).strftime("verification-%Y%m%dT%H%M%SZ.json")
    with path.open("x") as f:
        json.dump(dict(locator=URL, trials=trials, comparison="Case-sensitive passage match after whitespace normalization; case-insensitive immediately preceding heading."), f, indent=2)
    print(path)
    raise SystemExit(0 if len(trials)==2 and all(t["passed"] for t in trials) else 1)
