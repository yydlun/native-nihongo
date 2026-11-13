#!/usr/bin/env python3
"""Pitch-accent data pass: match cards against the kanjium accent
dictionary (accents.txt: word<TAB>reading<TAB>accent numbers; source
https://github.com/mifunetoshiro/kanjium, data CC BY-SA).
- Exact (word, reading) match -> accent = first listed value.
- Word-only match accepted only when every dictionary entry for the word
  agrees on the same first accent value.
Writes `accent` (int) into data/cards.json. Phrases/idioms have no
dictionary accent and are left unmarked on purpose.
Usage: python3 tools/apply_accent.py [path-to-accents.txt]
"""
import json
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/accents1.txt"
cards = json.load(open(os.path.join(REPO, "data", "cards.json"), encoding="utf-8"))
exact = {}
by_word = defaultdict(set)
for line in open(SRC, encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) != 3:
        continue
    m = re.search(r"\d+", p[2])
    if not m:
        continue
    first = int(m.group())
    exact[(p[0], p[1])] = first
    by_word[p[0]].add(first)
n_exact = n_word = 0
for c in cards:
    a = exact.get((c["front"], c["reading"]))
    if a is None and len(by_word.get(c["front"], ())) == 1:
        a = next(iter(by_word[c["front"]]))
        n_word += 1
    elif a is not None:
        n_exact += 1
    if a is not None:
        c["accent"] = a
json.dump(cards, open(os.path.join(REPO, "data", "cards.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"accent set: exact {n_exact}, word-only-agreeing {n_word}, total {n_exact + n_word}/{len(cards)}")
