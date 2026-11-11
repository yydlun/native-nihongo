# native-nihongo

日本で生活してると、「この言い方、教科書で見たことないな」って場面、ほんとによくあるんですよね。役所でも、職場でも、テニスコートでも。

このデッキは、そういう実際に耳にしたり使ったりした表現を、その都度メモして集めた個人的な表現集です。中心は動詞の組み合わせと IT の現場用語、それと敬語あたり。試験対策ではないので、点数を取るための言葉はあんまり入ってません。その代わり、どれも明日そのまま使えるやつです。

## 下载（固定链接，永远指向最新版）

**https://github.com/yydlun/native-nihongo/releases/latest/download/native-nihongo.apkg**

在 Anki 手机端/桌面端打开这个链接下载后导入即可。每次作者新增词条并推送后，
GitHub Actions 会自动重新打包并发布新版本，这个链接永远指向最新的一包。

### 重复导入说明（重要）

新包里的每张卡带有固定 ID，**直接导入新包会更新已有卡片的内容，并保留你的复习记录**。
请不要先删除旧牌组再导入——那样复习进度会丢失。

## 卡片内容

每张卡包含：

- **表头词条 + 发音音频**（正面）
- **读音**（假名）
- **中文释义**
- **按义项拆分的例句**：多义词每个义项各配一句地道例句，并附中文翻译
- **常用搭配**：该词最常见的固定搭配短语
- **例句发音音频**

卡片按类别打了标签：`動詞搭配` / `IT` / `敬語` / `地道表达`，可以在 Anki 里按标签筛选学习。

## 更新机制

作者在 WhatsApp 里随手新增单词或句子 → 同步进 `data/cards.json`（并生成新音频放进 `media/`）
→ 推送到本仓库 → GitHub Actions 自动打包发布新 Release → 固定下载链接即为最新版。

## 数据格式

核心数据在 `data/cards.json`（JSON 数组，每张卡一个对象）：

| 字段 | 说明 |
|---|---|
| `id` | 卡片 ID（稳定不变，与 Anki 里的 guid `nn-<id>` 对应） |
| `front` | 日语词条/短语 |
| `reading` | 假名读音 |
| `meaning` | 中文释义全文 |
| `senses` | 按义项拆分：`[{gloss, example, example_zh}]`，例句带中文翻译 |
| `collocations` | 常用搭配短语数组 |
| `cat` | 类别：動詞搭配 / IT / 敬語 / 地道表达 |

音频在 `media/`：`<id>_front.mp3`（词条发音）、`<id>_ex.mp3`（第一条例句发音），
由 Edge TTS（ja-JP-NanamiNeural）生成。

打包脚本 `build.py`（genanki）读取 `data/cards.json` + `media/` 生成 `dist/native-nihongo.apkg`。

## License

MIT，见 [LICENSE](LICENSE)。
