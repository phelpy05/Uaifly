"""backend/server.py
Servidor Flask: serve frontend + rotas de chat com persistencia em SQLite.
"""

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from ai.gemini import GeminiConfigError, generate_response  # noqa: E402
from backend.db import init_db, get_history, save_conversation, list_sessions, delete_conversation  # noqa: E402

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

# Cria tabelas no boot (idempotente).
init_db()


# ---------------------------------------------------------------------------
# Frontend statico
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/chat")
def chat_page():
    return send_from_directory(FRONTEND_DIR, "chat.html")


# ---------------------------------------------------------------------------
# Chat API
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    mode = body.get("mode") or "geral"
    session_id = body.get("session_id", "").strip()

    if not message:
        return jsonify({"error": "Mensagem vazia."}), 400

    if not session_id:
        return jsonify({"error": "session_id não informado."}), 400

    try:
        # Carrega historico persistido e chama a IA com contexto.
        history = get_history(session_id)

        reply = generate_response(mode=mode, user_message=message, history=history)

        # Atualiza historico: adiciona mensagem do usuario e resposta da IA.
        history.append({"role": "user", "content": message})
        history.append({"role": "model", "content": reply})
        save_conversation(session_id, history)

        return jsonify({"reply": reply, "mode": mode})

    except GeminiConfigError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": f"Erro ao consultar a IA: {exc}"}), 502


@app.route("/api/sessions", methods=["GET"])
def api_list_sessions():
    """Lista sessoes anteriores (mais recentes primeiro)."""
    limit = min(int(request.args.get("limit", 20)), 100)
    return jsonify({"sessions": list_sessions(limit=limit)})


@app.route("/api/sessions/<session_id>", methods=["GET"])
def api_get_session(session_id: str):
    """Retorna o historico de uma sessao especifica."""
    history = get_history(session_id)
    return jsonify({"session_id": session_id, "history": history})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_delete_session(session_id: str):
    """Remove uma sessao."""
    delete_conversation(session_id)
    return jsonify({"deleted": True})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
