from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from postgrest.exceptions import APIError
from supabase import Client, create_client


DEFAULT_CLASS_CODE = "AIHACKS-0605"
DEFAULT_PHASE = "collecting"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_class_code(class_code: str) -> str:
    cleaned = class_code.strip().upper().replace(" ", "-")
    if not cleaned:
        raise ValueError("請輸入課堂代碼。")
    return cleaned


def normalize_required(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"請填寫{label}。")
    return cleaned


def normalize_link(link: str) -> str:
    cleaned = link.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("作品連結必須是 http 或 https URL。")
    return cleaned


def _secret_value(key: str, default: str = "") -> str:
    if os.getenv(key):
        return os.getenv(key, default)
    try:
        import streamlit as st

        return str(st.secrets.get(key, default))
    except Exception:
        return default


@lru_cache(maxsize=1)
def client() -> Client:
    url = _secret_value("SUPABASE_URL")
    key = _secret_value("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY。")
    return create_client(url, key)


def _rows_to_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows or [])


def _execute(query: Any) -> Any:
    try:
        return query.execute()
    except APIError as exc:
        message = getattr(exc, "message", None) or str(exc)
        raise ValueError(message) from exc


def init_db() -> None:
    ensure_class(DEFAULT_CLASS_CODE, "AI Work Hacks 課堂")
    purge_old_data(retention_days=90)


def ensure_class(class_code: str, class_title: str = "") -> str:
    code = normalize_class_code(class_code)
    title = class_title.strip()
    now = utc_now()
    payload = {
        "class_code": code,
        "class_title": title,
        "updated_at": now,
    }
    existing = _execute(client().table("classes").select("class_code").eq("class_code", code).limit(1))
    if existing.data:
        update_payload = {"updated_at": now}
        if title:
            update_payload["class_title"] = title
        _execute(client().table("classes").update(update_payload).eq("class_code", code))
    else:
        payload.update({"phase": DEFAULT_PHASE, "created_at": now})
        _execute(client().table("classes").insert(payload))
    return code


def get_class(class_code: str) -> dict[str, str]:
    code = ensure_class(class_code)
    result = _execute(client().table("classes").select("*").eq("class_code", code).limit(1))
    return dict(result.data[0])


def list_classes() -> pd.DataFrame:
    rows = _execute(client().table("classes").select("*").order("updated_at", desc=True)).data or []
    submissions = _execute(client().table("submissions").select("class_code,votes")).data or []
    counts: dict[str, dict[str, int]] = {}
    for row in submissions:
        code = row["class_code"]
        counts.setdefault(code, {"submissions": 0, "votes": 0})
        counts[code]["submissions"] += 1
        counts[code]["votes"] += int(row.get("votes") or 0)
    for row in rows:
        row.update(counts.get(row["class_code"], {"submissions": 0, "votes": 0}))
    return _rows_to_df(rows)


def set_class_phase(class_code: str, phase: str) -> None:
    if phase not in {"collecting", "voting", "results"}:
        raise ValueError("未知的課堂流程狀態。")
    code = ensure_class(class_code)
    _execute(
        client()
        .table("classes")
        .update({"phase": phase, "updated_at": utc_now()})
        .eq("class_code", code)
    )


def create_submission(
    *,
    class_code: str,
    day: str,
    name: str,
    role: str,
    work_title: str,
    link: str,
    summary: str = "",
) -> int:
    code = ensure_class(class_code)
    now = utc_now()
    payload = {
        "class_code": code,
        "day": normalize_required(day, "展出日期"),
        "name": normalize_required(name, "學員姓名或暱稱"),
        "role": normalize_required(role, "品牌 / 職稱 / 組別"),
        "work_title": normalize_required(work_title, "作品標題"),
        "link": normalize_link(link),
        "summary": summary.strip(),
        "votes": 0,
        "hidden": False,
        "created_at": now,
        "updated_at": now,
    }
    result = _execute(client().table("submissions").insert(payload))
    return int(result.data[0]["id"])


def add_vote(submission_id: int, *, class_code: str, voter_label: str) -> None:
    code = normalize_class_code(class_code)
    voter = normalize_required(voter_label, "學員代碼")
    try:
        _execute(
            client().rpc(
                "ai_work_hacks_add_vote_once",
                {
                    "p_submission_id": int(submission_id),
                    "p_class_code": code,
                    "p_voter_label": voter,
                },
            )
        )
    except ValueError as exc:
        if "duplicate key" in str(exc).lower() or "unique" in str(exc).lower():
            raise ValueError("你已經投過這件作品，為了公平不能重複投票。") from exc
        raise


def query_submissions(
    *,
    class_code: str,
    day: str = "看所有人",
    search: str = "",
    sort_mode: str = "latest",
    include_hidden: bool = False,
) -> pd.DataFrame:
    code = normalize_class_code(class_code)
    query = client().table("submissions").select("*").eq("class_code", code)
    if not include_hidden:
        query = query.eq("hidden", False)
    if day != "看所有人":
        query = query.eq("day", day)
    if search.strip():
        keyword = search.strip()
        query = query.or_(
            f"name.ilike.%{keyword}%,role.ilike.%{keyword}%,work_title.ilike.%{keyword}%,summary.ilike.%{keyword}%"
        )
    if sort_mode == "top_votes":
        query = query.order("votes", desc=True).order("created_at", desc=True)
    elif sort_mode == "oldest":
        query = query.order("created_at", desc=False).order("id", desc=False)
    else:
        query = query.order("created_at", desc=True).order("id", desc=True)
    return _rows_to_df(_execute(query).data or [])


def leaderboard(*, class_code: str, limit: int = 10) -> pd.DataFrame:
    code = normalize_class_code(class_code)
    result = _execute(
        client()
        .table("submissions")
        .select("*")
        .eq("class_code", code)
        .eq("hidden", False)
        .order("votes", desc=True)
        .order("created_at", desc=True)
        .limit(limit)
    )
    return _rows_to_df(result.data or [])


def stats(class_code: str) -> dict[str, int]:
    code = normalize_class_code(class_code)
    rows = _execute(
        client().table("submissions").select("id,votes").eq("class_code", code).eq("hidden", False)
    ).data or []
    votes = _execute(client().table("votes").select("voter_label").eq("class_code", code)).data or []
    return {
        "submission_count": len(rows),
        "vote_count": sum(int(row.get("votes") or 0) for row in rows),
        "voter_count": len({row["voter_label"] for row in votes}),
    }


def set_submission_hidden(submission_id: int, *, hidden: bool) -> None:
    _execute(
        client()
        .table("submissions")
        .update({"hidden": bool(hidden), "updated_at": utc_now()})
        .eq("id", int(submission_id))
    )


def delete_submission(submission_id: int) -> None:
    _execute(client().table("votes").delete().eq("submission_id", int(submission_id)))
    _execute(client().table("submissions").delete().eq("id", int(submission_id)))


def reset_votes(class_code: str) -> None:
    code = normalize_class_code(class_code)
    _execute(client().table("votes").delete().eq("class_code", code))
    _execute(
        client()
        .table("submissions")
        .update({"votes": 0, "updated_at": utc_now()})
        .eq("class_code", code)
    )


def purge_old_data(*, retention_days: int = 90) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="seconds")
    result = _execute(client().table("submissions").delete().lt("created_at", cutoff))
    return len(result.data or [])
