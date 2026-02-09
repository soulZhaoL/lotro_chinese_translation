# 维护模式拦截测试。
from typing import Dict

from fastapi.testclient import TestClient

from server.app import create_app
from server.config import loader


def _build_config(enabled: bool) -> Dict[str, object]:
    return {
        "database": {"dsn": "postgresql://test:pass@localhost:5432/lotro"},
        "auth": {
            "hash_algorithm": "sha256",
            "salt_bytes": 16,
            "token_secret": "test-secret",
            "token_ttl_seconds": 3600,
        },
        "pagination": {"default_page_size": 20, "max_page_size": 200},
        "locks": {"default_ttl_seconds": 1800},
        "cors": {
            "allow_origins": ["*"],
            "allow_methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"],
            "expose_headers": [],
            "allow_credentials": False,
            "max_age": 600,
        },
        "http": {"gzip_minimum_size": 1024},
        "text_list": {"max_text_length": 5000},
        "maintenance": {
            "enabled": enabled,
            "message": "系统维护中",
            "allow_paths": ["/health"],
        },
    }


def _client_with_config(monkeypatch, config: Dict[str, object]) -> TestClient:
    monkeypatch.setattr(loader, "_CONFIG_CACHE", config)
    return TestClient(create_app())


def test_maintenance_enabled_blocks_login(monkeypatch):
    client = _client_with_config(monkeypatch, _build_config(True))

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["maintenance"]["enabled"] is True

    response = client.post("/auth/login", json={"username": "any", "password": "any"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "MAINTENANCE"


def test_maintenance_disabled_allows_health(monkeypatch):
    client = _client_with_config(monkeypatch, _build_config(False))

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["maintenance"]["enabled"] is False
