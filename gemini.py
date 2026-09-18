"""ai/gemini.py
Ponto unico de chamada para a API do Gemini.
Suporta:
  - Multiplas chaves de API com rotacao automatica (quando uma bate o limite,
    pula pra proxima).
  - Historico de conversa para manter contexto entre mensagens.

Configuracao das chaves:
  Opcao 1 (ENV): GEMINI_API_KEY=chave1
  Opcao 2 (ENV): GEMINI_API_KEYS=chave1,chave2,chave3,chave4,chave5
  Opcao 3 (.env): mesmo formato da ENV
"""

import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from prompts import PROMPTS, DEFAULT_MODE  # noqa: E402

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# ---------------------------------------------------------------------------
# Rotacao de chaves
# ---------------------------------------------------------------------------

class _KeyRotator:
    """Gerencia uma lista de chaves e faz rotacao automatica em erros 429."""

    def __init__(self, keys: list[str]):
        self._all_keys = keys
        self._blocked: dict[str, float] = {}  # chave -> timestamp do bloqueio
        self._block_duration = 60  # segundos ate tentar a chave bloqueada de novo

    def _available_keys(self) -> list[str]:
        """Retorna chaves que nao estao bloqueadas (ou cujo bloqueio expirou)."""
        now = time.time()
        # Libera chaves com bloqueio expirado.
        expired = [k for k, ts in self._blocked.items() if now - ts > self._block_duration]
        for k in expired:
            del self._blocked[k]
        return [k for k in self._all_keys if k not in self._blocked]

    def get_key(self) -> str:
        """Retorna a proxima chave disponivel. Se nenhuma, retorna a primeira."""
        avail = self._available_keys()
        if not avail:
            # Todas bloqueadas: reseta e usa a primeira.
            self._blocked.clear()
            return self._all_keys[0]
        return avail[0]

    def mark_blocked(self, key: str) -> None:
        """Marca uma chave como bloqueada (rate limit)."""
        self._blocked[key] = time.time()


def _load_keys() -> list[str]:
    """Carrega as chaves do ambiente ou do .env."""
    # Prioridade 1: GEMINI_API_KEYS (multiplas, separadas por virgula)
    multi = os.environ.get("GEMINI_API_KEYS")
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]

    # Prioridade 2: GEMINI_API_KEY (uma so)
    single = os.environ.get("GEMINI_API_KEY")
    if single:
        return [single.strip()]

    # Se python-dotenv carregou do .env, ja esta em os.environ
    raise GeminiConfigError(
        "GEMINI_API_KEY ou GEMINI_API_KEYS nao encontrada. Defina a variavel de "
        "ambiente ou crie um arquivo .env na raiz do projeto (veja .env.example)."
    )


_key_rotator = _KeyRotator(_load_keys())

# Cache de clientes: um por chave.
_clients: dict[str, genai.Client] = {}


class GeminiConfigError(RuntimeError):
    """Erro de configuracao (ex.: chave de API ausente)."""


def _get_client() -> tuple[genai.Client, str]:
    """Retorna (cliente, chave) — rotaciona entre as chaves disponiveis."""
    key = _key_rotator.get_key()
    if key not in _clients:
        _clients[key] = genai.Client(api_key=key)
    return _clients[key], key


# ---------------------------------------------------------------------------
# Construcao do historico
# ---------------------------------------------------------------------------

def _build_contents(history: list[dict] | None, user_message: str) -> list:
    """Monta a lista de contents para a API, incluindo historico."""
    contents: list = []

    if history:
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])],
                )
            )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )
    )
    return contents


# ---------------------------------------------------------------------------
# Chamada principal
# ---------------------------------------------------------------------------

def generate_response(
    mode: str,
    user_message: str,
    history: list[dict] | None = None,
) -> str:
    """
    Gera a resposta do assistente para uma mensagem do usuario.

    mode: chave de prompts.PROMPTS (ex.: 'roteiro', 'restaurante_tipico').
    user_message: texto digitado pelo usuario no chat.
    history: lista de {role, content} das mensagens anteriores (opcional).
    """
    if not user_message or not user_message.strip():
        raise ValueError("Mensagem vazia.")

    system_prompt = PROMPTS.get(mode, PROMPTS[DEFAULT_MODE])
    contents = _build_contents(history, user_message.strip())

    # Tenta todas as chaves antes de desistir.
    max_attempts = len(_key_rotator._all_keys)
    last_error = None

    for _ in range(max_attempts):
        client, key = _get_client()

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                ),
            )

            text = getattr(response, "text", None)
            return text.strip() if text else "Nao consegui gerar uma resposta agora. Pode tentar de novo?"

        except Exception as exc:
            err_msg = str(exc)
            # Erro 429 = rate limit / quota exceeded -> bloqueia a chave e tenta outra.
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                _key_rotator.mark_blocked(key)
                last_error = exc
                continue
            # Outro erro (ex.: chave invalida, 503) -> relanca na hora.
            raise

    # Todas as chaves falharam (rate limit).
    raise last_error or GeminiConfigError("Todas as chaves atingiram o limite de requisicoes. Tente novamente em alguns minutos.")
