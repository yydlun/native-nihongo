#!/usr/bin/env python3
"""Build dist/native-nihongo.apkg from data/cards.json + media/.

- Fixed model/deck IDs and per-note guid "nn-<id>": re-importing a newer
  package into Anki updates existing cards in place and keeps review history.
- Fields: Front / Reading / Meaning / SenseExamples / Collocations /
  FrontAudio / ExampleAudio. Category is stored as a tag.
- Register pairs (cards.json "pairs": [{id, register}]): the counterpart's
  front/reading/meaning is rendered into the Collocations field as a
  "🔗 <register>：..." line, and both notes get a shared tag "pair_<min id>"
  so the pair can be pulled up together in Anki's browser. The model itself
  is unchanged, so re-imports stay in place.
"""
import html
import json
import os

import genanki

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = 1738092451
DECK_ID = 2048691735
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"


def render_senses(senses):
    blocks = []
    for i, s in enumerate(senses):
        num = CIRCLED[i] if i < len(CIRCLED) else f"{i + 1}."
        blocks.append(
            f"{num} {html.escape(s['gloss'])}<br>"
            f"{html.escape(s['example'])}<br>"
            f"{html.escape(s['example_zh'])}"
        )
    return "<br><br>".join(blocks)


def main():
    cards = json.load(open(os.path.join(BASE, "data", "cards.json"), encoding="utf-8"))
    media_dir = os.path.join(BASE, "media")

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
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div class="front">{{Front}}</div>{{FrontAudio}}',
                "afmt": (
                    "{{FrontSide}}<hr id=\"answer\">"
                    '<div class="reading">{{Reading}}</div>'
                    '<div class="meaning">{{Meaning}}</div>'
                    '<div class="senses">{{SenseExamples}}</div>'
                    '<div class="collocations">{{Collocations}}</div>'
                    "{{ExampleAudio}}"
                ),
            }
        ],
        css=(
            ".card { font-family: sans-serif; font-size: 20px; text-align: left;"
            " color: #222; background: #fff; line-height: 1.6; }"
            ".front { font-size: 30px; text-align: center; margin: 12px 0; }"
            ".reading { color: #555; }"
            ".meaning { font-weight: bold; margin: 6px 0; }"
            ".senses { margin: 10px 0; }"
            ".collocations { color: #33529e; margin-top: 8px; }"
        ),
    )

    deck = genanki.Deck(DECK_ID, "native-nihongo")
    by_id = {c["id"]: c for c in cards}
    media_files = []
    for c in cards:
        front_mp3 = f"{c['id']}_front.mp3"
        ex_mp3 = f"{c['id']}_ex.mp3"
        front_audio = ""
        ex_audio = ""
        p = os.path.join(media_dir, front_mp3)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            front_audio = f"[sound:{front_mp3}]"
            media_files.append(p)
        p = os.path.join(media_dir, ex_mp3)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            ex_audio = f"[sound:{ex_mp3}]"
            media_files.append(p)
        pair_lines = []
        pair_tags = []
        for p in c.get("pairs", []):
            other = by_id.get(p["id"])
            if other is None:
                continue
            pair_lines.append(
                '<span style="color:#a05a00">🔗 '
                + html.escape(f"{p['register']}：{other['front']}（{other['reading']}）｜{other['meaning']}")
                + "</span>"
            )
            pair_tags.append(f"pair_{min(c['id'], p['id'])}")
        collocations_field = "<br>".join(
            [html.escape(x) for x in c["collocations"]] + pair_lines
        )
        note = genanki.Note(
            model=model,
            fields=[
                c["front"],
                c["reading"],
                c["meaning"],
                render_senses(c["senses"]),
                collocations_field,
                front_audio,
                ex_audio,
            ],
            tags=[c["cat"]] + sorted(set(pair_tags)),
            guid=f"nn-{c['id']}",
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = media_files
    out = os.path.join(BASE, "dist", "native-nihongo.apkg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    package.write_to_file(out)
    print(f"notes={len(cards)} media={len(media_files)} -> {out}")


if __name__ == "__main__":
    main()
