#!/usr/bin/env python3
"""Fourth linking pass: word-formation families (user asked for more coverage).

The deck's unlinked mass is mostly compound verbs and noun idioms, which have
no register twin but DO form families sharing one building block. This pass
links, with register 類似 and a family note explaining the shared element:
  A. noun idiom families: fronts built on 手/気/目/口/耳/頭/胸/心/顔/足/身/
     肩/腰/腹/声/腕/鼻/息/首/背 + a particle — chunked into cliques of <=6.
  B. compound-verb suffix families (〜込む/〜出す/〜切る/…): bare verbs in
     動詞搭配, chunked cliques of <=6, note gives the suffix nuance.
  C. a few hand-checked IT contrast pairs / text entries.
  D. 敬語 stragglers: 〜いただけますでしょうか / 〜いただけますと幸いです
     variants linked back to their ご〜ください base card when it exists.
Excludes: ・-joined fronts, 〜 grammar, literal phrases (水 family dropped),
known false positives. Idempotent; only touches data/cards.json.
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS_JSON = os.path.join(REPO, "data", "cards.json")
cards = json.load(open(CARDS_JSON, encoding="utf-8"))
by_front = {c["front"]: c for c in cards}
by_id = {c["id"]: c for c in cards}

EDGES = []       # (front_a, front_b, register, note)
TEXT_EDGES = []  # (front, entry dict)


def pair(a, b, register, note):
    if a != b:
        EDGES.append((a, b, register, note))


def clique(members, register, note, cap=6):
    ms = sorted(set(members))
    for i in range(0, len(ms), cap):
        chunk = ms[i:i + cap]
        for x in chunk:
            for y in chunk:
                if x < y:
                    pair(x, y, register, note)


def text(front, t_front, t_reading, t_meaning, register, note):
    TEXT_EDGES.append((front, {"front": t_front, "reading": t_reading,
                                "meaning": t_meaning, "register": register,
                                "note": note}))


unlinked = {c["front"] for c in cards if not c.get("pairs")}

# ---------------------------------------------------------------------------
# A. noun idiom families
# ---------------------------------------------------------------------------
NOUN_NOTE = {
    "手": "同じ『手』の慣用句家族：手は手段・技能・手伝いまで表す万能の名詞。動詞との組み合わせで意味が決まる",
    "気": "同じ『気』の慣用句家族：気は気持ちの動きを表す中心語。〜なる/する/を使うで方向が変わる",
    "目": "同じ『目』の慣用句家族：目は見ること・注目・判断を表す",
    "口": "同じ『口』の慣用句家族：口は話すこと・味・出入り口を表す",
    "耳": "同じ『耳』の慣用句家族：耳は聞くこと全般を表す",
    "頭": "同じ『頭』の慣用句家族：頭は思考・態度・立場を表す",
    "胸": "同じ『胸』の慣用句家族：胸は感情の座。本心や安堵が表れる場所",
    "心": "同じ『心』の慣用句家族：心は気持ちそのもの。心の動きを表す表現群",
    "顔": "同じ『顔』の慣用句家族：顔は体面（メンツ）と表情の両方を表す",
    "足": "同じ『足』の慣用句家族：足は移動と土台を表す",
    "身": "同じ『身』の慣用句家族：身は身体・自分・立場を表す",
    "肩": "同じ『肩』の慣用句家族：肩は負担・責任・味方を表す",
    "腰": "同じ『腰』の慣用句家族：腰は姿勢と本気度・粘りを表す",
    "腹": "同じ『腹』の慣用句家族：腹は本心と怒りの座",
    "声": "同じ『声』の慣用句家族：声は呼びかけと発声を表す",
    "腕": "同じ『腕』の慣用句家族：腕は技術と腕力を表す",
    "鼻": "同じ『鼻』の慣用句家族：鼻は自慢と嗅覚を表す",
    "息": "同じ『息』の慣用句家族：息は呼吸と間の取り方を表す",
    "首": "同じ『首』の慣用句家族：首は命・関与・解雇まで表す",
    "背": "同じ『背』の慣用句家族：背は後ろ姿と姿勢を表す",
}
EXCLUDE_A = {"聞き手の関心を引きつける", "勝手にしろよ", "不足を補う",
             "音声が途切れる", "手が離れた存在"}
fam = {}
for c in cards:
    f = c["front"]
    if f in EXCLUDE_A:
        continue
    if "・" in f or "〜" in f or len(f) > 12:
        continue
    for n in NOUN_NOTE:
        if re.search(n + r"[をがにのへ]", f):
            fam.setdefault(n, []).append(f)
            break
for n, g in fam.items():
    if len(g) >= 2:
        clique(g, "類似", NOUN_NOTE[n])
        print(f"A:{n} {len(g)}")

# ---------------------------------------------------------------------------
# B. compound-verb suffix families
# ---------------------------------------------------------------------------
SUF_NOTE = {
    "込む": "複合動詞『〜込む』家族：中へ深く入る・入り込む・すっかり〜の状態になる",
    "出す": "複合動詞『〜出す』家族：外へ出す、または突然〜し始める",
    "切る": "複合動詞『〜切る』家族：最後まで・完全に〜する、断ち切る",
    "上げる": "複合動詞『〜上げる』家族：上へ、または完成させる",
    "落とす": "複合動詞『〜落とす』家族：下へ落とす、または見・聞き漏らす",
    "抜く": "複合動詞『〜抜く』家族：突き抜ける、最後まで〜し通す",
    "取る": "複合動詞『〜取る』家族：手に取る・受け取る・取り除く",
    "合う": "複合動詞『〜合う』家族：互いに〜し合う（相互）",
    "付く": "複合動詞『〜付く』家族：近付く・くっ付く・思いが及ぶ",
    "入れる": "複合動詞『〜入れる』家族：中へ入れる・受け入れる",
    "寄せる": "複合動詞『〜寄せる』家族：近くへ集める・近付ける",
}
sfam = {}
for c in cards:
    f = c["front"]
    if c["cat"] != "動詞搭配":
        continue
    if "・" in f or "〜" in f or "を" in f or "に" in f or "が" in f or len(f) > 7:
        continue
    for s in SUF_NOTE:
        if f.endswith(s) and len(f) > len(s):
            sfam.setdefault(s, []).append(f)
            break
for s, g in sfam.items():
    if len(g) >= 3:
        clique(g, "類似", SUF_NOTE[s])
        print(f"B:{s} {len(g)}")

# ---------------------------------------------------------------------------
# C. IT contrasts (existence-checked below)
# ---------------------------------------------------------------------------
pair("拡大する", "縮小する", "類似", "対の操作：拡大＝大きく表示；縮小＝小さく表示")
pair("読み込む", "書き込む", "類似",
     "データの対：読み込む＝読み取る・ロード；書き込む＝書き出す・保存")
text("無効化する", "有効化する", "ゆうこうかする", "启用、使有效", "類似",
     "反対の操作：有効化する＝オンにする；無効化する＝オフにする")
text("ログイン", "ログアウト", "ろぐあうと", "退出登录", "類似",
     "反対の操作：ログアウト＝サインアウト")

# ---------------------------------------------------------------------------
# D. 敬語 stragglers: derived polite variants back to their base card
# ---------------------------------------------------------------------------
hits = 0
for c in cards:
    f = c["front"]
    if f in unlinked and c["cat"] == "敬語":
        for suf in ("いただけますでしょうか", "いただけますと幸いです"):
            if f.endswith(suf):
                base = f[: -len(suf)] + "ください"
                if base in by_front:
                    pair(f, base, "類似",
                         "同じ依頼の言い換え：〜いただけますでしょうか＝確認・念押し版、〜いただけますと幸いです＝委婉版、〜ください＝直接版（礼貌阶梯）")
                    hits += 1
                break
print("D hits:", hits)

# ---------------------------------------------------------------------------
# Engine (same as v3)
# ---------------------------------------------------------------------------
def add_link(card, entry):
    pairs = card.setdefault("pairs", [])
    for e in pairs:
        if "id" in entry and e.get("id") == entry["id"]:
            return False
        if "id" not in entry and "id" not in e and e.get("front") == entry["front"]:
            return False
    pairs.append(entry)
    return True


missing, applied = [], 0
for a, b, register, note in EDGES:
    ca, cb = by_front.get(a), by_front.get(b)
    if ca is None or cb is None:
        missing.append((a, b))
        continue
    applied += add_link(ca, {"id": cb["id"], "register": register, "note": note})
    applied += add_link(cb, {"id": ca["id"], "register": register, "note": note})
for front, entry in TEXT_EDGES:
    c = by_front.get(front)
    if c is None:
        missing.append((front, entry["front"]))
        continue
    applied += add_link(c, entry)
if missing:
    print("MISSING:", missing)
    sys.exit(1)

json.dump(cards, open(CARDS_JSON, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
linked = sum(1 for c in cards if c.get("pairs"))
entries = sum(len(c.get("pairs", [])) for c in cards)
print(f"applied {applied}; cards with pairs {linked}/{len(cards)}; entries {entries}")
