from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings


def _prod_settings(**overrides: object) -> Settings:
    base = {
        "app_env": "production",
        "jwt_secret": "production-test-secret-at-least-32b",
        "cors_origins": "https://ads-inversiones.es,https://backoffice.ads-inversiones.es",
    }
    base.update(overrides)
    return Settings(**base)


def test_production_resolves_docs_urls_to_none():
    settings = _prod_settings()
    assert settings.is_production is True
    assert settings.resolved_docs_url is None
    assert settings.resolved_redoc_url is None
    assert settings.resolved_openapi_url is None


def test_development_keeps_default_docs_urls():
    settings = Settings(
        app_env="development",
        jwt_secret="dev-only-change-me-use-32b-min-secret",
    )
    assert settings.resolved_docs_url == "/docs"
    assert settings.resolved_redoc_url == "/redoc"
    assert settings.resolved_openapi_url == "/openapi.json"


def test_blank_docs_urls_disable_even_in_development():
    settings = Settings(
        app_env="development",
        jwt_secret="dev-only-change-me-use-32b-min-secret",
        app_docs_url="",
        app_redoc_url=" ",
        app_openapi_url="",
    )
    assert settings.resolved_docs_url is None
    assert settings.resolved_redoc_url is None
    assert settings.resolved_openapi_url is None


def test_fastapi_returns_404_when_docs_disabled():
    """Mirrors PRO wiring: FastAPI(docs_url=None, ...) → 404 on doc paths."""
    settings = _prod_settings()
    app = FastAPI(
        docs_url=settings.resolved_docs_url,
        redoc_url=settings.resolved_redoc_url,
        openapi_url=settings.resolved_openapi_url,
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_production_cors_includes_backoffice_origin():
    settings = _prod_settings()
    assert "https://backoffice.ads-inversiones.es" in settings.cors_origin_list
    assert "https://ads-inversiones.es" in settings.cors_origin_list
