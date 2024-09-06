"""Test package."""

from app import MainClass


def test_version() -> None:
    app = MainClass()
    assert app.name() == "name"
