# AI Work Hacks 職場大絕 Streamlit MVP

這是 Streamlit + Supabase / SQLite 的課堂互動 SaaS MVP，用於翻轉教學中的學員成果提交、星級投票、排行榜、老師管理與投影展示。

本專案是獨立項目，不屬於《企業管理實務：國家考試補習班教材》Agentic AI Workflow。

## v0.3 Cloud Ready

正式課堂建議使用：

```text
GitHub repo -> Streamlit Community Cloud -> Supabase PostgreSQL
```

這樣可以取得：

- 固定網址，不受教室、Wi-Fi、老師 Mac IP 影響。
- 多人同時使用，提交與投票寫入雲端資料庫。
- 老師後台可跨裝置使用。
- 課堂資料保存 90 天；重要作品由老師 CSV 匯出後自行留存。
- 本機仍可用 SQLite fallback 做開發與離線 demo。

## 正式上線狀態

v0.3 Cloud Ready 已上線：

```text
https://ai-work-hacks-classroom.streamlit.app/
```

結案交付文件：

- [老師結案交付文件](docs/TEACHER_HANDOFF_v0.3.md)
- [真實課堂測試 Checklist](docs/REAL_CLASSROOM_TEST_CHECKLIST_v0.3.md)

注意：正式老師 PIN、Supabase key 等 secret 只放在 Streamlit Cloud Secrets，不要寫入 GitHub。

## 功能

- 課堂代碼：不同班級或梯次可用不同 `class_code` 隔離資料。
- 一人一票：同一課堂中，同一學員代碼對同一作品只能投一次；每票可先選 1 到 5 顆星，再確認送出。
- 老師管理後台：用 PIN 管理課堂流程、匯出 CSV、隱藏 / 恢復 / 刪除作品、重置投票、清理超過 90 天資料。
- 投影展示模式：大字版顯示最新提交與 TOP 5，方便課堂投影。
- 雙資料層：有 Supabase secrets 時走 Supabase；沒有 secrets 時走本機 SQLite。

## 本機啟動

最簡單方式：在 Finder 裡雙擊：

```text
TEACHER_START_HERE.command
```

或在終端機執行：

```bash
cd "/Users/wenanpan/Desktop/Codex/AI Work Hacks 職場大絕 Streamlit MVP"
bash run_app.sh
```

本機開：

```text
http://127.0.0.1:8501
```

本機模式只建議開發、測試或離線備援；正式上課請使用 Streamlit Cloud 固定網址。

## Supabase 設定

1. 在 Supabase 建立新 project。
2. 打開 Supabase SQL Editor。
3. 貼上並執行：

```text
supabase_schema.sql
```

4. 到 Project Settings 取得：

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

注意：`SUPABASE_SERVICE_ROLE_KEY` 只能放在 Streamlit secrets，不得寫入 GitHub。

## Streamlit Cloud Secrets

部署到 Streamlit Community Cloud 時，在 Advanced settings > Secrets 貼上：

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
AI_WORK_HACKS_ADMIN_PIN = "請改成你的老師後台PIN"
```

可參考範本：

```text
.streamlit/secrets.example.toml
```

不要建立或提交真的 `.streamlit/secrets.toml` 到 GitHub。

## GitHub / Streamlit Cloud 部署

1. 建立 GitHub repository，例如 `ai-work-hacks-streamlit-mvp`。
2. 推送本專案檔案到 GitHub。
3. 到 Streamlit Community Cloud 建立 app。
4. 選擇 GitHub repo、branch、entrypoint：

```text
app.py
```

5. 在 Advanced settings 設定 secrets。
6. App URL 建議設定成：

```text
ai-work-hacks-classroom
```

7. 部署後分享固定網址，例如：

```text
https://ai-work-hacks-classroom.streamlit.app
```

## 資料保存政策

- 課堂資料預設保存 90 天。
- 老師後台可手動清理超過 90 天資料。
- App 啟動時 Supabase backend 也會嘗試清理超過 90 天資料。
- 優秀或重要作品請課後在老師後台匯出 CSV，另存地端。

## 本地測試

```bash
cd "/Users/wenanpan/Desktop/Codex/AI Work Hacks 職場大絕 Streamlit MVP"
.venv/bin/python scripts/smoke_test.py
```

這個 smoke test 驗證 SQLite fallback。Supabase Cloud 測試需先設定 Streamlit secrets 並執行 `supabase_schema.sql`。
