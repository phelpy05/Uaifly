"""backend/db.py
Persistencia de conversas em SQLite.

Armazena o historico completo de cada sessao (identificada por um
session_id gerado no frontend) para que o usuario possa retomar
conversas anteriores e o contexto seja preservado entre recarregamentos.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "uaifly.db"


def _get_conn() -> sqlite3.Connection:
    """Retorna uma conexao com SQLite, criando o diretorio se necessario."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Cria as tabelas se nao existirem. Chamada na inicializacao do servidor."""
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                session_id    TEXT PRIMARY KEY,
                title         TEXT NOT NULL DEFAULT 'Nova conversa',
                history       TEXT NOT NULL DEFAULT '[]',
                created_at    TEXT,
                updated_at    TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_updated
                ON conversations(updated_at DESC);
        """)


# ---------------------------------------------------------------------------
# Leitura / escrita
# ---------------------------------------------------------------------------

def get_history(session_id: str) -> list[dict]:
    """Retorna o historico (lista de {role, content}) de uma sessao."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT history FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    return json.loads(row["history"]) if row else []


def list_sessions(limit: int = 20) -> list[dict]:
    """Lista sessoes, mais recentes primeiro."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT session_id, title, updated_at FROM conversations "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_conversation(session_id: str, history: list[dict], title: str | None = None) -> None:
    """Salva (insere ou atualiza) o historico completo de uma sessao."""
    now = datetime.now(timezone.utc).isoformat()

    if title is None:
        # Titulo automatico: primeiros 40 chars da primeira mensagem do usuario.
        title = next(
            (m["content"][:40] + ("..." if len(m["content"]) > 40 else "")
             for m in history if m["role"] == "user"),
            "Nova conversa",
        )

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, title, history, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "title = excluded.title, history = excluded.history, updated_at = excluded.updated_at",
            (session_id, title, json.dumps(history, ensure_ascii=False), now, now),
        )


def delete_conversation(session_id: str) -> None:
    """Remove uma sessao do banco."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
