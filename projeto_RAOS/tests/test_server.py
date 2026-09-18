"""tests/test_server.py
Testes do backend do Uaifly.

Rodar com: pytest tests/test_server.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ajusta path para importar o projeto.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.server import app
from backend.db import init_db, DB_PATH, get_history, save_conversation, list_sessions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def temp_db(monkeypatch):
    """Usa um SQLite temporario para os testes, sem sujar o banco real."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("backend.db.DB_PATH", Path(tmp_path))
    init_db()
    return tmp_path


@pytest.fixture
def client(monkeypatch):
    """Cliente Flask de teste com banco temporario."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("backend.db.DB_PATH", Path(tmp_path))
    init_db()
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Pagina inicial
# ---------------------------------------------------------------------------

def test_index_returns_html(client):
    """GET / deve retornar o HTML da pagina inicial."""
    res = client.get("/")
    assert res.status_code == 200
    assert b"uaifly" in res.data.lower() or b"Uaifly" in res.data


def test_chat_page_returns_html(client):
    """GET /chat deve retornar o HTML do chat."""
    res = client.get("/chat")
    assert res.status_code == 200
    assert b"chat-input" in res.data


def test_health_ok(client):
    """GET /api/health deve retornar status ok."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Chat API - validacoes
# ---------------------------------------------------------------------------

@patch("backend.server.generate_response", return_value="Resposta de teste.")
def test_chat_success(mock_gen, client):
    """POST /api/chat com dados validos deve retornar a resposta da IA."""
    res = client.post(
        "/api/chat",
        json={"message": "Ola", "mode": "geral", "session_id": "sess_abc123"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["reply"] == "Resposta de teste."
    assert data["mode"] == "geral"
    mock_gen.assert_called_once()


def test_chat_empty_message(client):
    """Mensagem vazia deve retornar 400."""
    res = client.post(
        "/api/chat",
        json={"message": "   ", "mode": "geral", "session_id": "sess_abc123"},
    )
    assert res.status_code == 400


def test_chat_missing_message(client):
    """Ausencia de message deve retornar 400."""
    res = client.post(
        "/api/chat",
        json={"mode": "geral", "session_id": "sess_abc123"},
    )
    assert res.status_code == 400


def test_chat_missing_session(client):
    """Ausencia de session_id deve retornar 400."""
    res = client.post(
        "/api/chat",
        json={"message": "Ola", "mode": "geral"},
    )
    assert res.status_code == 400
    assert "session_id" in res.get_json()["error"]


@patch("backend.server.generate_response", side_effect=Exception("API fora do ar"))
def test_chat_api_error(mock_gen, client):
    """Erro generico da IA deve retornar 502."""
    res = client.post(
        "/api/chat",
        json={"message": "Ola", "mode": "geral", "session_id": "sess_abc123"},
    )
    assert res.status_code == 502
    assert "API fora do ar" in res.get_json()["error"]


# ---------------------------------------------------------------------------
# Sessoes - CRUD
# ---------------------------------------------------------------------------

def test_list_sessions_empty(client):
    """Listar sessoes quando nao ha nenhuma."""
    res = client.get("/api/sessions")
    assert res.status_code == 200
    data = res.get_json()
    assert data["sessions"] == []


@patch("backend.server.generate_response", return_value="Oi!")
def test_session_persistence(mock_gen, client):
    """Conversa deve persistir no banco e ser recuperada depois."""
    session_id = "sess_persist_001"

    # Envia mensagem.
    res = client.post(
        "/api/chat",
        json={"message": "Ola", "mode": "geral", "session_id": session_id},
    )
    assert res.status_code == 200

    # Lista sessoes: deve aparecer 1.
    res = client.get("/api/sessions")
    assert len(res.get_json()["sessions"]) == 1

    # Recupera historico.
    res = client.get(f"/api/sessions/{session_id}")
    data = res.get_json()
    assert len(data["history"]) == 2  # user + model
    assert data["history"][0]["role"] == "user"
    assert data["history"][0]["content"] == "Ola"
    assert data["history"][1]["role"] == "model"
    assert data["history"][1]["content"] == "Oi!"


def test_delete_session(client):
    """Deve ser possivel apagar uma sessao."""
    session_id = "sess_del_001"
    save_conversation(session_id, [{"role": "user", "content": "teste"}])

    res = client.delete(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    assert res.get_json()["deleted"] is True

    # Confirma que foi apagado.
    res = client.get(f"/api/sessions/{session_id}")
    assert res.get_json()["history"] == []


# ---------------------------------------------------------------------------
# Database unitarios
# ---------------------------------------------------------------------------

def test_save_and_get_history(monkeypatch):
    """save_conversation / get_history devem armazenar e recuperar."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("backend.db.DB_PATH", Path(tmp_path))
    init_db()

    sess = "sess_db_unit"
    hist = [
        {"role": "user", "content": "Quero ir pra Lisboa"},
        {"role": "model", "content": "Lisboa e otimo! Quantos dias?"},
    ]
    save_conversation(sess, hist)

    result = get_history(sess)
    assert len(result) == 2
    assert result[0]["content"] == "Quero ir pra Lisboa"


def test_list_sessions_order(monkeypatch):
    """list_sessions deve retornar mais recente primeiro."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("backend.db.DB_PATH", Path(tmp_path))
    init_db()

    save_conversation("sess_old", [{"role": "user", "content": "antigo"}])
    import time; time.sleep(0.05)  # garante updated_at diferente
    save_conversation("sess_new", [{"role": "user", "content": "novo"}])

    sessions = list_sessions()
    assert sessions[0]["session_id"] == "sess_new"
    assert sessions[-1]["session_id"] == "sess_old"
