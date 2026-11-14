#!/usr/bin/env python3
"""Reading audit for cards.json.

Check A (dictionary): every card whose front (or a ・-separated part of it)
is a JMdict headword must have its curated reading among the dictionary's
readings for that kanji form. Mismatches are split into:
  - CERTAIN: the dictionary lists exactly one reading, the card differs.
  - REVIEW:  the dictionary lists several readings, the card's is not one.
Fronts not in JMdict (phrases, grammar patterns, slang) are skipped -
no dictionary can judge them.

Check B (furigana): wherever a card's own front appears verbatim in its
own examples/collocations, the tokenizer's ruby over that span must agree
with the card's curated reading. Catches tokenizer splits/misreads of
deck vocabulary (the 実店舗 class of bug) in rendered furigana.

Reads: data/cards.json, /tmp/jmdict (unzipped jmdict-simplified json).
Writes: tools/audit_report.json (report only; never edits card data).

Dictionary source (re-download when /tmp is wiped):
https://github.com/scriptin/jmdict-simplified/releases/download/3.6.2%2B20261109214828/jmdict-eng-common-3.6.2%2B20261109214828.json.zip

Known-legit flags (verified 2026-11-14, do not "fix"):
- 1014 手取り てどり: the subset dictionary lists only てとり, but for the
  card's sense (net pay) てどり is the standard spoken reading.
- 2784 〜気味: citation reading きみ; in compounds it rendaku-es to ぎみ
  (風邪気味 かぜぎみ) - the tokenizer is contextually right there.
"""
import importlib.util
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("b", os.path.join(REPO, "build.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

cards = json.load(open(os.path.join(REPO, "data", "cards.json"), encoding="utf-8"))

# ---- JMdict: kanji text -> set of kana readings (respecting appliesToKanji)
jm_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/jmdict/jmdict-eng-common.json"
jm = json.load(open(jm_path, encoding="utf-8"))
jm_readings = {}
for w in jm["words"]:
    for k in w.get("kanji", []):
        rs = set()
        for kana in w.get("kana", []):
            applies = kana.get("appliesToKanji", ["*"])
            if "*" in applies or k["text"] in applies:
                rs.add(kana["text"])
        if rs:
            jm_readings.setdefault(k["text"], set()).update(rs)


def hira(s):
    return b._to_hira(s or "")


def front_parts(front):
    parts = re.split(r"[・／/]", front)
    out = []
    for p in parts:
        p = p.strip().strip("〜~").strip()
        if p:
            out.append(p)
    return out


def reading_parts(reading):
    parts = re.split(r"[・／/]", reading or "")
    return [hira(p.strip().strip("〜~").strip()) for p in parts if p.strip()]


certain, review, checked = [], [], 0
for c in cards:
    fparts = front_parts(c["front"])
    rparts = reading_parts(c["reading"])
    for i, part in enumerate(fparts):
        if part in jm_readings:
            checked += 1
            dict_rs = {hira(r) for r in jm_readings[part]}
            mine = rparts[i] if len(rparts) == len(fparts) else hira(c["reading"].strip("〜~"))
            if mine not in dict_rs:
                item = {
                    "id": c["id"], "front": c["front"], "part": part,
                    "card_reading": mine,
                    "dict_readings": sorted(jm_readings[part]),
                }
                (certain if len(dict_rs) == 1 else review).append(item)

# ---- Check B: own front inside own examples/collocations.
# Only non-inflecting fronts (ending in kanji/katakana) whose exact form
# appears in the text: the tokenizer's reading over that exact span must
# equal the curated reading. Verb/adjective fronts inflect, so their
# in-text readings legitimately differ and are out of scope here.
b_flags = []
for c in cards:
    front = c["front"].strip("〜~")
    if not front or not b._has_kanji(front):
        continue
    if not re.search(r"[\u4e00-\u9fff\u30a0-\u30ff]$", front):
        continue
    texts = [s.get("example", "") for s in c["senses"]]
    texts += c.get("collocations", [])
    full = hira(c["reading"].strip("〜~"))
    for text in texts:
        if front not in text:
            continue
        toks = b._tokens(text)
        concat = "".join(t.surface for t in toks)
        start = concat.find(front)
        if start < 0:
            continue
        end = start + len(front)
        got, pos, aligned = "", 0, True
        for t in toks:
            nxt = pos + len(t.surface)
            if nxt > start and pos < end:
                if pos < start or nxt > end:
                    aligned = False
                got += hira(t.reading) if t.reading and t.reading != "*" else hira(t.surface)
            pos = nxt
        # katakana long-vowel notation differs by author (レビュー vs
        # れびゅう); treat ー and う as equivalent for this comparison
        got_n = got.replace("ー", "う")
        full_n = full.replace("ー", "う")
        if aligned and got and got_n != full_n:
            b_flags.append({
                "id": c["id"], "front": c["front"], "text": text,
                "tokenizer_reading": got, "card_reading": full,
            })

report = {"dict_checked_parts": checked, "certain": certain,
          "review": review, "furigana_flags": b_flags}
out = os.path.join(REPO, "tools", "audit_report.json")
json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"dict-checked parts: {checked}")
print(f"CERTAIN errors: {len(certain)}")
for x in certain:
    print("  ", x["id"], x["front"], "card:", x["card_reading"], "dict:", x["dict_readings"])
print(f"REVIEW (multi-reading mismatch): {len(review)}")
for x in review[:30]:
    print("  ", x["id"], x["front"], "card:", x["card_reading"], "dict:", x["dict_readings"])
print(f"FURIGANA flags: {len(b_flags)}")
for x in b_flags[:30]:
    print("  ", x["id"], x["front"], "|", x["text"][:40], "| tok:", x["tokenizer_reading"], "vs card:", x["card_reading"])
