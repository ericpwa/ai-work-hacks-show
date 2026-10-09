from __future__ import annotations

import html
import os

import streamlit as st

from data_store import (
    DEFAULT_CLASS_CODE,
    add_vote,
    active_backend_name,
    create_submission,
    delete_submission,
    ensure_class,
    get_class,
    init_db,
    normalize_class_code,
    leaderboard,
    list_classes,
    purge_old_data,
    query_submissions,
    reset_votes,
    set_class_phase,
    set_submission_hidden,
    stats,
)


APP_TITLE = "AI Work Hacks 職場大絕"
DAYS = ["Day 1", "Day 2", "Day 3", "Day 4"]
PHASE_LABELS = {
    "collecting": "收件中",
    "voting": "投票中",
    "results": "公布結果",
}
PHASE_VALUES = {value: key for key, value in PHASE_LABELS.items()}


def secret_value(key: str, default: str = "") -> str:
    if os.getenv(key):
        return os.getenv(key, default)
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


ADMIN_PIN = secret_value("AI_WORK_HACKS_ADMIN_PIN", "2468")


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="★",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .main .block-container { padding-top: 1.5rem; }
    .work-card {
        border: 1px solid #d7dde8;
        border-radius: 8px;
        padding: 16px;
        min-height: 250px;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    .work-card h3 {
        font-size: 1.05rem;
        line-height: 1.35;
        margin: 0 0 0.35rem;
    }
    .meta {
        color: #526070;
        font-size: 0.88rem;
        margin-bottom: 0.75rem;
    }
    .summary {
        color: #243041;
        font-size: 0.93rem;
        min-height: 44px;
        margin-bottom: 0.75rem;
    }
    .vote-pill {
        display: inline-block;
        border-radius: 999px;
        padding: 4px 10px;
        background: #fff4d6;
        color: #6b4f00;
        font-weight: 700;
    }
    .star-preview {
        font-size: 1.45rem;
        letter-spacing: 2px;
        line-height: 1.2;
        margin: 0.2rem 0 0.45rem;
    }
    .star-on { color: #f5b301; }
    .star-off { color: #cbd5e1; }
    .stage-card {
        border-left: 6px solid #0f766e;
        padding: 20px 24px;
        background: #f7fbfa;
        border-radius: 8px;
        min-height: 150px;
    }
    .stage-title {
        font-size: 1.55rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }
    .stage-meta {
        color: #526070;
        font-size: 1rem;
    }
    .projection-title {
        font-size: 2.4rem;
        font-weight: 900;
        line-height: 1.15;
        margin: 0;
    }
    .projection-row {
        border-bottom: 1px solid #e2e8f0;
        padding: 14px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_store_unavailable() -> None:
    st.title(APP_TITLE)
    st.error("資料服務暫時無法使用。請稍後重試或請管理員查核部署日誌。")
    st.stop()


try:
    init_db()
except Exception:
    show_store_unavailable()


def safe(value: object) -> str:
    return html.escape(str(value or ""))


def current_class_code() -> str:
    return normalize_class_code(st.session_state.get("class_code", DEFAULT_CLASS_CODE))


def render_phase_banner(class_info: dict[str, str]) -> None:
    phase = class_info["phase"]
    hints = {
        "collecting": "請學員提交作品。投票可以先暖身，但正式排名建議切到「投票中」後再開始。",
        "voting": "現在進入投票時段。同一位學員對同一件作品只能投一次。",
        "results": "公布排行榜與講評。可切到投影展示模式給全班觀看。",
    }
    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">{safe(PHASE_LABELS[phase])}</div>
            <div class="stage-meta">課堂代碼：{safe(class_info["class_code"])} ｜ {safe(hints[phase])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_star_preview(rating: int) -> str:
    stars = []
    for index in range(1, 6):
        css_class = "star-on" if index <= rating else "star-off"
        stars.append(f'<span class="{css_class}">★</span>')
    return f'<div class="star-preview">{"".join(stars)}</div>'


def render_rating_control(row, *, key_prefix: str, disabled: bool) -> None:
    submission_id = int(row["id"])
    rating_key = f"{key_prefix}_rating_{submission_id}"
    st.session_state.setdefault(rating_key, 0)
    current_rating = int(st.session_state[rating_key])

    st.caption("選擇星數")
    st.markdown(render_star_preview(current_rating), unsafe_allow_html=True)

    star_cols = st.columns(5)
    for rating in range(1, 6):
        selected = current_rating >= rating
        label = "★" if selected else "☆"
        if star_cols[rating - 1].button(
            label,
            key=f"{rating_key}_{rating}",
            width="stretch",
            disabled=disabled,
            help=f"選擇 {rating} 顆星",
        ):
            st.session_state[rating_key] = rating
            st.rerun()

    submit_label = f"送出 {current_rating} 顆星" if current_rating else "請先選星數"
    if st.button(
        submit_label,
        key=f"{key_prefix}_submit_{submission_id}",
        width="stretch",
        disabled=disabled or current_rating == 0,
    ):
        try:
            add_vote(
                submission_id,
                class_code=current_class_code(),
                voter_label=st.session_state.get("student_code", ""),
                rating=current_rating,
            )
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.session_state[rating_key] = 0
            st.toast(f"已寫入 {current_rating} 顆星。")
            st.rerun()


def render_card(row, *, key_prefix: str, allow_vote: bool = True) -> None:
    st.markdown(
        f"""
        <div class="work-card">
            <h3>{safe(row["work_title"])}</h3>
            <div class="meta">{safe(row["name"])} ｜ {safe(row["role"])} ｜ {safe(row["day"])}</div>
            <div class="summary">{safe(row["summary"]) or "尚未填寫作品摘要。"}</div>
            <div class="vote-pill">{int(row["votes"])} 顆星</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    link_col, vote_col = st.columns([1, 1])
    with link_col:
        st.link_button("開啟作品", row["link"], width="stretch")
    with vote_col:
        render_rating_control(row, key_prefix=key_prefix, disabled=not allow_vote)


with st.sidebar:
    st.title("課堂入口")
    st.caption("v0.3 Cloud Ready：固定網址、雲端資料庫、3 個月保存")

    class_code_input = st.text_input(
        "課堂代碼 *",
        value=st.session_state.get("class_code", DEFAULT_CLASS_CODE),
        help="同一堂課請使用同一個代碼，例如 AIHACKS-0605。",
    )
    try:
        st.session_state["class_code"] = normalize_class_code(class_code_input)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    st.session_state["student_code"] = st.text_input(
        "學員代碼 *",
        value=st.session_state.get("student_code", ""),
        placeholder="例如 A01、王小明、第一組",
        help="用於一人一票。請不要輸入電話、Email、證件號或密碼。",
    ).strip()

    with st.expander("資料保護", expanded=False):
        st.write("請使用課堂暱稱或可公開展示的姓名，不要輸入電話、地址、Email、證件號、密碼或其他敏感資料。")

    with st.form("submission_form", clear_on_submit=True):
        st.subheader("發布成果")
        day = st.selectbox("展出日期", DAYS)
        name = st.text_input("學員姓名或暱稱 *", placeholder="例如 Eric PAN")
        role = st.text_input("品牌 / 職稱 / 組別 *", placeholder="例如 WBP / Founder")
        work_title = st.text_input("作品標題 *", placeholder="例如 用 AI 做週報自動化")
        link = st.text_input("作品連結 *", placeholder="https://...")
        summary = st.text_area("作品摘要", placeholder="用 1-2 句說明這個大絕解決了什麼職場問題。")
        submitted = st.form_submit_button("確認發布", width="stretch")

    if submitted:
        try:
            create_submission(
                class_code=current_class_code(),
                day=day,
                name=name,
                role=role,
                work_title=work_title,
                link=link,
                summary=summary,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success("發布成功，資料會保存 3 個月；重要作品請課後由老師匯出留存。")
            st.rerun()


class_code = current_class_code()
try:
    class_info = get_class(class_code)
    current_stats = stats(class_code)
except Exception:
    show_store_unavailable()

st.title(APP_TITLE)
backend_name = active_backend_name()
backend_label = "Supabase Cloud" if backend_name == "supabase" else "SQLite Local"
st.caption(f"翻轉教學成果發表平台 ｜ v0.3 Cloud Ready ｜ 資料後端：{backend_label}")
render_phase_banner(class_info)

metric_cols = st.columns(5)
metric_cols[0].metric("課堂代碼", class_code)
metric_cols[1].metric("已提交作品", current_stats["submission_count"])
metric_cols[2].metric("累積星數", current_stats["vote_count"])
metric_cols[3].metric("投票人數", current_stats["voter_count"])
metric_cols[4].metric("保存期限", "90 天")

tab_hall, tab_projection, tab_fame, tab_admin = st.tabs(["成果展示大廳", "投影展示模式", "星級名人堂", "老師管理後台"])

with tab_hall:
    filter_cols = st.columns([1.2, 2.0, 1.3])
    with filter_cols[0]:
        selected_day = st.selectbox("展期", ["看所有人", *DAYS])
    with filter_cols[1]:
        search = st.text_input("搜尋", placeholder="姓名、職稱、組別、作品標題或摘要")
    with filter_cols[2]:
        sort_label = st.segmented_control(
            "排序",
            ["最新提交", "最高星數", "最早提交"],
            default="最新提交",
        )

    sort_mode = {"最新提交": "latest", "最高星數": "top_votes", "最早提交": "oldest"}[sort_label]
    submissions = query_submissions(class_code=class_code, day=selected_day, search=search, sort_mode=sort_mode)
    voting_allowed = bool(st.session_state.get("student_code")) and class_info["phase"] in {"collecting", "voting"}

    if not st.session_state.get("student_code"):
        st.info("請先在左側填寫學員代碼，才可以投票。")
    if submissions.empty:
        st.info("目前沒有符合條件的作品。")
    else:
        columns = st.columns(3)
        for position, (_, row) in enumerate(submissions.iterrows()):
            with columns[position % 3]:
                render_card(row, key_prefix="hall_vote", allow_vote=voting_allowed)

with tab_projection:
    st.markdown(f"<p class='projection-title'>{safe(APP_TITLE)}</p>", unsafe_allow_html=True)
    st.caption(f"{safe(class_code)} ｜ {safe(PHASE_LABELS[class_info['phase']])}")
    proj_cols = st.columns([1.2, 1])
    latest = query_submissions(class_code=class_code, sort_mode="latest")
    ranking = leaderboard(class_code=class_code, limit=5)

    with proj_cols[0]:
        st.subheader("最新提交")
        if latest.empty:
            st.info("等待學員提交作品。")
        else:
            for _, row in latest.head(6).iterrows():
                st.markdown(
                    f"""
                    <div class="projection-row">
                        <strong>{safe(row["work_title"])}</strong><br>
                        {safe(row["name"])} ｜ {safe(row["role"])} ｜ {safe(row["day"])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with proj_cols[1]:
        st.subheader("TOP 5")
        if ranking.empty:
            st.info("尚無排行榜資料。")
        else:
            for idx, (_, row) in enumerate(ranking.iterrows(), start=1):
                st.markdown(
                    f"""
                    <div class="projection-row">
                        <strong>#{idx}　{safe(row["work_title"])}</strong><br>
                        {int(row["votes"])} 顆星 ｜ {safe(row["name"])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

with tab_fame:
    st.subheader("星級名人堂")
    ranking = leaderboard(class_code=class_code, limit=10)
    if ranking.empty or int(ranking["votes"].sum()) == 0:
        st.info("目前尚無投票紀錄。")
    else:
        top_cols = st.columns(3)
        medals = ["第一名", "第二名", "第三名"]
        for idx, (_, row) in enumerate(ranking.head(3).iterrows()):
            with top_cols[idx]:
                st.metric(medals[idx], f"{int(row['votes'])} 顆星")
                st.markdown(f"**{safe(row['work_title'])}**")
                st.caption(f"{safe(row['name'])} ｜ {safe(row['role'])}")
                st.link_button("觀看作品", row["link"], width="stretch")

        st.dataframe(
            ranking[["day", "name", "role", "work_title", "votes", "created_at"]],
            width="stretch",
            hide_index=True,
        )

with tab_admin:
    st.subheader("老師管理後台")
    admin_pin = st.text_input("老師 PIN", type="password", help="預設 PIN 是 2468，可用環境變數 AI_WORK_HACKS_ADMIN_PIN 調整。")

    if admin_pin != ADMIN_PIN:
        st.info("輸入老師 PIN 後可管理課堂流程、匯出資料、隱藏作品與重置投票。")
    else:
        admin_cols = st.columns([1, 1])
        with admin_cols[0]:
            class_title = st.text_input("課堂名稱", value=class_info.get("class_title", ""))
            if st.button("建立 / 更新課堂", width="stretch"):
                ensure_class(class_code, class_title)
                st.success("課堂資料已更新。")
                st.rerun()

        with admin_cols[1]:
            phase_label = st.selectbox(
                "課堂流程",
                list(PHASE_VALUES.keys()),
                index=list(PHASE_VALUES.keys()).index(PHASE_LABELS[class_info["phase"]]),
            )
            if st.button("套用流程", width="stretch"):
                set_class_phase(class_code, PHASE_VALUES[phase_label])
                st.success("課堂流程已更新。")
                st.rerun()

        all_rows = query_submissions(class_code=class_code, sort_mode="latest", include_hidden=True)
        st.download_button(
            "匯出本課堂 CSV",
            all_rows.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{class_code}_ai_work_hacks.csv",
            mime="text/csv",
            width="stretch",
        )
        st.caption("資料預設保存 90 天。優秀或重要作品請使用 CSV 匯出留存在地端。")

        st.divider()
        st.markdown("**作品管理**")
        if all_rows.empty:
            st.info("目前沒有作品可管理。")
        else:
            st.dataframe(
                all_rows[["id", "hidden", "day", "name", "role", "work_title", "votes", "created_at"]],
                width="stretch",
                hide_index=True,
            )
            manage_id = st.number_input("作品 ID", min_value=1, step=1)
            action_cols = st.columns(4)
            with action_cols[0]:
                if st.button("隱藏作品", width="stretch"):
                    set_submission_hidden(int(manage_id), hidden=True)
                    st.rerun()
            with action_cols[1]:
                if st.button("恢復作品", width="stretch"):
                    set_submission_hidden(int(manage_id), hidden=False)
                    st.rerun()
            with action_cols[2]:
                confirm_delete = st.checkbox("確認刪除")
                if st.button("刪除作品", width="stretch", disabled=not confirm_delete):
                    delete_submission(int(manage_id))
                    st.rerun()
            with action_cols[3]:
                confirm_reset = st.checkbox("確認重置投票")
                if st.button("重置本課堂投票", width="stretch", disabled=not confirm_reset):
                    reset_votes(class_code)
                    st.rerun()

        st.divider()
        st.markdown("**資料保留**")
        confirm_purge = st.checkbox("確認清理超過 90 天的資料")
        if st.button("清理超過 90 天資料", width="stretch", disabled=not confirm_purge):
            deleted_count = purge_old_data(retention_days=90)
            st.success(f"已清理 {deleted_count} 筆超過 90 天的作品資料。")
            st.rerun()

        st.divider()
        st.markdown("**所有課堂**")
        st.dataframe(list_classes(), width="stretch", hide_index=True)

