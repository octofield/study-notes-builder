# study-notes-builder

一個 Claude skill：把課程講義、PDF、影片逐字稿或學習主題，整理成完整、自足、美觀、圖文並茂的繁體中文學習材料。

## 支援的形式

| 形式 | 說明 |
|---|---|
| 完整教學手冊 | 系統化的章節、離線單檔 HTML、互動測驗 |
| 講義解說網頁 | 依講義 PDF 製作，含公式推導、SVG 圖、逐步動畫 |
| 考前大抄 | 多欄、分章配色、自動縮放字級的 PDF |
| 影片轉教學文件 | 逐字稿分章流程與 NotebookLM 提示詞 |

## 結構

```
study-notes-builder/
├── SKILL.md                 # 入口：形式選擇、共通原則、流程
├── references/              # 各形式與視覺設計的詳細指引
└── scripts/verify_html.py   # HTML 驗證（外部請求、錨點、JS 語法、缺圖提醒）
```

## 安裝

**claude.ai 與 Claude Desktop**：把 `study-notes-builder` 資料夾壓縮成 zip（zip 的根目錄必須是這個資料夾，資料夾名稱要與 SKILL.md 的 `name` 相同），到 Settings → Capabilities → Skills 上傳，並確認已開啟 Code execution and file creation。

```bash
zip -r study-notes-builder.zip study-notes-builder
```

**Claude Code**：複製到個人 skills 目錄（所有專案可用），或放進專案的 `.claude/skills/`。

```bash
cp -r study-notes-builder ~/.claude/skills/
```

各平台的 skill 是分開安裝的，不會互相同步。

## 使用

直接描述需求即可，例如「幫我把這份講義做成解說網頁」「幫我做考前大抄」。如果 Claude 沒有自動使用，明確說「使用 study-notes-builder」。

## 驗證腳本

```bash
python study-notes-builder/scripts/verify_html.py 輸出.html
```
