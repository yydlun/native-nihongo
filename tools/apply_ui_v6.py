#!/usr/bin/env python3
"""UI v6 data pass (user's 2026-11-14 round-2 brief, sections 4/6/7):
1. Shorten shared family notes (noun idiom families -> the user's compact
   template; suffix families -> one short Chinese line; ladder note trimmed).
2. Remove v4 false positives from the 気 family （電気をつける etc. matched
   the kanji 気 but are not 気 idioms) - both directions.
3. Add a one-line usage `scene` to 手/気/目 idiom cards; the renderer shows
   it on related-word rows (brief section 6).
4. 引っかかる (178) / 引っ掛かる (2206): add the missing sense 心里在意、
   觉得不对劲 with an example; link the two spellings to each other.
Also syncs deck.csv backs for 178/2206. Idempotent.
"""
import csv
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDY = os.path.expanduser("~/workspace/japanese-study")
PATH = os.path.join(REPO, "data", "cards.json")
cards = json.load(open(PATH, encoding="utf-8"))
by_front = {c["front"]: c for c in cards}
by_id = {c["id"]: c for c in cards}

# --- 1. shorten shared notes ------------------------------------------------
NOUN_SHORT = "「{n}」を使った慣用句。意味は動詞との組み合わせで決まる。"
SUF_SHORT = {
    "込む": "複合動詞『〜込む』：中へ深く入る・すっかり〜になる。",
    "出す": "複合動詞『〜出す』：外へ出す・突然〜し始める。",
    "切る": "複合動詞『〜切る』：最後まで・完全に〜する。",
    "上げる": "複合動詞『〜上げる』：上へ・完成させる。",
    "落とす": "複合動詞『〜落とす』：下へ落とす・見聞き漏らす。",
    "抜く": "複合動詞『〜抜く』：突き抜ける・最後まで〜し通す。",
    "取る": "複合動詞『〜取る』：手に取る・受け取る・取り除く。",
    "合う": "複合動詞『〜合う』：互いに〜し合う。",
    "付く": "複合動詞『〜付く』：近付く・くっ付く。",
    "入れる": "複合動詞『〜入れる』：中へ入れる・受け入れる。",
    "寄せる": "複合動詞『〜寄せる』：近くへ集める・近付ける。",
}
LAD_OLD = ("同一请求的礼貌阶梯：ご〜ください（直接）＜ご〜いただけますと幸いです"
           "（委婉）＜ご〜賜りますようお願い申し上げます（最郑重，多用于邮件）")
LAD_NEW = "请求的礼貌阶梯：ください（直接）＜いただけますと幸いです（委婉）＜賜りますよう（最郑重・邮件）"
D_OLD = ("同じ依頼の言い換え：〜いただけますでしょうか＝確認・念押し版、"
         "〜いただけますと幸いです＝委婉版、〜ください＝直接版（礼貌阶梯）")
D_NEW = "同一请求的阶梯变体：〜いただけますでしょうか＝确认版（礼貌阶梯）"

n_short = 0
for c in cards:
    for p in c.get("pairs", []):
        note = p.get("note") or ""
        new = None
        if note.startswith("同じ『") and "』の慣用句家族" in note:
            noun = note[3]
            new = NOUN_SHORT.format(n=noun)
        elif note.startswith("複合動詞『〜"):
            for suf, short in SUF_SHORT.items():
                if note.startswith(f"複合動詞『〜{suf}』"):
                    new = short
                    break
        elif note == LAD_OLD:
            new = LAD_NEW
        elif note == D_OLD:
            new = D_NEW
        if new and new != note:
            p["note"] = new
            n_short += 1
print("notes shortened:", n_short)

# --- 2. remove false 気-family members --------------------------------------
BAD = ["電気をつける", "換気をする", "眠気が来る", "肌も元気になっている"]
ki_note_old_start = "同じ『気』の慣用句家族"
removed = 0
for f in BAD:
    c = by_front.get(f)
    if not c:
        continue
    kept = []
    for p in c.get("pairs", []):
        if (p.get("note") or "").startswith(ki_note_old_start) or \
           (p.get("note") or "") == NOUN_SHORT.format(n="気"):
            removed += 1
        else:
            kept.append(p)
    c["pairs"] = kept
bad_ids = {by_front[f]["id"] for f in BAD if f in by_front}
for c in cards:
    if not c.get("pairs"):
        continue
    kept = []
    for p in c["pairs"]:
        note = p.get("note") or ""
        if "id" in p and p["id"] in bad_ids and (
                note.startswith(ki_note_old_start)
                or note == NOUN_SHORT.format(n="気")):
            removed += 1
        else:
            kept.append(p)
    c["pairs"] = kept
print("false ki-family edges removed:", removed)

# --- 3. scenes ----------------------------------------------------------------
SCENES = {
    # 手
    "手を出す": "插手、动手（多指不该管的事）", "手が空く": "手头事结束、腾出空",
    "手に入れる": "弄到手（想要的东西）", "手に乗る": "上当、中圈套",
    "手が回らない": "忙不过来、顾不上（工作太多）", "手が離せない": "正在忙、脱不开身",
    "手を焼く": "棘手、拿某人没办法", "手を貸す": "出手帮忙",
    "手をつける": "着手开始做", "手を抜く": "偷工减料、敷衍",
    "手を組む": "联手合作", "手を打つ": "采取对策",
    "手を広げる": "扩大范围（铺得太开）", "手を尽くす": "想尽办法",
    "手が足りない": "人手不足（职场・活动现场）", "手を差し伸べる": "伸出援手（帮困境中的人）",
    "手に余る": "难以驾驭、管不了", "手を引く": "退出、撒手不管",
    "手を切る": "断绝关系", "手を加える": "加工修改（文章・作品）",
    "手を休める": "停下手头的活歇一下", "手を止める": "停下正在做的事",
    "手を拱く": "袖手旁观", "手を挙げる": "举手（发言・赞成）",
    "手を合わせる": "合掌（祈祷・感谢）", "手を振る": "挥手告别・招呼",
    "手に付かない": "无心做事、心不在焉", "手に取る": "拿在手里看（商品・书）",
    "手にする": "获得、拿到（机会・成果・物品）", "手を差し出す": "伸出手（握手・索取）",
    "手を握る": "握手；握紧（紧张・决心）", "手を離す": "松手、放开不管",
    "手をこまねく": "袖手旁观", "手を汚す": "亲手干（多指脏活・坏事）",
    "手を染める": "染指（多指坏事）", "手を緩める": "手下留情、放松（攻击・要求）",
    "手を入れる": "整修、翻改（房子・庭院）", "手を伸ばす": "伸手去够",
    "手を叩く": "拍手叫好；恍然大悟",
    # 気
    "気を使う": "照顾他人感受、费心周到", "嫌気が差す": "厌烦、受够了",
    "気が進まない": "提不起劲、不想做", "気が回る": "心思细、想得周到",
    "気の置けない": "无需见外（关系亲近）", "空気を読む": "会看气氛、察言观色",
    "気にする": "在意、介意（眼光・小事）", "気がする": "感觉、好像（直觉）",
    "気に障る": "听着刺耳、心里不舒服", "気が利く": "机灵、会来事",
    "空気が読める": "能看气氛（褒义评价）", "気が重い": "心情沉重",
    "呆気に取られる": "惊得目瞪口呆", "気が向く": "心血来潮、想做了",
    "気が済む": "心里舒坦了、出了口气", "気を付ける": "小心、注意（提醒常用）",
    "気を引き締める": "绷紧神经、打起精神", "気が散る": "分心、静不下心",
    "気にかける": "记挂（下属・晚辈）", "気にかかる": "挂在心上、放不下",
    "気を揉む": "干着急、瞎操心", "気を取り直す": "振作起来",
    "気が短い": "性子急、没耐心", "気が長い": "有耐心、沉得住气",
    "気がある": "有好感、有意（恋爱・兴趣）", "気になる": "在意、好奇（自然而然）",
    "気を配る": "关照周到（职场高评价）", "気を遣う": "费心照顾人（用多了会累）",
    "気に食わない": "看不顺眼、不合心意", "気に入る": "中意、合心意（东西・人）",
    "気を回す": "多心、瞎猜疑", "気を引く": "想引起（某人）注意",
    "気を散らす": "分散注意力、解闷", "気を紛らす": "排遣（悲伤・无聊）",
    "気を取られる": "被吸引走神", "気を落とす": "沮丧、泄气",
    "気を強く持つ": "坚强起来（鼓励人时）", "気を抜く": "松懈、放松警惕",
    "気が滅入る": "情绪低落、郁闷",
    # 目
    "目を通す": "过目、浏览（文件・资料）", "金に目が眩む": "见钱眼开",
    "目を細める": "眯眼笑（欣慰・喜爱）", "目を吊り上げる": "怒目而视",
    "出たら目を言うな": "别瞎说、别胡扯", "目を閉じて": "闭眼（休息・回忆）",
    "目が合う": "目光对上、对视", "目を配る": "留意照看（四周・下属）",
    "目を光らせる": "盯紧、严密监视", "目が離せない": "离不开眼（孩子・关键场面）",
    "目をつぶる": "睁一只眼闭一只眼", "目を覚ます": "睡醒、清醒过来",
    "目に浮かぶ": "浮现在眼前（回忆）", "目が回る": "忙得团团转；头晕",
    "目をつける": "盯上、看中（目标）", "目を見張る": "瞪大眼（惊讶・赞叹）",
    "目を凝らす": "凝神细看", "目を逸らす": "移开视线（心虚・尴尬）",
    "目を背ける": "别开脸、不愿面对", "目に留まる": "映入眼帘、注意到",
    "目を疑う": "怀疑自己的眼睛（难以置信）", "目を向ける": "看向、关注",
    "目をそらす": "移开目光", "目を丸くする": "瞪圆眼睛（吃惊）",
    "目を輝かせる": "眼睛发亮（期待・喜悦）", "目を伏せる": "垂下眼、低头不语",
    "目を引く": "抢眼、引人注目", "目を奪われる": "被吸引住目光",
    "目を潤ませる": "眼眶湿润、含泪", "夜中に目が覚める": "半夜醒来",
}
n_scene = 0
for f, s in SCENES.items():
    c = by_front.get(f)
    if c and c.get("scene") != s:
        c["scene"] = s
        n_scene += 1
print("scenes set:", n_scene)

# --- 4. 引っかかる senses + spelling link --------------------------------------
def add_link(card, entry):
    pairs = card.setdefault("pairs", [])
    for e in pairs:
        if "id" in entry and e.get("id") == entry["id"]:
            return False
        if "id" not in entry and "id" not in e and e.get("front") == entry["front"]:
            return False
    pairs.append(entry)
    return True


c178 = by_front["引っかかる"]
if not any(s["gloss"].startswith("心里在意") for s in c178["senses"]):
    c178["senses"].append({
        "gloss": "心里在意、觉得不对劲",
        "example": "何か引っかかるところがある。",
        "example_zh": "总觉得有什么地方不对劲。"})
    c178["meaning"] = "上当受骗；被勾住；心里在意"
c2206 = by_front["引っ掛かる"]
if not any(s["gloss"].startswith("心里在意") for s in c2206["senses"]):
    c2206["senses"].append({
        "gloss": "心里在意、觉得不对劲",
        "example": "その説明、どこか引っかかるところがある。",
        "example_zh": "那个说明，总觉得哪里不对劲。"})
    c2206["meaning"] = "被挂住；卡住；受骗上当；心里在意"
note = "表記ゆれ：引っかかる／引っ掛かる是同一个词的两种写法，意思用法相同"
add_link(c178, {"id": 2206, "register": "近義", "note": note})
add_link(c2206, {"id": 178, "register": "近義", "note": note})

json.dump(cards, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# deck.csv backs for 178 / 2206
deck_path = os.path.join(STUDY, "deck.csv")
rows = list(csv.reader(open(deck_path, encoding="utf-8")))
for r in rows:
    if r and r[0] == "178":
        r[2] = "ひっかかる｜上当受骗；被勾住；心里在意｜例：うまい話に引っかかって損をした。"
    if r and r[0] == "2206":
        r[2] = "ひっかかる｜被挂住；卡住；受骗上当；心里在意｜例：喉に異物が引っかかった。"
with open(deck_path, "w", encoding="utf-8", newline="") as f:
    csv.writer(f, lineterminator="\n").writerows(rows)
print("deck.csv synced for 178/2206")
