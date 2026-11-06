# HTML 工程細節

所有輸出 HTML 的形式（A、B、D）都適用。

## 目錄

1. 離線單檔
2. Markdown 轉 HTML
3. 版面與互動元件
4. 測驗卡片
5. 驗證
6. 交付

## 1. 離線單檔

使用者在手冊類材料上要求過「離線可用、零外部依賴」。做法：

- **字體**：程式碼字體（JetBrains Mono 400/500）和標題字體（例如 Bricolage Grotesque）轉成 base64 WOFF2 內嵌；中文用系統字體堆疊，例如 `"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif`。不要內嵌中文字體，檔案會暴增
- **程式碼上色**：highlight.js 只打包用得到的語言（例如 js、ts、json、bash、html、css），用 esbuild 打成 IIFE，約 50 KB，直接內嵌
- **數學式**：要離線時，在建置階段用 Node 的 `katex.renderToString` 預先轉成 HTML，內嵌 KaTeX 的 CSS 與需要的字體；使用者不要求離線時可用 CDN，但回覆中要告知「需要連網」
- **圖**：SVG 內嵌，不用外部圖片
- 做完用驗證腳本確認外部請求為零（見第 5 節）

被發佈成網頁（artifact）時，外部腳本只允許少數主機，離線內嵌的做法在那裡也最穩。

## 2. Markdown 轉 HTML

用 Python 的 `markdown` 套件，啟用 `fenced_code`、`tables`、`attr_list`、`sane_lists`。章節用 `<a id="chN"></a>` 加標題，方便目錄與對照表跳轉。建置腳本分階段（例如 `build_site.py` 轉換，`build_site2.py` 注入測驗與內嵌資源），每階段可獨立重跑。

## 3. 版面與互動元件

美觀與配圖的原則見 `visual-design.md`，這裡只列實作上的細節。

- 內文 17px 以上、行高 1.8、段落最大寬度約 760px
- 左側 sticky 目錄，用 IntersectionObserver 標示目前位置；手機版收合成選單；頁面頂端閱讀進度條
- 配色柔和，單一強調色；定義與重點用有色邊框卡片
- 深色模式：用 CSS 變數，`prefers-color-scheme` 加手動切換，兩種主題文字與背景都要檢查對比
- 列印樣式：隱藏導覽，避免分頁切在程式碼或表格中間
- 程式碼區塊附一鍵複製按鈕
- 寬表格放在自己的 `overflow-x: auto` 容器，頁面本身不要橫向捲動
- 互動元件用 `<button>`，並考慮鍵盤操作與 `aria-live` 狀態提示

## 4. 測驗卡片

- 正文放 `<!--QUIZ:key-->` 標記，題目資料另存；轉換時以標記取代成卡片
- 單選、多選、是非三種題型
- 作答後立即回饋：對 `#17805A`、錯 `#A8332A`，不要只靠顏色，加上文字或圖示
- 多選題標出漏選的選項；每組顯示分數；可重試
- 每題附解析，說明為什麼其他選項錯

## 5. 驗證

```bash
python scripts/verify_html.py 輸出.html
```

檢查：外部資源請求（`<script src>`、`<link href>`、`<img src>`、CSS 的 `url()`、`@import`）、重複 id、壞掉的站內錨點、標籤是否成對、內嵌 JavaScript 語法（需要 Node）。另外會以警告提醒：文字很多卻沒有圖或表的 `<h2>` 小節、缺少替代文字的 `<img>` 與 `<svg>`（對應 `visual-design.md` 的圖文並茂要求）。要容許 CDN 時加 `--allow-external`。

KaTeX 式子逐一驗證：

```bash
npm install katex
node -e "
const katex=require('katex');
const list=JSON.parse(require('fs').readFileSync('exprs.json','utf8'));
let bad=0;
for(const e of list){try{katex.renderToString(e.tex,{displayMode:e.d,throwOnError:true});}catch(err){bad++;console.log('FAIL:',e.tex.slice(0,90),err.message.slice(0,100));}}
console.log('total',list.length,'failed',bad);"
```

`exprs.json` 由 Python 從 HTML 抓出所有數學式（例如 class 為 `katex-inl`、`katex-blk` 的元素）產生。

視覺檢查：用 Playwright 截桌機與手機（約 390px 寬）兩種寬度，看目錄、表格、公式有沒有跑版。

## 6. 交付

- 檔案放到輸出目錄（`/mnt/user-data/outputs/`）
- 依環境規則：能發佈成網頁就發佈；使用者要檔案時用 present_files
- 若發佈成網頁，瀏覽器儲存（localStorage）要包 try/catch，取不到時頁面仍要正常運作
