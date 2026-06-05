# Revision Log

## 2026-06-05

- 升級為 v0.3 Cloud Ready。
- 新增 Supabase data store，支援 Streamlit Community Cloud 固定網址部署。
- 新增 backend router，依 secrets 自動選擇 Supabase 或 SQLite。
- 新增 90 天資料保存政策與老師後台清理按鈕。
- 新增 Supabase SQL schema 與 Streamlit secrets example。
- 驗證項目：SQLite smoke test passed、Supabase store import ok、Python py_compile passed。

## 2026-06-05 v0.2

- 升級為課堂穩定版 v0.2。
- 新增 `classes` 資料表、`class_code` 欄位與課堂流程狀態。
- 新增 `votes` 唯一投票約束與程式層查重，防止同一學員代碼對同一作品重複投票。
- 新增老師管理後台與投影展示模式。
- 更新 README、changelog、next_actions 與 smoke test。

## 2026-06-05 v0.1

- 依使用者要求建立《AI Work Hacks 職場大絕》MVP。
- 自主評估後未採用附件中的純 CSV 資料庫，改用 SQLite，原因是需解決多人課堂投票的併發寫入風險。
- 保留 Pandas DataFrame 作為查詢結果與表格呈現層。
