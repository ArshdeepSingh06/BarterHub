import pytest

import auth


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DATABASE", str(tmp_path / "test.db"))
    auth.setup_auth_database()


def test_valid_email():
    assert auth.valid_email("a.b+c@example.co.uk")
    assert not auth.valid_email("not-an-email")


def test_signup_and_login():
    assert auth.create_user("Ann", "Ann@Example.com", "password1")
    assert not auth.create_user("Ann2", "ann@example.com", "password1")
    assert auth.login_user("ANN@example.com", "password1")["name"] == "Ann"
    assert auth.login_user("ann@example.com", "bad") is None
    assert auth.login_user("nobody@example.com", "password1") is None
