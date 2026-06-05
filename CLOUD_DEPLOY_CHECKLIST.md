# Cloud Deploy Checklist

## 1. Supabase

- [ ] Create a Supabase project.
- [ ] Open SQL Editor.
- [ ] Run `supabase_schema.sql`.
- [ ] Copy `SUPABASE_URL`.
- [ ] Copy `SUPABASE_SERVICE_ROLE_KEY`.

## 2. GitHub

- [ ] Create a GitHub repository, for example `ai-work-hacks-streamlit-mvp`.
- [ ] Push this project to GitHub.
- [ ] Confirm `.streamlit/secrets.toml` and `data/*.db` are not committed.

## 3. Streamlit Community Cloud

- [ ] Create app from GitHub repo.
- [ ] Entrypoint: `app.py`.
- [ ] Set app URL, for example `ai-work-hacks`.
- [ ] Add secrets:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
AI_WORK_HACKS_ADMIN_PIN = "CHANGE_ME"
```

## 4. Smoke Test

- [ ] Open fixed Streamlit URL.
- [ ] Create class code `AIHACKS-TEST`.
- [ ] Submit two works.
- [ ] Vote once as `A01`.
- [ ] Try voting again as `A01`; confirm duplicate vote is blocked.
- [ ] Open teacher admin from another device.
- [ ] Export CSV.
- [ ] Confirm important works are downloaded before the 90-day retention window.
