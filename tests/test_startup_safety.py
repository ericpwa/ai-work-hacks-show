from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from streamlit.testing.v1 import AppTest

import data_store
import data_store_supabase as cloud


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("network forbidden")))


def fake_client(rows):
    query = Mock()
    for method in ("select", "eq", "limit", "order"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    client = Mock()
    client.table.return_value = query
    return client, query


@pytest.mark.parametrize("rows", [[], [{"class_code": "TEST", "class_title": "Synthetic", "phase": "collecting"}]])
def test_cloud_init_and_read_never_mutate_or_purge(rows):
    client, query = fake_client(rows)
    with patch.object(cloud, "client", return_value=client), \
         patch.object(cloud, "ensure_class", side_effect=AssertionError("write forbidden")), \
         patch.object(cloud, "purge_old_data", side_effect=AssertionError("purge forbidden")):
        cloud.init_db()
        result = cloud.get_class(" test ")
    assert result["class_code"] == "TEST"
    assert result["phase"] == "collecting"
    for method in ("insert", "update", "delete", "upsert"):
        getattr(query, method).assert_not_called()
    client.rpc.assert_not_called()
    assert query.execute.call_count == 2


@pytest.mark.parametrize("failure_point", ["init_db", "get_class", "stats"])
def test_backend_failure_shows_safe_notice_without_sqlite_fallback(failure_point):
    fake = Mock()
    fake.get_class.return_value = {"class_code": "TEST", "phase": "collecting", "class_title": ""}
    fake.stats.return_value = {"submission_count": 0, "vote_count": 0, "voter_count": 0}
    getattr(fake, failure_point).side_effect = ConnectionError("synthetic-secret")
    with patch.object(data_store, "_backend", return_value=fake):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    assert any("資料服務暫時無法使用" in error.value for error in app.error)
    assert all("synthetic-secret" not in error.value for error in app.error)
    fake.ensure_class.assert_not_called()
    fake.purge_old_data.assert_not_called()


def test_empty_class_code_stops_before_backend_read():
    fake = Mock()
    with patch.object(data_store, "_backend", return_value=fake):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
        app.session_state["class_code"] = "   "
        app.run()
    assert not app.exception
    assert any("請輸入課堂代碼" in error.value for error in app.error)
    fake.get_class.assert_not_called()
    fake.ensure_class.assert_not_called()


def test_full_cloud_homepage_and_rerun_are_read_only():
    client, query = fake_client([])
    with patch.object(data_store, "_backend", return_value=cloud), \
         patch.object(data_store, "active_backend_name", return_value="supabase"), \
         patch.object(cloud, "client", return_value=client), \
         patch.object(cloud, "ensure_class", side_effect=AssertionError("write forbidden")), \
         patch.object(cloud, "purge_old_data", side_effect=AssertionError("purge forbidden")):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
        assert not app.exception
        app.run()
        assert not app.exception
    assert query.execute.call_count > 2
    for method in ("insert", "update", "delete", "upsert"):
        getattr(query, method).assert_not_called()
    client.rpc.assert_not_called()
