# Changelog

## 2026-06-05 v0.3 handoff

- 新增老師結案交付文件：`docs/TEACHER_HANDOFF_v0.3.md`。
- 新增真實課堂測試 checklist：`docs/REAL_CLASSROOM_TEST_CHECKLIST_v0.3.md`。
- 更新 README，補上正式網址與交付文件入口。
- 更新 `next_actions.md`，將部署任務改為真實課堂測試與 v0.4 優先排序。

## 2026-06-05

- 升級為「v0.3 Cloud Ready」。
- 新增 `data_store.py` backend router：有 Supabase secrets 時使用 Supabase，否則使用 SQLite fallback。
- 保留 SQLite 本機資料層為 `data_store_sqlite.py`。
- 新增 Supabase 雲端資料層 `data_store_supabase.py`。
- 新增 `supabase_schema.sql`，包含 classes / submissions / votes、唯一投票規則、RLS、service_role grants、90 天清理 RPC。
- 新增 `.streamlit/secrets.example.toml`，供 Streamlit Cloud secrets 設定使用。
- 更新老師後台，支援手動清理超過 90 天資料。
- 將資料保存政策從永久保存改為 90 天保存，重要作品由老師 CSV 匯出留存。
- 更新 README 為 GitHub + Streamlit Cloud + Supabase 部署主線。

## 2026-06-05 v0.2

- 升級為「課堂穩定版 v0.2」。
- 新增課堂代碼 `class_code`，支援不同課堂資料隔離。
- 新增一人一票規則，同一學員代碼對同一作品不能重複投票。
- 新增老師管理後台：課堂流程、CSV 匯出、隱藏 / 恢復 / 刪除作品、重置投票。
- 新增投影展示模式，顯示最新提交與 TOP 5。
- 新增資料庫遷移邏輯，舊 SQLite 資料庫啟動時可自動補欄位。
- 更新 smoke test，覆蓋課堂隔離、一人一票、流程切換、隱藏作品與重置投票。

## 2026-06-05 v0.1

- 建立 `AI Work Hacks 職場大絕` Streamlit MVP。
- 將附件 CSV MVP 升級為 SQLite 持久化資料層，改善併發寫入與查詢效能。
- 新增學員成果提交、作品搜尋、展期篩選、排序、投票、星級名人堂、資料表檢視與 CSV 匯出。
- 新增 smoke test 驗證提交、投票、排行榜與查詢邏輯。
