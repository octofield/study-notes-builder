#!/usr/bin/env python3
"""檢查單檔 HTML 學習材料。

用法:
    python verify_html.py 檔案.html [--allow-external]

檢查項目:
  1. 外部資源請求 (script src / link href / img src / CSS url() / @import)
  2. 重複的 id
  3. 壞掉的站內錨點 (href="#xxx" 但沒有對應 id)
  4. 結構標籤是否成對
  5. 內嵌 JavaScript 語法 (需要 node)
  6. 圖文並茂提醒（警告，不影響結束碼）：文字很多卻沒有圖、表的小節，
     以及缺少替代文字的 <img> 與 <svg>
有錯誤時結束碼為 1。
"""
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

TRACKED = {"div", "section", "article", "nav", "main", "header", "footer", "aside",
           "ul", "ol", "table", "thead", "tbody", "details", "svg", "g", "pre", "script", "style"}
REQUEST_ATTRS = {("script", "src"), ("link", "href"), ("img", "src"), ("source", "src"),
                 ("iframe", "src"), ("video", "src"), ("audio", "src"), ("embed", "src")}


def is_external(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith(("http://", "https://", "//"))


class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.dup_ids = set(), set()
        self.anchors = []
        self.external = []
        self.stack = []
        self.tag_errors = []
        self.scripts = []
        self._in_script = False
        self._script_buf = []
        self._script_has_src = False
        self._script_type = ""
        self._in_style = False
        self.style_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a and a["id"]:
            if a["id"] in self.ids:
                self.dup_ids.add(a["id"])
            self.ids.add(a["id"])
        if tag == "a" and a.get("href", "").startswith("#") and len(a["href"]) > 1:
            self.anchors.append(a["href"][1:])
        for (t, attr) in REQUEST_ATTRS:
            if tag == t and attr in a and a[attr] and is_external(a[attr]):
                if tag == "link" and "stylesheet" not in (a.get("rel") or "").lower() and "preload" not in (a.get("rel") or "").lower():
                    continue
                self.external.append(f"<{tag} {attr}={a[attr][:80]}>")
        style = a.get("style", "")
        for m in re.finditer(r"url\(\s*['\"]?(https?:[^'\")\s]+|//[^'\")\s]+)", style):
            self.external.append(f"inline style url({m.group(1)[:80]})")
        if tag == "script":
            self._in_script = True
            self._script_buf = []
            self._script_has_src = "src" in a
            self._script_type = (a.get("type") or "").lower()
        if tag == "style":
            self._in_style = True
        if tag in TRACKED:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # <svg ... /> 或 <g ... /> 這類自閉合標籤不入堆疊
        a = dict(attrs)
        if "id" in a and a["id"]:
            if a["id"] in self.ids:
                self.dup_ids.add(a["id"])
            self.ids.add(a["id"])

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            self._in_script = False
            if not self._script_has_src and self._script_type in ("", "text/javascript", "module"):
                self.scripts.append((self._script_type, "".join(self._script_buf)))
        if tag == "style":
            self._in_style = False
        if tag in TRACKED:
            if not self.stack:
                self.tag_errors.append(f"第 {self.getpos()[0]} 行: 多出的 </{tag}>")
                return
            top, line = self.stack[-1]
            if top == tag:
                self.stack.pop()
            else:
                found = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
                if found is None:
                    self.tag_errors.append(f"第 {self.getpos()[0]} 行: 多出的 </{tag}>")
                else:
                    for t, l in self.stack[found + 1:]:
                        self.tag_errors.append(f"第 {l} 行: <{t}> 沒有關閉")
                    del self.stack[found:]

    def handle_data(self, data):
        if self._in_script:
            self._script_buf.append(data)
        if self._in_style:
            self.style_text.append(data)


VISUAL_RE = re.compile(r"<(svg|img|figure|canvas|table)\b|class=[\"'][^\"']*mermaid", re.I)


def visual_report(text: str, min_chars: int = 600):
    """依 <h2> 切成小節，找出文字多但沒有圖、表的小節，並檢查替代文字。"""
    body = re.sub(r"<(script|style)\b.*?</\1>", "", text, flags=re.S | re.I)
    parts = re.split(r"(?=<h2\b)", body, flags=re.I)
    plain_sections = []
    for part in parts:
        m = re.match(r"<h2\b[^>]*>(.*?)</h2>", part, flags=re.S | re.I)
        if not m:
            continue
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        plain = re.sub(r"<[^>]+>", "", part)
        plain = re.sub(r"\s+", "", plain)
        n_vis = len(VISUAL_RE.findall(part))
        plain_sections.append((title, len(plain), n_vis))
    text_walls = [(t, n) for t, n, v in plain_sections if n >= min_chars and v == 0]
    total_vis = sum(v for _, _, v in plain_sections)
    imgs_no_alt = len(re.findall(r"<img\b(?![^>]*\balt=)[^>]*>", body, flags=re.I))
    svgs_no_label = 0
    for m in re.finditer(r"<svg\b([^>]*)>(.*?)</svg>", body, flags=re.S | re.I):
        attrs, inner = m.group(1), m.group(2)
        if "aria-label" not in attrs and "aria-hidden" not in attrs and "<title" not in inner.lower():
            svgs_no_label += 1
    return plain_sections, text_walls, total_vis, imgs_no_alt, svgs_no_label


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_external = "--allow-external" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(2)
    path = Path(args[0])
    text = path.read_text(encoding="utf-8")
    c = Checker()
    c.feed(text)

    errors, warnings = [], []

    css = "".join(c.style_text)
    for m in re.finditer(r"url\(\s*['\"]?(https?:[^'\")\s]+|//[^'\")\s]+)", css):
        c.external.append(f"CSS url({m.group(1)[:80]})")
    for m in re.finditer(r"@import\s+(?:url\()?['\"]?(https?:[^'\")\s;]+)", css):
        c.external.append(f"CSS @import {m.group(1)[:80]}")

    if c.external:
        (warnings if allow_external else errors).append(
            f"外部資源請求 {len(c.external)} 項:\n    " + "\n    ".join(sorted(set(c.external))[:15]))
    if c.dup_ids:
        errors.append("重複的 id: " + ", ".join(sorted(c.dup_ids)[:15]))
    broken = sorted({a for a in c.anchors if a not in c.ids})
    if broken:
        errors.append("壞掉的站內錨點: " + ", ".join(broken[:15]))
    for t, l in c.stack:
        c.tag_errors.append(f"第 {l} 行: <{t}> 沒有關閉")
    if c.tag_errors:
        errors.append("標籤不成對:\n    " + "\n    ".join(c.tag_errors[:15]))

    node = shutil.which("node")
    if c.scripts and node:
        for i, (stype, code) in enumerate(c.scripts, 1):
            suffix = ".mjs" if stype == "module" else ".js"
            with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append(f"第 {i} 個內嵌 script 語法錯誤:\n    " + "\n    ".join(r.stderr.strip().splitlines()[:4]))
    elif c.scripts:
        warnings.append("找不到 node，略過內嵌 JavaScript 語法檢查")

    sections, walls, total_vis, imgs_no_alt, svgs_no_label = visual_report(text)
    if walls:
        warnings.append("以下小節文字很多但沒有圖或表，請考慮補圖（見 references/visual-design.md）:\n    "
                        + "\n    ".join(f"{t}（約 {n} 字）" for t, n in walls[:15]))
    if imgs_no_alt:
        warnings.append(f"{imgs_no_alt} 個 <img> 沒有 alt 替代文字")
    if svgs_no_label:
        warnings.append(f"{svgs_no_label} 個 <svg> 沒有 aria-label 或 <title>")

    size_kb = path.stat().st_size / 1024
    print(f"檔案: {path}  大小: {size_kb:.0f} KB  id 數: {len(c.ids)}  內嵌 script: {len(c.scripts)}  "
          f"小節數: {len(sections)}  圖表數: {total_vis}")
    for w in warnings:
        print("警告:", w)
    for e in errors:
        print("錯誤:", e)
    if not errors:
        print("通過")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
