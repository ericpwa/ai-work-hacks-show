from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import data_store_sqlite


DEFAULT_CLASS_CODE = data_store_sqlite.DEFAULT_CLASS_CODE
DEFAULT_PHASE = data_store_sqlite.DEFAULT_PHASE
normalize_class_code = data_store_sqlite.normalize_class_code


def _secret_value(key: str, default: str = "") -> str:
    if os.getenv(key):
        return os.getenv(key, default)
    try:
        import streamlit as st

        return str(st.secrets.get(key, default))
    except Exception:
        return default


def active_backend_name() -> str:
    if _secret_value("SUPABASE_URL") and _secret_value("SUPABASE_SERVICE_ROLE_KEY"):
        return "supabase"
    return "sqlite"


@lru_cache(maxsize=1)
def _backend() -> Any:
    if active_backend_name() == "supabase":
        import data_store_supabase

        return data_store_supabase
    return data_store_sqlite


def init_db(*args: Any, **kwargs: Any) -> Any:
    return _backend().init_db(*args, **kwargs)


def ensure_class(*args: Any, **kwargs: Any) -> Any:
    return _backend().ensure_class(*args, **kwargs)


def get_class(*args: Any, **kwargs: Any) -> Any:
    return _backend().get_class(*args, **kwargs)


def list_classes(*args: Any, **kwargs: Any) -> Any:
    return _backend().list_classes(*args, **kwargs)


def set_class_phase(*args: Any, **kwargs: Any) -> Any:
    return _backend().set_class_phase(*args, **kwargs)


def create_submission(*args: Any, **kwargs: Any) -> Any:
    return _backend().create_submission(*args, **kwargs)


def add_vote(*args: Any, **kwargs: Any) -> Any:
    return _backend().add_vote(*args, **kwargs)


def query_submissions(*args: Any, **kwargs: Any) -> Any:
    return _backend().query_submissions(*args, **kwargs)


def leaderboard(*args: Any, **kwargs: Any) -> Any:
    return _backend().leaderboard(*args, **kwargs)


def stats(*args: Any, **kwargs: Any) -> Any:
    return _backend().stats(*args, **kwargs)


def set_submission_hidden(*args: Any, **kwargs: Any) -> Any:
    return _backend().set_submission_hidden(*args, **kwargs)


def delete_submission(*args: Any, **kwargs: Any) -> Any:
    return _backend().delete_submission(*args, **kwargs)


def reset_votes(*args: Any, **kwargs: Any) -> Any:
    return _backend().reset_votes(*args, **kwargs)


def purge_old_data(*args: Any, **kwargs: Any) -> Any:
    return _backend().purge_old_data(*args, **kwargs)


