# -*- coding: utf-8 -*-
"""index.src.html の文章に BudouX で文節区切り（ゼロ幅スペース）を入れて index.html を生成します。
文言を直したいときは index.src.html を編集し、 python3 budoux_apply.py を実行してください。"""
import budoux, re
from bs4 import BeautifulSoup, NavigableString
parser = budoux.load_default_japanese_parser()
SEL = ".lead, .tl p, .member p, .member li, .plan .for, details .a, .plan-notes li, summary, .micro, .about-grid li, .card li, .points li, .area span, footer p, .hero .sub, .report q, .report .meta dd, .team-note li, h2 .l, h2, .about-grid h3, .card h3, .plan li, .exp b, .exp span, .member .msg, .member p, .member li, .handoff-k, .hero .phil"
soup = BeautifulSoup(open("index.src.html", encoding="utf-8"), "html.parser")
ZW = "​"
def seg(text):
    if not re.search(r"[ぁ-んァ-ン一-龥]", text): return text
    return ZW.join(parser.parse(text))
done = 0
for el in soup.select(SEL):
    for node in list(el.descendants):
        if isinstance(node, NavigableString) and node.parent.name not in ("script","style") and node.strip():
            node.replace_with(NavigableString(seg(str(node))))
    style = el.get("style","")
    if "keep-all" not in style:
        el["style"] = (style + ";" if style else "") + "word-break:keep-all;overflow-wrap:anywhere"
    done += 1
open("index.html","w",encoding="utf-8").write(str(soup))
print("segmented elements:", done)
