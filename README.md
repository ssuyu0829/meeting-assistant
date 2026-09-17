# 開會小助手 (Meeting Assistant)

> 日式極簡風格的線上會議排程與紀錄工具

解決的問題：社團與小組要喬開會時間時，訊息在群組裡來回洗版，最後還是沒人記得結論。
這個站把「填可用時段 → 熱力圖看交集 → 組長拍板並自動寄信 → 記出席與會議紀錄 → 產生總結」
收成一條線，每一步都留在同一個會議底下。

<!-- TODO：放一張熱力圖的截圖或 GIF，這裡最有畫面 -->

---

## 一、網站網址

**正式網址：** https://meeting-assistant-k765.onrender.com

> **注意事項**
> - 使用 Render 免費方案，閒置 15 分鐘後會自動休眠
> - 第一次開啟需等待約 50 秒喚醒，之後瀏覽速度正常
> - 資料儲存在 Supabase，休眠不影響資料安全

---

## 二、網站功能

### 1. 帳號系統
- 使用者註冊 / 登入（Email + 密碼）
- JWT Token 身份驗證，登入狀態保持 7 天

### 2. 群組管理
- 建立群組（擔任 Leader）
- 透過邀請碼加入群組
- 查看群組成員清單
- 離開群組

### 3. 資料夾與會議管理
- 在群組內建立資料夾，分類整理會議
- 建立會議，設定多個候選日期
- 將會議標記為「已結束」

### 4. 時間填寫（可用時段調查）
- 每位成員填寫自己在各候選日期的可用時段（早上 7 點～晚上 11 點，共 16 個時段）
- 即時查看哪個時段最多人有空

### 5. 熱力圖（Heatmap）
- 以視覺化方式呈現各日期 × 時段的出席人數
- 幫助快速找出最佳會議時間

### 6. 確認開會時間 + 發送 Email 通知
- Leader 決定最終開會時間後，自動寄送通知 Email 給所有群組成員

### 7. 出席紀錄
- 記錄每位成員出席狀態：準時 / 遲到 / 缺席
- 記錄任務完成狀態：完成 / 未完成

### 8. 會議紀錄
- 填寫會議筆記
- 新增補充備注

### 9. 會議總結
- 統計出席率與任務完成率
- 以圓餅圖（Chart.js）視覺化呈現結果

---

## 三、使用的工具與技術

### 後端
| 套件 | 用途 |
|------|------|
| Python 3.11.9 | 主要程式語言 |
| FastAPI | 建立 REST API 伺服器 |
| SQLAlchemy | ORM 資料庫操作 |
| Alembic | 資料庫版本控制（migration）|
| python-jose | JWT Token 產生與驗證 |
| passlib + bcrypt | 密碼加密（bcrypt + SHA-256 預雜湊）|
| python-multipart | 表單資料解析 |
| python-dotenv | 讀取環境變數（.env 檔）|
| Resend | 發送通知 Email 的 API 服務 |

### 資料庫
- **本地開發：** SQLite
- **正式部署：** PostgreSQL（由 Supabase 託管）
- psycopg2-binary — Python 連接 PostgreSQL 的驅動程式
- Supabase Connection Pooler（Session Pooler，port 5432）— 解決 Render 免費方案無法直連 Supabase 的網路問題

### 前端
- 純 HTML / CSS / JavaScript（無框架）
- Chart.js — 繪製圓餅圖（出席率、任務完成率）
- Fetch API — 與後端 API 溝通
- **設計風格：** 無印良品 / 日式極簡，莫蘭迪色系
  - 主色：`#F5F0EB` 米白、`#B8A99A` 暖棕、`#9BAF9F` 鼠尾草綠、`#A8B4C0` 霧藍

### 部署與版本控制
- **GitHub** — 原始碼管理：https://github.com/ssuyu0829/meeting-assistant
- **Render** — 雲端部署平台（免費方案），自動偵測 GitHub 推送並重新部署
- **Claude Code** — AI 輔助開發，負責程式撰寫與除錯

---

## 四、GitHub 原始碼結構與各檔案說明

```
meeting-assistant/
│
├── render.yaml                 部署設定檔，告訴 Render 如何建置與啟動服務
├── .python-version             指定 Python 版本為 3.11.9（避免 Render 使用不相容的新版本）
├── .gitignore                  排除不上傳的檔案（.env、資料庫、虛擬環境等）
│
├── backend/
│   ├── requirements.txt        列出所有 Python 套件及版本，Render 安裝時使用
│   ├── main.py                 程式進入點：啟動 FastAPI、載入所有路由、提供前端靜態檔案
│   ├── database.py             資料庫連線設定：建立 SQLAlchemy 引擎與 Session
│   ├── models.py               定義所有資料庫表格（User、Group、Meeting 等 9 個資料表）
│   ├── auth.py                 身份驗證邏輯：密碼雜湊、JWT Token 產生與驗證
│   │
│   └── routers/                API 路由（依功能分檔）
│       ├── auth.py             註冊、登入 API（/api/register、/api/login）
│       ├── groups.py           群組 API（建立、加入、查詢、離開群組）
│       ├── meetings.py         會議 API（建立資料夾、建立會議、查詢、結束會議）
│       ├── availability.py     時間填寫 API（提交可用時段、查詢熱力圖資料）
│       └── records.py          紀錄 API（出席狀態、會議筆記、確認時間、發送 Email、總結）
│
└── frontend/
    ├── index.html              登入 / 註冊頁面
    ├── groups.html             群組列表頁面
    ├── meetings.html           群組內會議與資料夾列表
    ├── meeting.html            單一會議首頁（顯示候選日期與成員填寫狀態）
    ├── availability.html       填寫個人可用時段頁面
    ├── heatmap.html            熱力圖頁面（視覺化呈現最佳時段）
    ├── record.html             會議紀錄首頁（顯示決定時間、筆記入口）
    ├── attendance.html         出席狀態記錄頁面
    ├── notes.html              填寫會議筆記與備注頁面
    ├── summary.html            會議總結頁面（出席率與任務完成率圓餅圖）
    │
    └── static/
        ├── css/
        │   └── style.css       全站 CSS 樣式（莫蘭迪色系設計系統）
        └── js/
            └── api.js          前端 API 工具（所有與後端溝通的函式、Token 管理、Toast 通知）
```

---

## 五、環境變數說明

這些變數儲存在 Render 的 Environment 設定中，**絕對不能上傳到 GitHub**。

| 變數名稱 | 用途 |
|----------|------|
| `DATABASE_URL` | PostgreSQL 連線字串（Supabase Session Pooler）格式：`postgresql://postgres.[REF]:[PASSWORD]@[HOST]:5432/postgres` |
| `SECRET_KEY` | JWT Token 簽名密鑰（任意長字串），需保密 |
| `RESEND_API_KEY` | Resend 服務的 API 金鑰，用於發送通知 Email |
| `FROM_EMAIL` | 通知 Email 的寄件人地址，例如 `noreply@yourdomain.com` |

> 本地開發時，在 `backend/` 資料夾建立 `.env` 檔案並填入上述變數。`.env` 已加入 `.gitignore`，不會被上傳到 GitHub。

---

## 六、本地開發步驟

```bash
# 1. 進入後端目錄
cd meeting-assistant/backend

# 2. 建立虛擬環境並安裝套件
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 建立 .env 檔案（DATABASE_URL 留空則使用本地 SQLite）
SECRET_KEY=any-random-secret-string
RESEND_API_KEY=（選填）
FROM_EMAIL=（選填）

# 4. 啟動後端伺服器
uvicorn main:app --reload

# 5. 開啟瀏覽器
# http://localhost:8000
```

修改程式碼後，伺服器會自動重載（`--reload` 模式）。

---

## 七、更新部署流程

每次新增或修改功能後，只需三個步驟即可發布到線上：

```bash
# 步驟 1：完成程式碼修改後，推送到 GitHub
git add .
git commit -m "描述這次的更新內容"
git push
```

**步驟 2：** Render 自動偵測到新 commit，開始重新建置（約 2～3 分鐘）

**步驟 3：** 部署完成，線上版本即更新為最新功能
- 可在 Render Dashboard → Events 查看部署進度

> **注意：** 若只修改了 Render Environment 環境變數，需手動點擊 **Manual Deploy** 才會生效。

---

## 八、設計決策（為什麼這樣選）

| 決策 | 理由 |
|---|---|
| **密碼先 SHA-256 再 bcrypt** | bcrypt 只吃前 72 bytes，超過的部分會被靜默截斷。先做一次固定長度的 SHA-256 摘要就沒有這個上限，雜湊強度仍由 bcrypt 提供。 |
| **資料庫用 Supabase 而不是 Render 的磁碟** | Render 免費方案的檔案系統是暫時的，每次重新部署就會清空，SQLite 檔會連同資料一起消失。 |
| **前端不用框架** | 九個頁面、每頁一支表單，用純 HTML＋一個 `api.js` 就夠；不需要 build step，部署只有一個服務。 |
| **靜態檔由 FastAPI 自己送** | 前後端同源，省掉 CORS 與第二個部署目標；代價是要自己做路徑邊界檢查（見 `main.py` 的 `serve_frontend`）。 |
| **SECRET_KEY 不給預設值** | 有預設值就會有人帶著公開原始碼裡的字串上線，等於任何人都能偽造 token。寧可啟動失敗。 |

## 九、已知限制

- **JWT 有效期 7 天且無法撤銷**：登出只清掉瀏覽器的 token，伺服器端不做黑名單。
- **免費方案冷啟動**：閒置 15 分鐘後第一次開啟要等約 50 秒。
- **沒有寄信重試**：Resend 失敗只會寫進 log，不會重送。
- **schema 用 `create_all` 建立**：之後改欄位需要手動處理，還沒導入 alembic migration。
- **測試只涵蓋認證、權限與靜態檔路徑**（`backend/tests/`），業務邏輯（熱力圖、總結）還沒有測試。

## 十、測試

```bash
cd backend
SECRET_KEY=test-secret DATABASE_URL="sqlite:///./test.db" python -m pytest tests -q
```

## 授權

MIT，見 [LICENSE](LICENSE)。
