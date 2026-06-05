from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_store import (
    add_vote,
    create_submission,
    get_class,
    init_db,
    leaderboard,
    purge_old_data,
    query_submissions,
    reset_votes,
    set_class_phase,
    set_submission_hidden,
    stats,
)


def main() -> None:
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        class_code = "AIHACKS-TEST"
        init_db(db_path)

        first_id = create_submission(
            class_code=class_code,
            day="Day 1",
            name="Test Student",
            role="Group A",
            work_title="AI Weekly Report",
            link="https://example.com/report",
            summary="Use AI to draft and review a weekly report.",
            db_path=db_path,
        )
        second_id = create_submission(
            class_code=class_code,
            day="Day 2",
            name="Another Student",
            role="Group B",
            work_title="Prompt Library",
            link="https://example.com/prompts",
            summary="Reusable workplace prompts.",
            db_path=db_path,
        )
        other_class_id = create_submission(
            class_code="OTHER-CLASS",
            day="Day 1",
            name="Other Student",
            role="Group C",
            work_title="Other Class Work",
            link="https://example.com/other",
            db_path=db_path,
        )

        add_vote(first_id, class_code=class_code, voter_label="A01", db_path=db_path)
        add_vote(first_id, class_code=class_code, voter_label="A02", db_path=db_path)
        add_vote(second_id, class_code=class_code, voter_label="A01", db_path=db_path)

        duplicate_blocked = False
        try:
            add_vote(first_id, class_code=class_code, voter_label="A01", db_path=db_path)
        except ValueError:
            duplicate_blocked = True
        assert duplicate_blocked

        assert stats(class_code, db_path) == {"submission_count": 2, "vote_count": 3, "voter_count": 2}
        assert stats("OTHER-CLASS", db_path) == {"submission_count": 1, "vote_count": 0, "voter_count": 0}
        assert len(query_submissions(class_code=class_code, day="Day 1", db_path=db_path)) == 1
        assert len(query_submissions(class_code=class_code, search="weekly", db_path=db_path)) == 1
        assert int(leaderboard(class_code=class_code, limit=1, db_path=db_path).iloc[0]["id"]) == first_id

        set_class_phase(class_code, "voting", db_path=db_path)
        assert get_class(class_code, db_path)["phase"] == "voting"

        set_submission_hidden(first_id, hidden=True, db_path=db_path)
        assert len(query_submissions(class_code=class_code, db_path=db_path)) == 1
        assert len(query_submissions(class_code=class_code, include_hidden=True, db_path=db_path)) == 2

        reset_votes(class_code, db_path=db_path)
        assert stats(class_code, db_path)["vote_count"] == 0
        assert stats("OTHER-CLASS", db_path)["submission_count"] == 1
        assert other_class_id > 0
        assert purge_old_data(retention_days=90, db_path=db_path) == 0

    print("smoke test passed")


if __name__ == "__main__":
    main()
