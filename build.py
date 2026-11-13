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
  mojidict.com/searchText on the web - plus a ChatGPT icon that asks about
  the word; the icon is inlined into the template as a data URI - as a media
  file it never reached the phone, since no note field references it).
  v3 (same day, from the user's phone screenshots): everything left-aligned,
  Anki's oversized native play buttons CSS-sized to a uniform 30px, the
  duplicated meaning/gloss line removed on single-sense cards, furigana
  segmentation switched from pykakasi to Janome (pykakasi merged particles
  into one ruby block, e.g. 彼は口 read as one chunk).
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
from janome.tokenizer import Tokenizer

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = 1738092451
DECK_ID = 2048691735
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
ICON_FILE = "chatgpt-icon.png"
_TKZ = Tokenizer()

CSS = """
.card { font-family: -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif;
  font-size: 19px; color: #2a251d; background: #faf7f0; line-height: 1.65;
  text-align: left; }
.nightMode .card, .card.nightMode { background: #20201e; color: #e9e4d8; }
.qhead { display: flex; align-items: center; justify-content: space-between;
  margin: 10px 2px 4px; }
.front { font-size: 34px; font-weight: 600; text-align: center; flex: 1; }
.tools { display: flex; align-items: center; gap: 4px; min-width: 76px; }
.Search { font-size: 20px; text-decoration: none; width: 34px; text-align: center; }
.Gpt { width: 34px; text-align: center; text-decoration: none; }
.Gpt img { width: 23px; height: 23px; vertical-align: middle; border-radius: 6px;
  background: #111111; padding: 2px; box-sizing: border-box; }
.faudio { width: 76px; text-align: right; }
a.replaybutton, a.replay-button, button.replay-button {
  display: inline-flex !important; align-items: center; justify-content: center;
  width: 30px !important; height: 30px !important; vertical-align: middle; }
a.replaybutton img, a.replay-button img, a.replay-button svg,
button.replay-button svg, button.replay-button img {
  width: 30px !important; height: 30px !important; }
.sep { border: none; border-top: 1px solid #ddd3c0; margin: 12px 0; }
.nightMode .sep { border-top-color: #444444; }
.rline { font-size: 20px; color: #6b6151; letter-spacing: .02em; }
.nightMode .rline { color: #b6ab97; }
.meaning { font-size: 20px; font-weight: 700; margin: 2px 0 6px; }
.sense { margin: 10px 0 14px; border-left: 3px solid #ead9bd; padding-left: 10px; }
.nightMode .sense { border-left-color: #57492e; }
.gloss { font-weight: 600; margin-bottom: 2px; }
.num { color: #c96a1e; font-weight: 700; margin-right: 4px; }
.ex { display: flex; align-items: flex-start; gap: 6px; }
.tag { color: #a08b6d; font-size: 15px; white-space: nowrap; padding-top: 3px; }
.ex-text { flex: 1; }
.ex-audio { flex: none; }
.hl { color: #e07b39; font-weight: 700; }
ruby rt { font-size: 11px; color: #8a7f6a; }
.tr { color: #7d7466; font-size: 17px; }
.nightMode .tr { color: #a99f8d; }
.sec { margin: 12px 0; }
.sec-h { color: #a08b6d; font-size: 15px; margin-bottom: 3px; }
.col-list { margin: 0; padding: 0; list-style: none; color: #33529e; font-size: 17.5px; }
.nightMode .col-list { color: #9db8ec; }
.col-list li { margin: 2px 0; }
.col-list li::before { content: "・"; color: #c98a3d; }
.rel { margin: 7px 0; }
.rel-head { display: flex; align-items: center; gap: 6px; }
.chip { font-size: 12px; color: #ffffff; background: #c98a3d; border-radius: 8px;
  padding: 1px 7px; white-space: nowrap; }
.rel-front { font-size: 20px; font-weight: 600; color: #1f6f5c; }
.nightMode .rel-front { color: #7fd1b9; }
.rel-read { color: #6b6151; }
.nightMode .rel-read { color: #b6ab97; }
.rel-audio { margin-left: auto; flex: none; }
.rel-sub { color: #7d7466; font-size: 16px; }
.nightMode .rel-sub { color: #a99f8d; }
body.dense1 .card { font-size: 17px; }
body.dense1 .front { font-size: 29px; }
body.dense1 .rline, body.dense1 .meaning { font-size: 18px; }
body.dense1 .rel-front { font-size: 18px; }
body.dense2 .card { font-size: 15.5px; line-height: 1.55; }
body.dense2 .front { font-size: 25px; }
body.dense2 .rline, body.dense2 .meaning { font-size: 16.5px; }
body.dense2 .rel-front { font-size: 16.5px; }
body.dense2 .tr, body.dense2 .rel-sub { font-size: 14.5px; }
"""

QFMT = """
<header class="qhead">
<div class="tools">
<a class="Search" target="_blank" rel="noopener" title="MOJi辞書">🔍</a>
<a class="Gpt" target="_blank" rel="noopener" title="ChatGPT"><img src="data:image/png;base64,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" alt="ChatGPT"></a>
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
  // 内容多的卡自动调小字号，保证一屏看得完、重点不被淹没（按钮尺寸不变）。
  var n = document.body.innerText.length;
  if (n > 1500) document.body.classList.add("dense2");
  else if (n > 850) document.body.classList.add("dense1");
})();
</script>
"""


def _has_kanji(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def _to_hira(s):
    return "".join(
        chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch for ch in s
    )


def stem_of(front):
    """Highlight stem: drop 〜 and trailing okurigana (用いる→用, 潰れる→潰)."""
    s = front.replace("〜", "").strip()
    while len(s) > 1 and "ぁ" <= s[-1] <= "ん":
        s = s[:-1]
    return s


def furigana_html(text, stem):
    """Tokenize with Janome, add <ruby> over kanji tokens with a known
    reading, and wrap the first token matching the headword stem in a
    highlight span."""
    out = []
    highlighted = False
    for tok in _TKZ.tokenize(text):
        surf = tok.surface
        reading = _to_hira(tok.reading) if tok.reading and tok.reading != "*" else None
        if reading and reading != _to_hira(surf) and _has_kanji(surf):
            piece = f"<ruby>{html.escape(surf)}<rt>{html.escape(reading)}</rt></ruby>"
        else:
            piece = html.escape(surf)
        if (
            not highlighted
            and stem
            and _has_kanji(stem)
            and (surf == stem or surf.startswith(stem))
        ):
            piece = f'<span class="hl">{piece}</span>'
            highlighted = True
        out.append(piece)
    return "".join(out)


def ex_filename(card_id, idx):
    return f"{card_id}_ex.mp3" if idx == 0 else f"{card_id}_ex{idx + 1}.mp3"


def render_senses(card, media_set):
    stem = stem_of(card["front"])
    multi = len(card["senses"]) > 1
    # On single-sense cards the standalone Meaning line already carries the
    # gloss; repeating it as a ① line is pure duplication. Keep the gloss
    # line only for multi-sense cards, or when Meaning is empty.
    show_gloss = multi or not card["meaning"].strip()
    blocks = []
    for i, s in enumerate(card["senses"]):
        gloss_html = ""
        if show_gloss:
            num = ""
            if multi:
                n = CIRCLED[i] if i < len(CIRCLED) else f"{i + 1}."
                num = f'<span class="num">{n}</span>'
            gloss_html = f'<div class="gloss">{num}{html.escape(s["gloss"])}</div>'
        audio = ""
        fname = ex_filename(card["id"], i)
        if fname in media_set:
            audio = f'<span class="ex-audio">[sound:{fname}]</span>'
        blocks.append(
            '<div class="sense">'
            + gloss_html
            + f'<div class="ex"><span class="tag">［例］</span>'
            f'<span class="ex-text">{furigana_html(s["example"], stem)}</span>{audio}</div>'
            f'<div class="tr"><span class="tag">［訳］</span>{html.escape(s["example_zh"])}</div>'
            "</div>"
        )
    return "".join(blocks)


def render_collocations(card, by_id, media_set):
    parts = []
    cols = [x for x in card["collocations"] if x.strip() != card["front"].strip()]
    if cols:
        items = "".join(f"<li>{html.escape(x)}</li>" for x in cols)
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
