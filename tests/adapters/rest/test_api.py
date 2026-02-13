"""Tests for REST API endpoints."""

import pytest
from fastapi.testclient import TestClient

from chatterbox.adapters.rest import create_app


@pytest.fixture
def stt_only_app():
    """Create a test app in STT-only mode."""
    return create_app(mode="stt_only")


@pytest.fixture
def tts_only_app():
    """Create a test app in TTS-only mode."""
    return create_app(mode="tts_only")


@pytest.fixture
def combined_app():
    """Create a test app in combined mode."""
    return create_app(mode="combined")


def test_health_check_stt_only(stt_only_app):
    """Test health check endpoint in STT-only mode."""
    client = TestClient(stt_only_app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "stt_only"
    assert data["services"]["stt"] is True
    assert data["services"]["tts"] is False
    assert data["services"]["agent"] is False


def test_health_check_tts_only(tts_only_app):
    """Test health check endpoint in TTS-only mode."""
    client = TestClient(tts_only_app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "tts_only"
    assert data["services"]["stt"] is False
    assert data["services"]["tts"] is True
    assert data["services"]["agent"] is False


def test_health_check_combined(combined_app):
    """Test health check endpoint in combined mode."""
    client = TestClient(combined_app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "combined"
    assert data["services"]["stt"] is True
    assert data["services"]["tts"] is True
    assert data["services"]["agent"] is True


def test_stt_unavailable_in_tts_only(tts_only_app):
    """Test that STT endpoint returns 503 in TTS-only mode."""
    client = TestClient(tts_only_app)

    # Create a dummy audio file
    audio_data = b"dummy audio"
    response = client.post(
        "/stt",
        files={"file": ("audio.wav", audio_data, "audio/wav")},
    )

    assert response.status_code == 503
    assert "STT service not available" in response.json()["detail"]


def test_tts_unavailable_in_stt_only(stt_only_app):
    """Test that TTS endpoint returns 503 in STT-only mode."""
    client = TestClient(stt_only_app)

    response = client.post(
        "/tts",
        json={"text": "Hello world"},
    )

    assert response.status_code == 503
    assert "TTS service not available" in response.json()["detail"]


def test_tts_missing_text_field(tts_only_app):
    """Test TTS endpoint with missing text field."""
    client = TestClient(tts_only_app)

    response = client.post("/tts", json={})

    assert response.status_code == 400
    assert "Text field is required" in response.json()["detail"]


def test_chat_unavailable_in_stt_only(stt_only_app):
    """Test that chat endpoint returns 503 in STT-only mode."""
    client = TestClient(stt_only_app)

    response = client.post(
        "/chat",
        json={"text": "Hello"},
    )

    assert response.status_code == 503
    assert "Agent not available" in response.json()["detail"]


def test_stt_file_endpoint_unavailable_in_tts_only(tts_only_app):
    """Test that STT file endpoint returns 503 in TTS-only mode."""
    client = TestClient(tts_only_app)

    audio_data = b"dummy audio"
    response = client.post(
        "/stt/file",
        files={"file": ("audio.wav", audio_data, "audio/wav")},
    )

    assert response.status_code == 503
    assert "STT service not available" in response.json()["detail"]


def test_full_pipeline_only_in_full_mode(stt_only_app):
    """Test that full pipeline endpoint is only available in full mode."""
    client = TestClient(stt_only_app)

    audio_data = b"dummy audio"
    response = client.post(
        "/stt-chat-tts",
        files={"file": ("audio.wav", audio_data, "audio/wav")},
    )

    assert response.status_code == 503
    assert "Full pipeline only available in 'full' mode" in response.json()["detail"]
