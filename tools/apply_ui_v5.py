#!/usr/bin/env python3
"""UI v5 data pass (user's 2026-11-14 card-UI brief, sections 4-5):
- Give pair registers a real taxonomy for chip display:
  family edges (note starts 同じ『…』)      -> 慣用句
  suffix-family edges (note starts 複合動詞『〜) -> 関連
  every other 類似                            -> 近義
- Mark true antonym links 反対 (拡大/縮小 both ways, add 増やす/減らす,
  and the two one-way text entries 有効化/ログアウト).
- Add a 思う/考える contrast pair if both cards exist and are unlinked.
Only touches data/cards.json; idempotent.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(REPO, "data", "cards.json")
cards = json.load(open(PATH, encoding="utf-8"))
by_front = {c["front"]: c for c in cards}

changed = 0
for c in cards:
    for p in c.get("pairs", []):
        note = p.get("note") or ""
        if note.startswith("同じ『"):
            new = "慣用句"
        elif note.startswith("複合動詞『〜"):
            new = "関連"
        elif p["register"] == "類似":
            new = "近義"
        else:
            continue
        if p["register"] != new:
            p["register"] = new
            changed += 1


def set_reg(a, b, reg):
    """Set register on a->b entry (id or text), if present."""
    ca = by_front.get(a)
    if not ca:
        return
    for p in ca.get("pairs", []):
        tgt = p.get("front")
        if "id" in p:
            tgt = next((c["front"] for c in cards if c["id"] == p["id"]), None)
        if tgt == b and p["register"] != reg:
            p["register"] = reg


set_reg("拡大する", "縮小する", "反対")
set_reg("縮小する", "拡大する", "反対")
set_reg("無効化する", "有効化する", "反対")
set_reg("ログイン", "ログアウト", "反対")


def add_link(card, entry):
    pairs = card.setdefault("pairs", [])
    for e in pairs:
        if "id" in entry and e.get("id") == entry["id"]:
            return False
        if "id" not in entry and "id" not in e and e.get("front") == entry["front"]:
            return False
    pairs.append(entry)
    return True


def pair(a, b, register, note):
    ca, cb = by_front.get(a), by_front.get(b)
    if ca and cb:
        add_link(ca, {"id": cb["id"], "register": register, "note": note})
        add_link(cb, {"id": ca["id"], "register": register, "note": note})


pair("増やす", "減らす", "反対",
     "正反対の操作：増やす＝使って多くする；減らす＝使って少なくする")
pair("思う", "考える", "近義",
     "思う＝心里的感觉・直觉（とっさの判断）；考える＝动脑整理・认真考虑（時間をかけて検討）。「と思います」是亮明想法，「考えます」是要去想清楚")

json.dump(cards, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
regs = {}
for c in cards:
    for p in c.get("pairs", []):
        regs[p["register"]] = regs.get(p["register"], 0) + 1
print("register changes:", changed, "| register totals:", regs)
