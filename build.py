#!/usr/bin/env python3
"""Build dist/native-nihongo.apkg from data/cards.json + media/.

- Fixed model/deck IDs and per-note guid "nn-<id>": re-importing a newer
  package into Anki updates existing cards in place and keeps review history.
  The field set never changes; only templates/CSS/rendering evolve
  (restyled 2026-11-13 at the user's request, modelled on the eggrolls
  JLPT deck he uses: labelled ［例］/［訳］/［搭］/［関］ sections, furigana
  on examples, the headword highlighted inside its example, per-example
  audio buttons, related words with their own audio, and a 🔍 that jumps
  to the MOJi dictionary - app scheme mojisho:// on mobile,
  mojidict.com/searchText on the web).
- Fields: Front / Reading / Meaning / SenseExamples / Collocations /
  FrontAudio / ExampleAudio. Category is stored as a tag.
- Register/similarity links (cards.json "pairs", v2): each entry is either
  {"id", "register", "note"?} pointing at another card, or a text entry
  {"front", "reading", "meaning", "register", "note"?} for counterparts too
  basic to deserve their own card. register is 口语／书面／敬语／類似; a card
  may carry several entries (multi-way groups). Links render into the
  Collocations field under ［関］ with the difference note; id entries also
  get a shared tag "pair_<min id>" and their front audio is embedded so the
  related word can be played in place.
"""
import html
import json
import os

import genanki
import pykakasi

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = 1738092451
DECK_ID = 2048691735
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
_KKS = pykakasi.kakasi()

CSS = """
.card { font-family: -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif;
  font-size: 19px; color: #2a251d; background: #faf7f0; line-height: 1.65; }
.nightMode .card, .card.nightMode { background: #20201e; color: #e9e4d8; }
.qhead { display: flex; align-items: center; justify-content: space-between;
  margin: 10px 2px 4px; }
.front { font-size: 34px; font-weight: 600; text-align: center; flex: 1; }
.tools { display: flex; align-items: center; gap: 2px; min-width: 76px; }
.Search { font-size: 20px; text-decoration: none; width: 36px; text-align: center; }
.Gpt { width: 36px; text-align: center; text-decoration: none; }
.Gpt img { width: 22px; height: 22px; vertical-align: middle; border-radius: 5px; }
.faudio { width: 40px; text-align: center; }
body.dense1 .card { font-size: 17px; }
body.dense1 .front { font-size: 29px; }
body.dense1 .rline, body.dense1 .meaning { font-size: 18px; }
body.dense1 .rel-front { font-size: 18px; }
body.dense1 .Gpt img { width: 19px; height: 19px; }
body.dense1 .Search { font-size: 18px; }
body.dense2 .card { font-size: 15.5px; line-height: 1.55; }
body.dense2 .front { font-size: 25px; }
body.dense2 .rline, body.dense2 .meaning { font-size: 16.5px; }
body.dense2 .rel-front { font-size: 16.5px; }
body.dense2 .tr, body.dense2 .rel-sub { font-size: 14.5px; }
body.dense2 .Gpt img { width: 17px; height: 17px; }
body.dense2 .Search { font-size: 16px; }
.sep { border: none; border-top: 1px solid #ddd3c0; margin: 12px 0; }
.nightMode .sep { border-top-color: #444444; }
.rline { font-size: 21px; color: #6b6151; }
.nightMode .rline { color: #b6ab97; }
.meaning { font-size: 20px; font-weight: 700; margin: 2px 0 4px; }
.sense { margin: 10px 0 14px; }
.gloss { font-weight: 600; margin-bottom: 2px; }
.num { color: #c96a1e; font-weight: 700; margin-right: 4px; }
.ex { display: flex; align-items: flex-start; gap: 6px; }
.tag { color: #a08b6d; font-size: 15px; white-space: nowrap; padding-top: 3px; }
.ex-text { flex: 1; }
.hl { color: #e07b39; font-weight: 700; }
ruby rt { font-size: 11px; color: #8a7f6a; }
.tr { color: #7d7466; font-size: 17px; }
.nightMode .tr { color: #a99f8d; }
.sec { margin: 10px 0; }
.sec-h { color: #a08b6d; font-size: 15px; margin-bottom: 2px; }
.col-list { margin: 0; padding-left: 20px; color: #33529e; }
.nightMode .col-list { color: #9db8ec; }
.rel { margin: 7px 0; }
.rel-head { display: flex; align-items: center; gap: 6px; }
.chip { font-size: 12px; color: #ffffff; background: #c98a3d; border-radius: 8px;
  padding: 1px 7px; white-space: nowrap; }
.rel-front { font-size: 20px; font-weight: 600; color: #1f6f5c; }
.nightMode .rel-front { color: #7fd1b9; }
.rel-read { color: #6b6151; }
.nightMode .rel-read { color: #b6ab97; }
.rel-audio { margin-left: auto; }
.rel-sub { color: #7d7466; font-size: 16px; }
.nightMode .rel-sub { color: #a99f8d; }
"""

QFMT = """
<header class="qhead">
<div class="tools">
<a class="Search" target="_blank" rel="noopener" title="MOJi辞書">🔍</a>
<a class="Gpt" target="_blank" rel="noopener" title="ChatGPT"><img src="https://chatgpt.com/favicon.ico" alt="ChatGPT"></a>
</div>
<div class="front">{{Front}}</div>
<div class="faudio">{{FrontAudio}}</div>
</header>
<script>
(function () {
  var w = "{{text:Front}}".replace(/〜/g, "").trim();
  if (!w) return;
  var mobile = /iPhone|iPad|Android/i.test(navigator.userAgent);
  var s = document.querySelector(".Search");
  if (s) {
    s.href = mobile
      ? "mojisho://?search=" + encodeURIComponent(w)
      : "https://www.mojidict.com/searchText/" + encodeURIComponent(w);
  }
  var g = document.querySelector(".Gpt");
  if (g) {
    var q = "日语「" + w + "」是什么意思？请给出读音、中文释义、常用搭配和3个日常例句，并说明它在口语和书面语里的区别。";
    g.href = "https://chatgpt.com/?q=" + encodeURIComponent(q);
  }
})();
</script>
"""

AFMT = """
{{FrontSide}}
<hr class="sep">
<div class="rline">{{Reading}}</div>
<div class="meaning">{{Meaning}}</div>
<div class="senses">{{SenseExamples}}</div>
{{#Collocations}}<hr class="sep"><div class="cols">{{Collocations}}</div>{{/Collocations}}
<script>
(function () {
  // 内容多的卡自动调小字号/图标，保证一屏看得完、重点不被淹没。
  var n = document.body.innerText.length;
  if (n > 1500) document.body.classList.add("dense2");
  else if (n > 850) document.body.classList.add("dense1");
})();
</script>
"""


def _has_kanji(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def stem_of(front):
    """Highlight stem: drop 〜 and trailing okurigana (用いる→用, 潰れる→潰)."""
    s = front.replace("〜", "").strip()
    while len(s) > 1 and "ぁ" <= s[-1] <= "ん":
        s = s[:-1]
    return s


def furigana_html(text, stem):
    """Segment with pykakasi, add <ruby> over kanji segments, and wrap the
    first segment matching the headword stem in a highlight span."""
    out = []
    highlighted = False
    for seg in _KKS.convert(text):
        orig, hira = seg["orig"], seg["hira"]
        if orig != hira and _has_kanji(orig):
            piece = f"<ruby>{html.escape(orig)}<rt>{html.escape(hira)}</rt></ruby>"
        else:
            piece = html.escape(orig)
        if (
            not highlighted
            and stem
            and _has_kanji(stem)
            and (orig == stem or orig.startswith(stem))
        ):
            piece = f'<span class="hl">{piece}</span>'
            highlighted = True
        out.append(piece)
    return "".join(out)


def ex_filename(card_id, idx):
    return f"{card_id}_ex.mp3" if idx == 0 else f"{card_id}_ex{idx + 1}.mp3"


def render_senses(card, media_set):
    stem = stem_of(card["front"])
    blocks = []
    for i, s in enumerate(card["senses"]):
        num = CIRCLED[i] if i < len(CIRCLED) else f"{i + 1}."
        audio = ""
        fname = ex_filename(card["id"], i)
        if fname in media_set:
            audio = f'<span class="ex-audio">[sound:{fname}]</span>'
        blocks.append(
            '<div class="sense">'
            f'<div class="gloss"><span class="num">{num}</span>{html.escape(s["gloss"])}</div>'
            f'<div class="ex"><span class="tag">［例］</span>'
            f'<span class="ex-text">{furigana_html(s["example"], stem)}</span>{audio}</div>'
            f'<div class="tr"><span class="tag">［訳］</span>{html.escape(s["example_zh"])}</div>'
            "</div>"
        )
    return "".join(blocks)


def render_collocations(card, by_id, media_set):
    parts = []
    if card["collocations"]:
        items = "".join(
            f"<li>{html.escape(x)}</li>" for x in card["collocations"]
        )
        parts.append(
            f'<div class="sec"><div class="sec-h">［搭］</div>'
            f'<ul class="col-list">{items}</ul></div>'
        )
    rels = []
    for p in card.get("pairs", []):
        if "id" in p:
            other = by_id.get(p["id"])
            if other is None:
                continue
            d_front, d_reading, d_meaning = (
                other["front"], other["reading"], other["meaning"])
            audio = ""
            fname = f"{p['id']}_front.mp3"
            if fname in media_set:
                audio = f'<span class="rel-audio">[sound:{fname}]</span>'
        else:
            d_front, d_reading, d_meaning = (
                p["front"], p["reading"], p["meaning"])
            audio = ""
        sub = html.escape(d_meaning)
        if p.get("note"):
            sub += f"（{html.escape(p['note'])}）"
        rels.append(
            '<div class="rel"><div class="rel-head">'
            f'<span class="chip">{html.escape(p["register"])}</span>'
            f'<span class="rel-front">{html.escape(d_front)}</span>'
            f'<span class="rel-read">（{html.escape(d_reading)}）</span>{audio}</div>'
            f'<div class="rel-sub">{sub}</div></div>'
        )
    if rels:
        parts.append(
            '<div class="sec"><div class="sec-h">［関］</div>' + "".join(rels) + "</div>"
        )
    return "".join(parts)


def main():
    cards = json.load(open(os.path.join(BASE, "data", "cards.json"), encoding="utf-8"))
    media_dir = os.path.join(BASE, "media")
    media_set = {
        f for f in os.listdir(media_dir)
        if os.path.getsize(os.path.join(media_dir, f)) > 0
    }

    model = genanki.Model(
        MODEL_ID,
        "native-nihongo",
        fields=[
            {"name": "Front"},
            {"name": "Reading"},
            {"name": "Meaning"},
            {"name": "SenseExamples"},
            {"name": "Collocations"},
            {"name": "FrontAudio"},
            {"name": "ExampleAudio"},
        ],
        templates=[{"name": "Card 1", "qfmt": QFMT, "afmt": AFMT}],
        css=CSS,
    )

    deck = genanki.Deck(DECK_ID, "native-nihongo")
    by_id = {c["id"]: c for c in cards}
    media_files = []
    for c in cards:
        front_mp3 = f"{c['id']}_front.mp3"
        ex_mp3 = f"{c['id']}_ex.mp3"
        front_audio = f"[sound:{front_mp3}]" if front_mp3 in media_set else ""
        ex_audio = f"[sound:{ex_mp3}]" if ex_mp3 in media_set else ""
        used = {front_mp3, ex_mp3} | {
            ex_filename(c["id"], i) for i in range(len(c["senses"]))
        }
        if "pairs" in c:
            used |= {f"{p['id']}_front.mp3" for p in c["pairs"] if "id" in p}
        for fname in sorted(used):
            if fname in media_set:
                media_files.append(os.path.join(media_dir, fname))
        pair_tags = [
            f"pair_{min(c['id'], p['id'])}" for p in c.get("pairs", []) if "id" in p
        ]
        note = genanki.Note(
            model=model,
            fields=[
                c["front"],
                c["reading"],
                c["meaning"],
                render_senses(c, media_set),
                render_collocations(c, by_id, media_set),
                front_audio,
                ex_audio,
            ],
            tags=[c["cat"]] + sorted(set(pair_tags)),
            guid=f"nn-{c['id']}",
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = sorted(set(media_files))
    out = os.path.join(BASE, "dist", "native-nihongo.apkg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    package.write_to_file(out)
    print(f"notes={len(cards)} media={len(package.media_files)} -> {out}")


if __name__ == "__main__":
    main()
