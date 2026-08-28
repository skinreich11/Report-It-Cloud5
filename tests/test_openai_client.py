import pytest

from app import create_app
from app.openai_client import ServiceConfigError, create_openai_client


def test_create_openai_client_requires_api_key(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "report_it.sqlite3",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "OPENAI_API_KEY": None,
        }
    )

    with app.app_context(), pytest.raises(ServiceConfigError):
        create_openai_client()
