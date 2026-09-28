"""Render two HTML explanations from their Mermaid sources."""

from html import escape
from pathlib import Path


ROOT = Path(__file__).parent

PAGES = {
    "decision-tree": {
        "title": "Release decision tree",
        "subtitle": "เริ่มจากเหตุการณ์ใน GitHub แล้วตอบทีละเงื่อนไขว่าจะสร้าง Release หรือส่งไป Databricks ทางใด",
        "notes": [
            ("1. เริ่มจาก trigger", "PR เข้า master ใช้ CI และ Security; push สาขาอื่นใช้ Security; push เข้า master จึงสร้าง GitHub Release"),
            ("2. ตรวจ release", "release_id ผูกกับ 12 ตัวแรกของ commit SHA หาก id เดิมมี package ต่างกัน workflow จะหยุด"),
            ("3. เลือก delivery", "อ่าน delivery_mode จาก config/env/dev.yaml ค่าปัจจุบันคือ u2m: ผู้ใช้ login แล้วให้สคริปต์ทำ CD-1 ถึง CD-8"),
        ],
    },
    "flow-chart": {
        "title": "Release flow chart",
        "subtitle": "ลำดับงานตั้งแต่ PR, build package, publish GitHub Release จนถึงการบันทึก ACTIVATED ใน Databricks",
        "notes": [
            ("1. ตรวจและสร้าง", "PR สร้าง preview package; push เข้า master จึงสร้าง package จริงและตรวจ release gate"),
            ("2. ส่ง package", "auto และ u2m ใช้ deliver_release.sh ชุดเดียวกัน; manual ใช้ UI กับ SQL ที่เตรียมไว้"),
            ("3. ยืนยันผล", "manifest.json ปิดผนึกโฟลเดอร์ Volume; แถว ACTIVATED ล่าสุดใน registry บอก release ที่ใช้งาน"),
        ],
    },
}

STYLE = """
:root{color-scheme:light;--ink:#182b3a;--muted:#58707f;--line:#d8e4e8;--blue:#276087}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#e8f1f5 0,#f6f9fb 320px);color:var(--ink);font-family:Tahoma,"Segoe UI",sans-serif;line-height:1.6}
a{color:var(--blue)}a:focus-visible{outline:3px solid #e9a83c;outline-offset:3px}
.wrap{width:min(1440px,calc(100% - 36px));margin:auto}
header{padding:28px 0 20px;border-bottom:1px solid var(--line)}
.topline{display:flex;flex-wrap:wrap;justify-content:space-between;gap:14px;align-items:center}
.brand{font-weight:700;letter-spacing:.04em;color:#194766}
nav{display:flex;flex-wrap:wrap;gap:8px}
nav a{display:inline-block;padding:8px 13px;text-decoration:none;border-radius:999px;border:1px solid #b9d0dc;background:#fff;font-size:14px}
nav a[aria-current=page]{color:#fff;background:#275e81;border-color:#275e81}
main{padding:32px 0 64px}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;color:#537285}
h1{margin:7px 0 10px;font-size:clamp(30px,3.5vw,50px);line-height:1.16}
.lead{max-width:900px;margin:0;font-size:18px;color:#3f5d6b}
.notice{display:flex;gap:12px;align-items:flex-start;margin:24px 0 22px;padding:15px 18px;border-left:5px solid #449271;background:#dff2e6;border-radius:0 10px 10px 0}
.notice strong{white-space:nowrap}.meta{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;margin:0 0 16px;color:var(--muted);font-size:14px}
.meta a{text-decoration:underline;text-underline-offset:3px}
.diagram-shell{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:0 10px 40px rgba(25,58,78,.07)}
.diagram-top{padding:15px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.diagram-top h2{margin:0;font-size:17px}.diagram-top span{color:var(--muted);font-size:13px}
.diagram-viewport{overflow:auto;padding:20px;min-height:320px}
.mermaid{display:flex;justify-content:center;margin:0;white-space:pre-wrap;font-size:15px}
.mermaid svg{max-width:none!important;height:auto}.status{padding:0 20px 16px;color:var(--muted);font-size:13px}.status.error{color:#9c3030}
.legend{display:flex;flex-wrap:wrap;gap:10px 18px;margin:16px 0 28px;color:#4d6574;font-size:14px}
.legend span::before{content:"";display:inline-block;width:13px;height:13px;margin-right:7px;vertical-align:-2px;border:1px solid #b9cad2;border-radius:3px;background:#e8f3ff}
.legend .decision::before{background:#fff2d8}.legend .success::before{background:#dcf4e8}.legend .stop::before{background:#fce6e6}
.notes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.notes article{padding:18px 19px;border-top:3px solid #93b7cc;background:#fff}
.notes h3{margin:0 0 5px;font-size:16px}.notes p{margin:0;color:#4d6574;font-size:14px}
footer{margin-top:30px;padding-top:20px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
code{background:#e8eef1;border-radius:4px;padding:1px 4px}
@media(max-width:760px){.notes{grid-template-columns:1fr}.notice{display:block}.notice strong{display:block;margin-bottom:3px}.diagram-viewport{padding:12px}}
"""

TEMPLATE = """<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="__SUBTITLE__">
  <title>__TITLE__ · Metadata Registry</title>
  <style>__STYLE__</style>
</head>
<body>
  <header><div class="wrap topline">
    <div class="brand">METADATA REGISTRY · RELEASE</div>
    <nav aria-label="แผนภาพ release">
      <a href="decision-tree.html" __DECISION_CURRENT__>Decision tree</a>
      <a href="flow-chart.html" __FLOW_CURRENT__>Flow chart</a>
      <a href="../../runbooks/release-delivery.md">Runbook</a>
    </nav>
  </div></header>
  <main class="wrap">
    <div class="eyebrow">RELEASE WORKFLOW / __KICKER__</div>
    <h1>__TITLE__</h1>
    <p class="lead">__SUBTITLE__</p>
    <div class="notice"><strong>สถานะปัจจุบัน · u2m</strong><span>Push เข้า <code>master</code> จะสร้าง GitHub Release อัตโนมัติ จากนั้นผู้ใช้ checkout release tag, login Databricks และรัน <code>scripts/deliver_release.sh</code> เพื่อส่งและ activate</span></div>
    <div class="meta"><a href="__SLUG__.mmd" download>ดาวน์โหลด Mermaid source (.mmd)</a><span>·</span><a href="__OTHER__.html">ดู __OTHER_LABEL__</a><span>·</span><a href="../../config/env/dev.yaml">config/env/dev.yaml</a></div>
    <section class="diagram-shell" aria-labelledby="diagram-title">
      <div class="diagram-top"><h2 id="diagram-title">แผนภาพ</h2><span>เลื่อนภายในภาพเพื่อดูส่วนที่อยู่นอกจอ</span></div>
      <div class="diagram-viewport"><pre class="mermaid" id="diagram">__SOURCE__</pre></div>
      <div class="status" id="render-status" role="status" aria-live="polite">กำลังแสดงแผนภาพ…</div>
    </section>
    <div class="legend" aria-label="คำอธิบายสี"><span>ขั้นตอน</span><span class="decision">จุดตัดสินใจ</span><span class="success">สำเร็จ</span><span class="stop">หยุดหรือแก้ไข</span></div>
    <section class="notes" aria-label="วิธีอ่านแผนภาพ">__NOTES__</section>
    <footer>อ้างอิงจาก <a href="../../.github/workflows/ci.yml">ci.yml</a>, <a href="../../.github/workflows/security.yml">security.yml</a>, <a href="../../.github/workflows/release.yml">release.yml</a>, <a href="../../.github/workflows/deploy-dev.yml">deploy-dev.yml</a>, <a href="../../scripts/deliver_release.sh">deliver_release.sh</a> และ <a href="../../scripts/next_steps.py">next_steps.py</a></footer>
  </main>
  <script type="module">
    const status = document.getElementById("render-status");
    try {
      const { default: mermaid } = await import("https://cdn.jsdelivr.net/npm/mermaid@11.16.1/dist/mermaid.esm.min.mjs");
      mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "base", themeVariables: { fontFamily: "Tahoma, Segoe UI, sans-serif", background: "#ffffff", primaryColor: "#e8f3ff", primaryTextColor: "#182b3a", primaryBorderColor: "#5584a6", lineColor: "#6c8492", secondaryColor: "#fff2d8", tertiaryColor: "#dcf4e8" }, flowchart: { useMaxWidth: false, htmlLabels: true, curve: "basis" } });
      await mermaid.run({ nodes: [document.getElementById("diagram")] });
      status.textContent = "แสดงแผนภาพแล้ว";
    } catch (error) {
      status.textContent = "โหลดแผนภาพไม่สำเร็จ: เปิดไฟล์ .mmd เพื่อดู Mermaid source หรือเชื่อมต่ออินเทอร์เน็ตแล้วโหลดหน้าใหม่";
      status.classList.add("error");
      console.error(error);
    }
  </script>
</body>
</html>
"""


def main() -> None:
    for slug, page in PAGES.items():
        other = "flow-chart" if slug == "decision-tree" else "decision-tree"
        notes = "\n".join(
            f"<article><h3>{escape(title)}</h3><p>{escape(body)}</p></article>"
            for title, body in page["notes"]
        )
        replacements = {
            "__STYLE__": STYLE,
            "__TITLE__": escape(page["title"]),
            "__SUBTITLE__": escape(page["subtitle"], quote=True),
            "__SLUG__": slug,
            "__OTHER__": other,
            "__OTHER_LABEL__": "flow chart" if other == "flow-chart" else "decision tree",
            "__KICKER__": "DECISIONS" if slug == "decision-tree" else "SEQUENCE",
            "__DECISION_CURRENT__": 'aria-current="page"' if slug == "decision-tree" else "",
            "__FLOW_CURRENT__": 'aria-current="page"' if slug == "flow-chart" else "",
            "__SOURCE__": escape((ROOT / f"{slug}.mmd").read_text(encoding="utf-8")),
            "__NOTES__": notes,
        }
        content = TEMPLATE
        for key, value in replacements.items():
            content = content.replace(key, value)
        output = ROOT / f"{slug}.html"
        output.write_text(content, encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
