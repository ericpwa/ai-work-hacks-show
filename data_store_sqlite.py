from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from datetime import timedelta
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import pandas as pd


DB_PATH = Path(__file__).resolve().parent / "data" / "ai_work_hacks.db"
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


def normalize_rating(rating: int) -> int:
    try:
        score = int(rating)
    except (TypeError, ValueError) as exc:
        raise ValueError("請選擇 1 到 5 顆星。") from exc
    if score < 1 or score > 5:
        raise ValueError("請選擇 1 到 5 顆星。")
    return score


@contextmanager
def get_connection(db_path: Path | str = DB_PATH) -> Iterator[sqlite3.Connection]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
    finally:
        conn.close()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if column not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db(db_path: Path | str = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS classes (
                class_code TEXT PRIMARY KEY,
                class_title TEXT NOT NULL DEFAULT '',
                phase TEXT NOT NULL DEFAULT 'collecting',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_code TEXT NOT NULL DEFAULT 'AIHACKS-0605',
                day TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                work_title TEXT NOT NULL,
                link TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                votes INTEGER NOT NULL DEFAULT 0 CHECK (votes >= 0),
                hidden INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_code TEXT NOT NULL DEFAULT 'AIHACKS-0605',
                submission_id INTEGER NOT NULL,
                voter_label TEXT NOT NULL,
                rating INTEGER NOT NULL DEFAULT 1 CHECK (rating BETWEEN 1 AND 5),
                created_at TEXT NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
                UNIQUE (class_code, submission_id, voter_label)
            );
            """
        )

        _add_column(conn, "submissions", "class_code", "TEXT NOT NULL DEFAULT 'AIHACKS-0605'")
        _add_column(conn, "submissions", "hidden", "INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "votes", "class_code", "TEXT NOT NULL DEFAULT 'AIHACKS-0605'")
        _add_column(conn, "votes", "rating", "INTEGER NOT NULL DEFAULT 1 CHECK (rating BETWEEN 1 AND 5)")

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_submissions_class_day_created
                ON submissions(class_code, day, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_submissions_class_votes
                ON submissions(class_code, hidden, votes DESC, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_submissions_search
                ON submissions(name, role, work_title);
            CREATE INDEX IF NOT EXISTS idx_votes_submission
                ON votes(submission_id, created_at DESC);
            """
        )
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_one_per_student
                    ON votes(class_code, submission_id, voter_label)
                """
            )
        except sqlite3.IntegrityError:
            pass
        ensure_class(DEFAULT_CLASS_CODE, "AI Work Hacks 課堂", db_path=db_path)


def ensure_class(
    class_code: str,
    class_title: str = "",
    *,
    db_path: Path | str = DB_PATH,
) -> str:
    code = normalize_class_code(class_code)
    title = class_title.strip()
    now = utc_now()
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO classes (class_code, class_title, phase, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(class_code) DO UPDATE SET
                class_title = CASE
                    WHEN excluded.class_title != '' THEN excluded.class_title
                    ELSE classes.class_title
                END,
                updated_at = excluded.updated_at
            """,
            (code, title, DEFAULT_PHASE, now, now),
        )
    return code


def get_class(class_code: str, db_path: Path | str = DB_PATH) -> dict[str, str]:
    code = ensure_class(class_code, db_path=db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM classes WHERE class_code = ?", (code,)).fetchone()
    return dict(row)


def list_classes(db_path: Path | str = DB_PATH) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            """
            SELECT c.class_code, c.class_title, c.phase,
                   COUNT(s.id) AS submissions,
                   COALESCE(SUM(s.votes), 0) AS votes
              FROM classes c
              LEFT JOIN submissions s ON s.class_code = c.class_code
             GROUP BY c.class_code, c.class_title, c.phase
             ORDER BY c.updated_at DESC
            """,
            conn,
        )


def set_class_phase(
    class_code: str,
    phase: str,
    *,
    db_path: Path | str = DB_PATH,
) -> None:
    if phase not in {"collecting", "voting", "results"}:
        raise ValueError("未知的課堂流程狀態。")
    code = ensure_class(class_code, db_path=db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE classes SET phase = ?, updated_at = ? WHERE class_code = ?",
            (phase, utc_now(), code),
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
    db_path: Path | str = DB_PATH,
) -> int:
    code = ensure_class(class_code, db_path=db_path)
    values = {
        "class_code": code,
        "day": normalize_required(day, "展出日期"),
        "name": normalize_required(name, "學員姓名或暱稱"),
        "role": normalize_required(role, "品牌 / 職稱 / 組別"),
        "work_title": normalize_required(work_title, "作品標題"),
        "link": normalize_link(link),
        "summary": summary.strip(),
    }

    now = utc_now()
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        cursor = conn.execute(
            """
            INSERT INTO submissions
                (class_code, day, name, role, work_title, link, summary, votes, hidden, created_at, updated_at)
            VALUES
                (:class_code, :day, :name, :role, :work_title, :link, :summary, 0, 0, :created_at, :updated_at)
            """,
            {**values, "created_at": now, "updated_at": now},
        )
        conn.execute("COMMIT;")
        return int(cursor.lastrowid)


def add_vote(
    submission_id: int,
    *,
    class_code: str,
    voter_label: str,
    rating: int = 1,
    db_path: Path | str = DB_PATH,
) -> None:
    code = normalize_class_code(class_code)
    voter = normalize_required(voter_label, "學員代碼")
    score = normalize_rating(rating)
    now = utc_now()
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        row = conn.execute(
            "SELECT id FROM submissions WHERE id = ? AND class_code = ? AND hidden = 0",
            (submission_id, code),
        ).fetchone()
        if row is None:
            conn.execute("ROLLBACK;")
            raise ValueError("找不到指定作品，投票未寫入。")
        existing_vote = conn.execute(
            """
            SELECT id
              FROM votes
             WHERE class_code = ? AND submission_id = ? AND voter_label = ?
            """,
            (code, submission_id, voter),
        ).fetchone()
        if existing_vote is not None:
            conn.execute("ROLLBACK;")
            raise ValueError("你已經投過這件作品，為了公平不能重複投票。")
        try:
            conn.execute(
                """
                INSERT INTO votes (class_code, submission_id, voter_label, rating, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (code, submission_id, voter, score, now),
            )
        except sqlite3.IntegrityError as exc:
            conn.execute("ROLLBACK;")
            raise ValueError("你已經投過這件作品，為了公平不能重複投票。") from exc
        conn.execute(
            """
            UPDATE submissions
               SET votes = votes + ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (score, now, submission_id),
        )
        conn.execute("COMMIT;")


def query_submissions(
    *,
    class_code: str,
    day: str = "看所有人",
    search: str = "",
    sort_mode: str = "latest",
    include_hidden: bool = False,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    code = normalize_class_code(class_code)
    clauses: list[str] = ["class_code = ?"]
    params: list[str | int] = [code]

    if not include_hidden:
        clauses.append("hidden = 0")

    if day != "看所有人":
        clauses.append("day = ?")
        params.append(day)

    if search.strip():
        keyword = f"%{search.strip()}%"
        clauses.append(
            "(name LIKE ? COLLATE NOCASE OR role LIKE ? COLLATE NOCASE "
            "OR work_title LIKE ? COLLATE NOCASE OR summary LIKE ? COLLATE NOCASE)"
        )
        params.extend([keyword, keyword, keyword, keyword])

    order_by = {
        "latest": "created_at DESC, id DESC",
        "top_votes": "votes DESC, created_at DESC",
        "oldest": "created_at ASC, id ASC",
    }.get(sort_mode, "created_at DESC, id DESC")

    sql = "SELECT * FROM submissions WHERE " + " AND ".join(clauses)
    sql += f" ORDER BY {order_by}"

    with get_connection(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def leaderboard(
    *,
    class_code: str,
    limit: int = 10,
    db_path: Path | str = DB_PATH,
) -> pd.DataFrame:
    code = normalize_class_code(class_code)
    with get_connection(db_path) as conn:
        return pd.read_sql_query(
            """
            SELECT *
              FROM submissions
             WHERE class_code = ? AND hidden = 0
             ORDER BY votes DESC, created_at DESC
             LIMIT ?
            """,
            conn,
            params=(code, limit),
        )


def stats(class_code: str, db_path: Path | str = DB_PATH) -> dict[str, int]:
    code = normalize_class_code(class_code)
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS submission_count,
                COALESCE(SUM(votes), 0) AS vote_count
              FROM submissions
             WHERE class_code = ? AND hidden = 0
            """,
            (code,),
        ).fetchone()
        voters = conn.execute(
            "SELECT COUNT(DISTINCT voter_label) AS voter_count FROM votes WHERE class_code = ?",
            (code,),
        ).fetchone()
        return {
            "submission_count": int(row["submission_count"]),
            "vote_count": int(row["vote_count"]),
            "voter_count": int(voters["voter_count"]),
        }


def set_submission_hidden(
    submission_id: int,
    *,
    hidden: bool,
    db_path: Path | str = DB_PATH,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE submissions SET hidden = ?, updated_at = ? WHERE id = ?",
            (1 if hidden else 0, utc_now(), submission_id),
        )


def delete_submission(submission_id: int, db_path: Path | str = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("DELETE FROM votes WHERE submission_id = ?", (submission_id,))
        conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        conn.execute("COMMIT;")


def reset_votes(class_code: str, db_path: Path | str = DB_PATH) -> None:
    code = normalize_class_code(class_code)
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("DELETE FROM votes WHERE class_code = ?", (code,))
        conn.execute(
            "UPDATE submissions SET votes = 0, updated_at = ? WHERE class_code = ?",
            (utc_now(), code),
        )
        conn.execute("COMMIT;")


def purge_old_data(*, retention_days: int = 90, db_path: Path | str = DB_PATH) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="seconds")
    with get_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE;")
        old_ids = [
            int(row["id"])
            for row in conn.execute("SELECT id FROM submissions WHERE created_at < ?", (cutoff,)).fetchall()
        ]
        for submission_id in old_ids:
            conn.execute("DELETE FROM votes WHERE submission_id = ?", (submission_id,))
        conn.execute("DELETE FROM submissions WHERE created_at < ?", (cutoff,))
        conn.execute("COMMIT;")
        return len(old_ids)
