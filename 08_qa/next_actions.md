# QA Next Actions

1. 在 Supabase SQL Editor 執行 `supabase_schema.sql`。
2. 在 Streamlit Cloud secrets 設定 Supabase URL、service role key 與老師 PIN。
3. 部署後提交 2 筆作品，確認資料寫入 Supabase。
4. 使用同一學員代碼對同一作品連續投票，確認第二次會被阻擋。
5. 以老師 PIN 進入後台，測試流程切換、CSV 匯出、清理 90 天前資料。
6. 使用不同裝置開啟固定網址，確認老師後台可跨裝置使用。
