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
import re

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
  text-align: left;
  padding-bottom: calc(96px + env(safe-area-inset-bottom, 0px)); }
.nightMode .card, .card.nightMode { background: #20201e; color: #eae5dc; }
.nightMode .hl { color: #e58a48; }
.nightMode .num { color: #e58a48; }
.nightMode ruby rt { color: #a99f90; }
.nightMode .tag { color: #a99f90; }
.qhead { display: flex; align-items: center; justify-content: space-between;
  margin: 6px 2px 2px; }
.front { font-size: 32px; font-weight: 600; text-align: center; flex: 1; min-width: 0; }
.tools { display: flex; align-items: center; gap: 4px; min-width: 76px; }
.Search { font-size: 16px; text-decoration: none; width: 27px; text-align: center; }
.Gpt { width: 27px; height: 27px;
  background-image: url("data:image/png;base64,__GPT_ICON_B64__");
  background-size: 100% 100%; background-position: center; background-repeat: no-repeat; }
.Dict { font-size: 15px; text-decoration: none; }
.WordLink { color: inherit; text-decoration: none; border-bottom: 1px dotted #d97706; }
.GptL { width: 19px; height: 19px;
  background-image: url("data:image/png;base64,__GPT_ICON_B64__");
  background-size: 100% 100%; background-position: center; background-repeat: no-repeat;
  display: inline-block; vertical-align: middle; }
.col-list .GptL { margin-left: 8px; }
.nightMode .Gpt, .nightMode .GptL, .night-mode .Gpt, .night-mode .GptL,
.night_mode .Gpt, .night_mode .GptL { filter: invert(1); }
.faudio { width: 76px; text-align: right; }
a.replaybutton, a.replay-button, button.replay-button {
  display: inline-flex !important; align-items: center; justify-content: center;
  width: 30px !important; height: 30px !important; border-radius: 50%; border: none;
  background-color: rgba(90, 75, 50, 0.08);
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20fill%3D%27%23c2540a%27%20d%3D%27M3%209.2v5.6c0%20.6.4%201%201%201h3.4L12%2019.6c.5.4%201.3.1%201.3-.6V5c0-.7-.8-1-1.3-.6L7.4%208.2H4c-.6%200-1%20.4-1%201z%27%2F%3E%3Cpath%20fill%3D%27none%27%20stroke%3D%27%23c2540a%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%20d%3D%27M15.6%209.2a4%204%200%200%201%200%205.6%27%2F%3E%3Cpath%20fill%3D%27none%27%20stroke%3D%27%23c2540a%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%20d%3D%27M18%206.8a7.4%207.4%200%200%201%200%2010.4%27%2F%3E%3C%2Fsvg%3E");
  background-repeat: no-repeat; background-position: center; background-size: 58% 58%;
  box-shadow: 0 2px 8px rgba(90, 75, 50, 0.12); vertical-align: middle; }
.nightMode a.replaybutton, .nightMode a.replay-button,
.night-mode a.replay-button, .night_mode a.replay-button {
  background-color: rgba(255, 255, 255, 0.10);
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20fill%3D%27%23f5ede0%27%20d%3D%27M3%209.2v5.6c0%20.6.4%201%201%201h3.4L12%2019.6c.5.4%201.3.1%201.3-.6V5c0-.7-.8-1-1.3-.6L7.4%208.2H4c-.6%200-1%20.4-1%201z%27%2F%3E%3Cpath%20fill%3D%27none%27%20stroke%3D%27%23f5ede0%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%20d%3D%27M15.6%209.2a4%204%200%200%201%200%205.6%27%2F%3E%3Cpath%20fill%3D%27none%27%20stroke%3D%27%23f5ede0%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%20d%3D%27M18%206.8a7.4%207.4%200%200%201%200%2010.4%27%2F%3E%3C%2Fsvg%3E");
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25); }
a.replaybutton:active, a.replay-button:active { transform: scale(0.93); }
a.replaybutton img, a.replay-button img, a.replay-button svg,
button.replay-button svg, button.replay-button img {
  display: none !important; }
.rel-audio a.replaybutton, .rel-audio a.replay-button,
.rel-audio button.replay-button {
  width: 22px; height: 22px; }
.rel-audio a.replaybutton, .rel-audio a.replay-button,
.rel-audio button.replay-button {
  width: 22px !important; height: 22px !important; }
.rel-audio a.replaybutton img, .rel-audio a.replay-button img,
.rel-audio a.replay-button svg, .rel-audio button.replay-button svg,
.rel-audio button.replay-button img {
  width: 22px !important; height: 22px !important; }
.rline { font-size: 16px; color: #6b6151; letter-spacing: .02em; margin-top: 2px; }
.accdata { display: none; }
.acc-h { border-top: 2px solid #c96a1e; padding-top: 1px; }
.nightMode .acc-h { border-top-color: #e58a48; }
.acc-d { color: #c96a1e; font-size: 12px; }
.nightMode .acc-d { color: #e58a48; }
.nightMode .rline { color: #a99f90; }
.meaning { font-size: 24px; font-weight: 700; margin: 12px 0 0; }
.senses { margin-top: 16px; }
.utags { display: flex; gap: 6px; flex-wrap: wrap; margin: 0 0 14px; }
.utag { font-size: 12px; color: #6f6154; border: 1px solid #d8cbb2;
  border-radius: 8px; padding: 0 7px; line-height: 1.7; }
.utag.reg { color: #ffffff; font-weight: 700; border-color: transparent;
  padding: 0 9px; }
.utag.reg.w { background: #4456a8; }
.utag.reg.o { background: #2e7d32; }
.nightMode .utag { color: #a99f90; border-color: #55503f; }
.sense { margin: 0 0 20px; border-left: 3px solid #ead9bd; padding-left: 9px; }
.nightMode .sense { border-left-color: #57492e; }
.gloss { font-weight: 600; font-size: 17px; color: #5d5342; margin-bottom: 4px; }
.nightMode .gloss { color: #beb4a4; }
.num { color: #c96a1e; font-weight: 700; margin-right: 4px; }
.ex { display: flex; align-items: flex-start; gap: 6px; }
.tag { color: #b39b78; font-size: 11.5px; white-space: nowrap; padding-top: 7px; }
.ex-text { flex: 1; min-width: 0; font-size: 18.5px; line-height: 1.6; line-break: strict; }
.u { white-space: nowrap; }
.ex-audio { flex: none; }
.hl { color: #e07b39; font-weight: 700; }
ruby rt { font-size: 11px; color: #8a7f6a; }
.tr { color: #6f6154; font-size: 16px; margin-top: 8px; }
.nightMode .tr { color: #beb4a4; }
.sec { margin: 19px 0 0; }
.sec-h { color: #a08b6d; font-size: 14px; margin-bottom: 6px; }
.col-list { margin: 0; padding: 0; list-style: none; color: #33529e; font-size: 17px; }
.nightMode .col-list { color: #72bceb; }
.col-list li { margin: 4px 0; }
.col-list li::before { content: "・"; color: #c98a3d; }
.rel { margin: 12px 0; }
.rel.g { margin: 8px 0; }
.rel-gh { display: flex; align-items: center; gap: 6px; margin: 14px 0 4px; }
.gh-note { font-size: 13.5px; color: #6f6154; flex: 1; min-width: 0; }
.nightMode .gh-note { color: #a99f90; }
.rel-head { display: flex; align-items: center; gap: 6px; }
.chip { font-size: 12px; color: #ffffff; background: #c98a3d; border-radius: 8px;
  padding: 1px 7px; white-space: nowrap; }
.c-oral { background: #2e7d32; }
.c-syn { background: #2563eb; }
.c-fam { background: #6483c4; }
.c-wri { background: #4456a8; }
.c-idi { background: #d97706; }
.c-kei { background: #8a6d3b; }
.c-ant { background: #b3402e; }
.rel-front { font-size: 17px; font-weight: 600; color: #1f6f5c; min-width: 0; }
.nightMode .rel-front { color: #73bba5; }
.rel-read { color: #7a6f5e; font-size: 15px; }
.nightMode .rel-read { color: #a99f90; }
.rel-audio { margin-left: auto; flex: none; }
.rel-sub { color: #4f463a; font-size: 16px; }
.nightMode .rel-sub { color: #beb4a4; }
body.dense1 .card { font-size: 17px; }
body.dense1 .front { font-size: 28px; }
body.dense1 .rline { font-size: 15px; }
body.dense1 .meaning { font-size: 21px; }
body.dense1 .ex-text { font-size: 17px; }
body.dense1 .gloss { font-size: 15.5px; }
body.dense1 .rel-front { font-size: 15.5px; }
body.dense2 .card { font-size: 15.5px; line-height: 1.55; }
body.dense2 .front { font-size: 24px; }
body.dense2 .rline { font-size: 14.5px; }
body.dense2 .meaning { font-size: 19px; }
body.dense2 .ex-text { font-size: 16px; }
body.dense2 .gloss { font-size: 14.5px; }
body.dense2 .rel-front { font-size: 14.5px; }
body.dense2 .tr, body.dense2 .rel-sub { font-size: 14.5px; }
"""

QFMT = """
<header class="qhead">
<div class="tools">
<a class="Search" data-w="{{text:Front}}" target="_blank" rel="noopener" title="MOJi辞書">🔍</a>
<a class="Gpt" data-w="{{text:Front}}" target="_blank" rel="noopener" title="ChatGPT"></a>
</div>
<div class="front">{{Front}}</div>
<div class="faudio">{{FrontAudio}}</div>
</header>
<script>
(function () {
  var mobile = /iPhone|iPad|Android/i.test(navigator.userAgent);
  document.querySelectorAll("[data-w]").forEach(function (a) {
    var w = (a.getAttribute("data-w") || "").replace(/〜/g, "").trim();
    if (!w) return;
    if (a.classList.contains("Gpt") || a.classList.contains("GptL")) {
      var q = "日语「" + w + "」是什么意思？请给出读音、中文释义、常用搭配和3个日常例句，并说明它在口语和书面语里的区别。";
      a.href = "https://chatgpt.com/?q=" + encodeURIComponent(q);
    } else {
      a.href = mobile
        ? "mojisho://?search=" + encodeURIComponent(w)
        : "https://www.mojidict.com/searchText/" + encodeURIComponent(w);
    }
  });
})();
</script>
"""

AFMT = """
{{FrontSide}}
<div class="rline">{{Reading}}</div>
<div class="meaning">{{Meaning}}</div>
<div class="senses">{{SenseExamples}}</div>
{{#Collocations}}<div class="cols">{{Collocations}}</div>{{/Collocations}}
<script>
(function () {
  // 内容多的卡自动调小字号，保证一屏看得完、重点不被淹没（按钮尺寸不变）。
  var n = document.body.innerText.length;
  if (n > 1500) document.body.classList.add("dense2");
  else if (n > 850) document.body.classList.add("dense1");
})();
</script>
<script>
try {
  var d = document.querySelector(".accdata");
  var r = document.querySelector(".rline");
  if (d && r) {
    var acc = parseInt(d.getAttribute("data-acc"), 10);
    var s = r.textContent.replace(/\s+/g, "");
    var small = "ゃゅょャュョ";
    var morae = [];
    for (var i = 0; i < s.length; i++) {
      var ch = s.charAt(i);
      if (small.indexOf(ch) >= 0 && morae.length) morae[morae.length - 1] += ch;
      else morae.push(ch);
    }
    var n = morae.length, out = "";
    for (var j = 0; j < n; j++) {
      var high;
      if (acc === 0) high = j >= 1;
      else if (acc === 1) high = j === 0;
      else high = j >= 1 && j < acc;
      out += high ? '<span class="acc-h">' + morae[j] + "</span>" : morae[j];
      if (acc >= 1 && j === acc - 1) out += '<span class="acc-d">\ua71c</span>';
    }
    if (n > 0) r.innerHTML = out;
  }
} catch (e) {}
</script>
"""


def _css_with_icon(media_dir):
    """Inline the ChatGPT icon into the model CSS (stored once, always
    available; a media-file icon never synced to the phone because no note
    field references it)."""
    import base64

    path = os.path.join(media_dir, ICON_FILE)
    b64 = ""
    if os.path.exists(path):
        b64 = base64.b64encode(open(path, "rb").read()).decode()
    return CSS.replace("__GPT_ICON_B64__", b64)


def _has_kanji(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def _to_hira(s):
    return "".join(
        chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch for ch in s
    )


def stem_of(front):
    """Highlight stem: drop 〜 and trailing okurigana (用いる→用, 潰れる→潰).
    Pure-kana words have no kanji to stop at: strip only ONE trailing kana
    (the inflection point), so てしまう→てしま, かねる→かね, ちゃう→ちゃ -
    stripping further would degenerate the needle to a single kana."""
    s = front.replace("〜", "").strip()
    if any(_has_kanji(ch) for ch in s):
        while len(s) > 1 and "ぁ" <= s[-1] <= "ん":
            s = s[:-1]
    elif len(s) >= 3 and "ぁ" <= s[-1] <= "ん":
        s = s[:-1]
    return s


def _ruby_html(surf, reading):
    """Ruby placed ONLY over kanji runs: kana runs of the surface act as
    anchors into the reading (okurigana alignment), so furigana never
    spills onto kana. Falls back to whole-token ruby if alignment fails."""
    if not reading or reading == _to_hira(surf) or not _has_kanji(surf):
        return html.escape(surf)
    runs = []
    for ch in surf:
        k = _has_kanji(ch)
        if runs and runs[-1][0] == k:
            runs[-1][1] += ch
        else:
            runs.append([k, ch])
    parts, pos = [], 0
    for i, (is_k, text) in enumerate(runs):
        if not is_k:
            if reading[pos:pos + len(text)] != text:
                return f"<ruby>{html.escape(surf)}<rt>{html.escape(reading)}</rt></ruby>"
            parts.append(html.escape(text))
            pos += len(text)
        else:
            nxt = runs[i + 1][1] if i + 1 < len(runs) else None
            if nxt is None:
                r = reading[pos:]
                if not r:
                    return f"<ruby>{html.escape(surf)}<rt>{html.escape(reading)}</rt></ruby>"
                parts.append(
                    f"<ruby>{html.escape(text)}<rt>{html.escape(r)}</rt></ruby>")
                pos = len(reading)
            else:
                j = reading.find(nxt, pos)
                if j <= pos:
                    return f"<ruby>{html.escape(surf)}<rt>{html.escape(reading)}</rt></ruby>"
                parts.append(
                    f"<ruby>{html.escape(text)}<rt>{html.escape(reading[pos:j])}</rt></ruby>")
                pos = j
    if pos != len(reading):
        return f"<ruby>{html.escape(surf)}<rt>{html.escape(reading)}</rt></ruby>"
    return "".join(parts)


def furigana_html(text, stem, stem_kana=None):
    """Tokenize with Janome; furigana only over kanji (see _ruby_html), the
    headword highlighted in orange, and tokens glued into bunsetsu-like
    units (particles/auxiliaries/punctuation stick to the preceding token)
    wrapped in nowrap spans - line breaks fall only between units, so a
    verb ending like た。 is never orphaned on its own line.

    Highlighting, in order: (1) a token whose surface starts with the
    headword stem; (2) the stem found in the concatenated unit surfaces
    (phrase headwords split across units); (3) each kanji run of the stem
    located in order; (4) the stem's kana reading found in the concatenated
    unit readings (examples that write the word in kana only)."""
    units = []  # {"html": str, "surf": str, "read": str}
    cur = None
    glue_next = False
    highlighted = False
    for tok in _TKZ.tokenize(text):
        surf = tok.surface
        reading = _to_hira(tok.reading) if tok.reading and tok.reading != "*" else None
        piece = _ruby_html(surf, reading) if reading else html.escape(surf)
        if (
            not highlighted
            and stem
            and _has_kanji(stem)
            and (surf == stem or surf.startswith(stem))
        ):
            piece = f'<span class="hl">{piece}</span>'
            highlighted = True
        pos = (tok.part_of_speech or "").split(",")
        pos1 = pos[0] if pos else ""
        pos2 = pos[1] if len(pos) > 1 else ""
        glue = (
            pos1 in ("助詞", "助動詞", "記号")
            or pos2 == "接尾"
            or surf in "。、！？"
        )
        tread = reading if reading else _to_hira(surf)
        if cur is not None and (glue or glue_next):
            cur["html"] += piece
            cur["surf"] += surf
            cur["read"] += tread
        elif cur is not None:
            units.append(cur)
            cur = {"html": piece, "surf": surf, "read": tread}
        else:
            cur = {"html": piece, "surf": surf, "read": tread}
        glue_next = pos1 == "接頭詞"
    if cur is not None:
        units.append(cur)

    def mark_span(strings, needle):
        """Highlight every unit intersecting the first occurrence of needle
        in the concatenation of the given per-unit strings."""
        if not needle or len(needle) < 2:
            return False
        idx = "".join(strings).find(needle)
        if idx < 0:
            return False
        end = idx + len(needle)
        pos = 0
        for u, s in zip(units, strings):
            nxt = pos + len(s)
            if nxt > idx and pos < end:
                u["html"] = f'<span class="hl">{u["html"]}</span>'
            pos = nxt
        return True

    if not highlighted and stem and units:
        surfs = [u["surf"] for u in units]
        reads = [u["read"] for u in units]
        done = mark_span(surfs, stem)
        if not done and stem.endswith("す") and len(stem) >= 4:
            # 〜する verbs: the example may use the bare noun (うっかりした)
            done = mark_span(surfs, stem[:-1])
        if not done:
            # combo headwords joined by ・or /: match each component,
            # minus a trailing をする/する
            def _cores(comp):
                out = [comp]
                for suf in ("をする", "する", "す", "を"):
                    if comp.endswith(suf) and len(comp) > len(suf) + 1:
                        out.append(comp[:-len(suf)])
                if out[-1].endswith("を"):
                    out.append(out[-1][:-1])
                return out
            for comp in re.split(r"[・/／]", stem):
                for cand in _cores(comp):
                    if len(cand) >= 2 and mark_span(surfs, cand):
                        done = True
                        break
            if stem_kana:
                for comp in re.split(r"[・/／]", stem_kana):
                    for cand in _cores(comp):
                        if len(cand) >= 2 and mark_span(reads, cand):
                            done = True
                            break
        if not done:
            # punctuation-insensitive pass (fronts like ありえない、マジか?!
            # vs fullwidth ？！ in examples)
            punct = r"[、,。．？！?!・…]"
            cs = [re.sub(punct, "", s) for s in surfs]
            cr = [re.sub(punct, "", s) for s in reads]
            done = mark_span(cs, re.sub(punct, "", stem))
            if not done and stem_kana:
                done = mark_span(cr, re.sub(punct, "", stem_kana))
        if not done:
            # kanji skeleton: consume the stem's kanji in order, marking
            # each unit that contains the next expected kanji (the example
            # may split the word with particles: 調子悪い -> 調子が/悪い)
            kanji = [ch for ch in stem if _has_kanji(ch)]
            ki = 0
            for u in units:
                if ki >= len(kanji):
                    break
                j = ki
                while j < len(kanji) and kanji[j] in u["surf"]:
                    j += 1
                if j > ki:
                    u["html"] = f'<span class="hl">{u["html"]}</span>'
                    done = True
                    ki = j
        if not done:
            # last resort: progressively shorter suffixes of the stem
            # (surface, then reading), at least 3 chars - sentence-pattern
            # headwords (これはガチです) appear in examples without their
            # leading part
            for needle_src, strings in ((stem, surfs), (stem_kana, reads)):
                if done or not needle_src or len(needle_src) <= 4:
                    continue
                for cut in range(1, len(needle_src) - 2):
                    if mark_span(strings, needle_src[cut:]):
                        done = True
                        break
    return "".join(f'<span class="u">{u["html"]}</span>' for u in units)


def ex_filename(card_id, idx):
    return f"{card_id}_ex.mp3" if idx == 0 else f"{card_id}_ex{idx + 1}.mp3"


CHIP_CLASS = {
    "口语": "c-oral", "近義": "c-syn", "関連": "c-fam", "书面": "c-wri",
    "慣用句": "c-idi", "敬语": "c-kei", "反対": "c-ant",
}


def usage_tags(card, incoming=None):
    """Scene/register tags derived only from curated data (category and the
    registers of this card's curated counterparts) - never invented
    frequency claims."""
    tags = []  # (text, extra css class)
    regs = {p.get("register") for p in card.get("pairs", [])}
    inc = (incoming or {}).get(card["id"], set())
    # Register badges derive from BOTH directions of the curated links:
    # an outgoing edge to a spoken counterpart (or an incoming edge that
    # labels this card 书面/敬语) means this card is the written style;
    # the mirror image means the spoken style. (Some pairs were curated
    # with the register fully stated on one side only.)
    if "口语" in regs or inc & {"书面", "敬语"}:
        tags.append(("書", "reg w"))
    if regs & {"书面", "敬语"} or "口语" in inc:
        tags.append(("話", "reg o"))
    if card["cat"] == "敬语":
        tags.append(("商务・正式", ""))
    elif card["cat"] == "IT":
        tags.append(("职场・IT", ""))
    seen, out = set(), []
    for t in tags:
        if t[0] not in seen:
            seen.add(t[0])
            out.append(t)
    return out[:3]


def render_senses(card, media_set, incoming=None):
    stem = stem_of(card["front"])
    stem_kana = stem_of(card["reading"])
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
            f'<span class="ex-text">{furigana_html(s["example"], stem, stem_kana)}</span>{audio}</div>'
            f'<div class="tr"><span class="tag">［訳］</span>{html.escape(s["example_zh"])}</div>'
            "</div>"
        )
    acc_span = ""
    if card.get("accent") is not None:
        acc_span = f'<span class="accdata" data-acc="{card["accent"]}"></span>'
    utags = usage_tags(card, incoming)
    head = ""
    if utags:
        head = ('<div class="utags">' + "".join(
            f'<span class="utag {cls}">{html.escape(t)}</span>'
            for t, cls in utags) + "</div>")
    return acc_span + head + "".join(blocks)


def render_collocations(card, by_id, media_set):
    parts = []
    cols = [x for x in card["collocations"] if x.strip() != card["front"].strip()]
    if cols:
        items = "".join(
            f'<li><a class="Dict WordLink" data-w="{html.escape(x, quote=True)}" '
            f'target="_blank" rel="noopener">{furigana_html(x, "")}</a>'
            f'<a class="GptL" data-w="{html.escape(x, quote=True)}" '
            f'target="_blank" rel="noopener"></a></li>'
            for x in cols)
        parts.append(
            f'<div class="sec"><div class="sec-h">［搭］</div>'
            f'<ul class="col-list">{items}</ul></div>'
        )
    # Build pair rows first, then group rows that share one identical note
    # (family / ladder explanations): the shared note is shown once as a
    # group header instead of being repeated on every row.
    rows = []
    for p in card.get("pairs", []):
        if "id" in p:
            other = by_id.get(p["id"])
            if other is None:
                continue
            d_front, d_reading, d_meaning = (
                other["front"], other["reading"], other["meaning"])
            d_scene = other.get("scene") or ""
            audio = ""
            fname = f"{p['id']}_front.mp3"
            if fname in media_set:
                audio = f'<span class="rel-audio">[sound:{fname}]</span>'
        else:
            d_front, d_reading, d_meaning = (
                p["front"], p["reading"], p["meaning"])
            d_scene = ""
            audio = ""
        rows.append({
            "reg": p["register"], "front": d_front, "reading": d_reading,
            "meaning": d_meaning, "note": p.get("note") or "",
            "scene": d_scene, "audio": audio,
        })

    def head_html(r, with_chip=True):
        chip = ""
        if with_chip:
            cls = CHIP_CLASS.get(r["reg"], "c-syn")
            chip = f'<span class="chip {cls}">{html.escape(r["reg"])}</span>'
        return (
            '<div class="rel-head">' + chip
            + f'<a class="Dict WordLink rel-front" data-w="{html.escape(r["front"], quote=True)}" target="_blank" rel="noopener">{_ruby_html(r["front"], _to_hira(r["reading"]))}</a>'
            f'<a class="GptL" data-w="{html.escape(r["front"], quote=True)}" target="_blank" rel="noopener"></a>{r["audio"]}</div>'
        )

    from collections import Counter, OrderedDict
    counts = Counter(r["note"] for r in rows if r["note"])
    singles = [r for r in rows if not r["note"] or counts[r["note"]] < 2]
    groups = OrderedDict()
    for r in rows:
        if r["note"] and counts[r["note"]] >= 2:
            groups.setdefault(r["note"], []).append(r)

    rels = []
    for r in singles:
        if r["note"]:
            sub = html.escape(r["meaning"]) + f'（{html.escape(r["note"])}）'
        elif r.get("scene"):
            sub = html.escape(r["scene"])
        else:
            sub = html.escape(r["meaning"])
        rels.append(
            '<div class="rel">' + head_html(r)
            + f'<div class="rel-sub">{sub}</div></div>'
        )
    for note, members in groups.items():
        reg = members[0]["reg"]
        cls = CHIP_CLASS.get(reg, "c-syn")
        rels.append(
            f'<div class="rel-gh"><span class="chip {cls}">{html.escape(reg)}</span>'
            f'<span class="gh-note">{html.escape(note)}</span></div>'
        )
        for r in members:
            # a scene already carries the gloss + scenario, so it
            # replaces the plain meaning instead of duplicating it
            gsub = html.escape(r["scene"]) if r.get("scene") else html.escape(r["meaning"])
            rels.append(
                '<div class="rel g">' + head_html(r, with_chip=False)
                + f'<div class="rel-sub">{gsub}</div></div>'
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
        css=_css_with_icon(media_dir),
    )

    deck = genanki.Deck(DECK_ID, "native-nihongo")
    by_id = {c["id"]: c for c in cards}
    incoming = {}
    for c in cards:
        for p in c.get("pairs", []):
            if "id" in p:
                incoming.setdefault(p["id"], set()).add(p["register"])
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
                render_senses(c, media_set, incoming),
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
