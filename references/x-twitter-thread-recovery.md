# X.com / X 貼文完整內容 Recovery（2026-06-07 驗證，2026-06-21 補 Substack 路徑）

通用 JS-shell / truncated 處理在 `web-extraction-truncated.md`。這份專講 X 貼文 URL（`x.com/<user>/status/<id>` 或舊 `twitter.com/...`）特有的升級路徑。

## 升級鏈（按順序試）

| 工具 | X 貼文常見結果 | 是否要繼續 |
|------|---------------|-----------|
| `collect.py url` | 抓回 JS shell 字串（"JavaScript is not available"） | 進 `browser_navigate` |
| `web_extract`（同 URL 重抓）| 部分成功 + 結尾 `[... summary truncated ...]` | 進 `browser_navigate` |
| `browser_navigate` + `browser_snapshot` | 看見 login wall 跟側欄，**看不見貼文主體**（無登入不渲染 article 元素） | 進 `browser_console` |
| `browser_console` 跑 `document.querySelector('article')?.innerText \|\| document.body.innerText.slice(0, 5000)` | 抓到完整 thread 文字（從 timeline DOM 抓的，不是 post-detail article） | 收尾 |
| **Bonus**：掃 `x.com/i/article/XXXX` 連結 → `web_extract` 該 blog URL | 拿到 canonical 完整 markdown，比 X DOM 乾淨 | 優先此路徑 |
| **Bonus 2**：newsletter writer → t.co 短網址 → `web_extract` Substack canonical | 跳過 X DOM 整個 chain，直接拿乾淨 Substack HTML | 預設路徑（見下面「Newsletter writer (Substack) 路徑」段） |

## 為什麼 `article` 抓不到，`body.innerText` 抓得到

未登入 X 時，貼文主體文字**不在 post-detail 的 `<article>` 元素裡**（那是被登入牆擋住的 SPA 區塊）。但 timeline 區塊會把同則貼文當作 feed item 渲染，文字落在 generic `<div>` 裡。所以 `body.innerText` 一次掃整頁，thread 主體就會被抓出來。`.slice(0, 5000)` 是保險絲，實際多數 thread < 5000 chars。

## Cross-post 偵測（加速捷徑）

掃貼文內文（含 timeline 抓回的版本）找以下任一訊號：
- 連結文字 `x.com/i/article/...`（Anthropic / OpenAI 員工常 cross-post 到官方 blog）
- 字串 `"This post is also available on the [Company] Blog"`
- 字串 `"Read the full post on our blog"`
- **Newsletter writer 的 t.co 短網址**（見下「Newsletter writer (Substack) 路徑」段）

找到就把 `x.com/i/article/XXXX` 對應的 blog URL（常是 `https://www.<company>.com/news/<slug>`）丟給 `web_extract`，回傳的 markdown 通常**比 X DOM 乾淨**（有正確段落、沒 engagement metadata 雜訊）。可直接取代 X recovery 結果。

### Newsletter writer (Substack) 路徑（2026-06-21 驗證）

**訊號：** X 貼文作者是獨立 newsletter 寫手（Dan Koe、Naval、Stratechery 等），X post 內文只有一個 t.co 短網址、沒有 `x.com/i/article/...` 連結，X bio 寫 "Substack" / "newsletter" / "subscribe"。

**問題：** 對這種作者，`x.com/i/article/<id>` 路徑**根本不存在**或 `web_extract` 會回 `"Website Not Supported"`。X 把他們的 long-form post 視為外部 Substack URL，不走 X native article 引擎。盲目試 `/i/article/` 浪費一次 quota。

**解法：**
1. 從 X 頁面 snapshot 抓 t.co 短網址（例：`https://t.co/7l7Jef99QZ`）
2. `browser_navigate` 開那個 t.co URL → 撞 X login wall，但 `url` 欄位會有 redirect URL（含 `/i/article/<id>` query param — 例：`redirect_after_login=%2Fi%2Farticle%2F2010742786430021632`）。這個 article ID 是線索但不是終點
3. `web_search "<author name> <article title> site:substack.com OR site:letters.*"` 找 canonical Substack URL
4. Substack 命名的典型 pattern：
   - `https://letters.<author-domain>.com/p/<slug>`（例：Dan Koe 的 `letters.thedankoe.com`）
   - `https://<author-domain>.com/p/<slug>`（例：Naval 的 `nav.al`）
   - X bio 通常有 newsletter 連結，`web_search "<handle> newsletter"` 可直接定位
5. `web_extract` 該 Substack URL → 拿到 canonical markdown（完整段落、正確 H1/H2、沒 X engagement 雜訊），通常 30–50KB 一篇
6. **不需要走 X DOM recovery chain**。`web_extract` Substack 是終點，乾淨度勝過 X timeline 抓回 + 任何拼接

**為什麼這條比 `/i/article/` 乾淨：** Substack 是 full HTML page（gatsby/static export），不是 X SPA。`web_extract` 能解析完整 DOM、保留 headings、沒 login wall 雜訊。**判斷：作者 bio 寫 "Substack"/"newsletter"/"subscribe" 的，預設走 Substack 路徑，跳過 `/i/article/` 嘗試。**

**保留：**
- X 帖的 engagement metadata（views/likes/reposts/bookmarks）寫進 KB note 內文頂部「Source:」行（用 metadata block 格式，見下「保留進 KB frontmatter 的 engagement metadata」段）
- X 帖 URL 作為 cross-post reference 寫進 frontmatter `cross_post:` 欄位（不取代 `source:`，是補上）

## 保留進 KB frontmatter 的 engagement metadata

X DOM 抓回的結尾常有這段：
```
**Post metadata:** 282.2萬 views · 241 replies · 1,525 retweets · 9,773 likes · 2.2萬 bookmarks · Posted 2026-06-03 04:26
```

把這段原封不動放進 KB note 內文頂部（緊接 H1 後的 "Source:" 區塊），不是 frontmatter — frontmatter 是結構，metadata 是內容。理由：views / likes 數字會過期，5 年後沒意義，但**擺在內文能標示「這份分析是基於 X 公開數據，數字可能已變」**，不污染未來 grep / 標籤搜尋。

**Substack 路徑的 metadata 來源例外：** Substack page 沒有 X engagement 數字。要拿 engagement 必須回頭從 X 頁面 snapshot 抓（"2億 views · 49,081 reposts · 317,681 likes · 828,603 bookmarks · Posted 2026-01-12 16:31" 這段出現在 X post 文章的 link card 下方）。兩邊合併：Substack 給正文、X 給 metadata。

## KB note 命名（不要 rename）

`collect.py url` 預設存成 `{date}-web-note.md`。即使內容是完整 Anthropic blog 文章，**保留 `web-note.md` 檔名**，不要改成 `2026-06-07-Dynamic-Workflows-Claude-Code.md`。理由：
- 同源回溯：`web-note.md` 是 collector 自動命名，未來 grep 同來源可一次抓
- 標題在檔案內 H1 已經修了，外部可讀性不打折
- Rename 等於「多寫一個 note 給同樣來源」，會污染 KB

**例外：** Substack 路徑的 KB note 可以用具意義的標題（例：`2026-06-21-Dan Koe — How to Fix Your Entire Life in 1 Day.md`），因為內容是真實 long-form 文章（不是 X 殼），標題放在檔名比放在 H1 更利於 Obsidian 搜尋。

## 不需要動的東西

- `collect.py` 腳本本身 — JS-shell 是 X 端行為，不是 collector bug
- `web-extraction-truncated.md` — 那份是 generic 多來源，這份是 X-specific，**互補不取代**

## 驗證 checklist（recovery 完成後跑一次）

- [ ] 抓回內容 > 1000 chars（不是 JS shell）
- [ ] 看到作者 handle（`@xxx`）跟時間戳
- [ ] 看到 `## ` 或 `# ` Markdown headers（X DOM 抓的不一定有，blog / Substack 來源一定有）
- [ ] 結尾看到 engagement metadata 或 "Cross-posted on..." 字串
- [ ] KB note frontmatter `author` 從 "Unknown" 改成實際作者
- [ ] H1 title 從 "web-note" 改成原始標題
- [ ] tags 從預設 `[web]` 擴成實際領域（`[web, x-thread, substack, self-improvement, ...]`）
- [ ] （Substack 路徑）frontmatter `source:` 指向 Substack canonical URL；X URL 寫進 `cross_post:` 欄位
- [ ] （Substack 路徑）檔名用具意義標題（不是 `web-note.md`）
- [ ] （Substack 路徑）X engagement metadata 從 X page snapshot 補進去（因為 Substack page 沒有）
