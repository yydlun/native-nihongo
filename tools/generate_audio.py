#!/usr/bin/env python3
"""用 Edge TTS 为 data/cards.json 的每张卡生成发音音频（断点续跑）。

- media/<id>_front.mp3：读 front 原文
- media/<id>_ex.mp3：读 senses[0].example（第一个义项的例句）
已存在的非空文件会跳过，所以本地和 GitHub Actions 里都可以反复运行，
只补缺失的。音色 ja-JP-NanamiNeural。
"""
import asyncio, json, os, sys

import edge_tts

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(BASE, "media")
VOICE = "ja-JP-NanamiNeural"
SEM = asyncio.Semaphore(6)


def load_items():
    cards = json.load(open(os.path.join(BASE, "data", "cards.json"), encoding="utf-8"))
    items = []
    for c in cards:
        items.append((c["id"], c["front"], f"{c['id']}_front.mp3"))
        items.append((c["id"], c["senses"][0]["example"], f"{c['id']}_ex.mp3"))
    return items


async def synth(text, path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)


async def worker(item, results):
    cid, text, fname = item
    path = os.path.join(MEDIA, fname)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        results["skip"] += 1
        return
    async with SEM:
        last = None
        for attempt in range(3):
            try:
                await asyncio.wait_for(synth(text, path), timeout=60)
                if os.path.getsize(path) > 0:
                    results["ok"] += 1
                    return
                last = "empty file"
            except Exception as e:  # noqa: BLE001
                last = f"{type(e).__name__}: {e}"
            await asyncio.sleep(2 * (attempt + 1))
        results["fail"].append({"id": cid, "file": fname, "error": last})


async def main():
    os.makedirs(MEDIA, exist_ok=True)
    items = load_items()
    results = {"ok": 0, "skip": 0, "fail": []}
    print(f"total={len(items)}", flush=True)
    tasks = [asyncio.create_task(worker(it, results)) for it in items]
    done = 0
    for t in asyncio.as_completed(tasks):
        await t
        done += 1
        if done % 500 == 0:
            print(f"progress {done}/{len(items)} ok={results['ok']} skip={results['skip']} fail={len(results['fail'])}", flush=True)
    print(f"DONE ok={results['ok']} skip={results['skip']} fail={len(results['fail'])}", flush=True)
    for f in results["fail"][:20]:
        print("FAIL", f, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
