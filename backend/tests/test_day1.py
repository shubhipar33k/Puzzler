"""Tests for Day 1 — health check and basic route availability."""
import pytest


def test_health_endpoint(client):
    """GET /health must return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Puzzler" in response.json()["message"]


def test_register_and_login(client):
    """End-to-end: register a user then log in."""
    reg = client.post(
        "/api/auth/register",
        json={"username": "testplayer", "email": "test@puzzler.dev", "password": "secret123"},
    )
    assert reg.status_code == 201, reg.text
    assert "access_token" in reg.json()

    login = client.post(
        "/api/auth/login",
        json={"username": "testplayer", "password": "secret123"},
    )
    assert login.status_code == 200, login.text
    assert "access_token" in login.json()


def test_duplicate_username_rejected(client):
    """Registering the same username twice should fail with 400."""
    payload = {"username": "dupeuser", "email": "dupe@puzzler.dev", "password": "abc"}
    client.post("/api/auth/register", json=payload)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400


def test_generate_puzzle_stub(client):
    """POST /api/puzzle/generate returns 201 with a placeholder puzzle."""
    response = client.post(
        "/api/puzzle/generate",
        json={"type": "sudoku", "difficulty_band": "medium"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["type"] == "sudoku"
    assert data["difficulty_band"] == "medium"
