# Uaifly

Assistente de viagem por IA (chat), com backend em Flask fazendo proxy
para o Gemini — a chave de API fica só no servidor, nunca no navegador.

## Estrutura

```
├── frontend/           → interface (HTML, CSS, JS puro)
│   ├── index.html        → página inicial (site institucional)
│   ├── chat.html          → assistente (chat com a IA)
│   ├── style.css          → estilos das duas páginas
│   ├── app.js              → lógica das duas páginas
│   └── assets/logo.png
├── backend/
│   └── server.py        → serve o frontend + rota POST /api/chat (proxy)
├── ai/
│   └── gemini.py         → chamada à API do Gemini
├── data/                  → reservada para uso futuro (vazia por enquanto)
├── prompts.py             → prompt de cada funcionalidade da IA
├── requirements.txt
├── render.yaml             → configuração de deploy no Render
├── .gitignore
└── .env.example
```

A página inicial (`index.html`) é a home institucional, com o botão
"Planejar viagem" levando para `chat.html`, onde a conversa com a IA
acontece de fato.

## Funcionalidades (modos do chat)

Roteiro · Dicas de viagem · Hotéis · Voos · Eventos · Fuso-horário ·
**Restaurante típico** · **Passeios** · **Intérprete pessoal** ·
**Intérprete online**

Cada uma tem seu próprio prompt em `prompts.py`. Pra adicionar uma nova
funcionalidade: crie a chave em `PROMPTS`, e em `frontend/chat.html`
adicione um botão `<button class="chip" data-mode="sua_chave">`.

## Rodando no seu computador

### Windows (CMD ou PowerShell)

1. Abra o CMD na pasta do projeto:
   ```cmd
   cd caminho\para\projeto_RAOS
   ```

2. Instale as dependências:
   ```cmd
   pip install -r requirements.txt
   ```

3. Rode o servidor:
   ```cmd
   python backend\server.py
   ```

4. Abra `http://localhost:5000` no navegador.

### Mac/Linux

```bash
cd projeto_RAOS
pip install -r requirements.txt
python backend/server.py
# abra http://localhost:5000
```

O `backend/server.py` já serve os arquivos de `frontend/` — não precisa
abrir o `index.html` direto, precisa passar pelo servidor Flask, senão o
chat não tem com quem falar.

### Erros comuns no Windows

**Erro: `ImportError: cannot import name 'genai' from 'google'`**

Se aparecer esse erro, o pacote `google-genai` não está instalou corretamente.
Tente:
```cmd
pip uninstall google google-genai
pip install google-genai python-dotenv flask
```

Ou crie um ambiente virtual limpo:
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python backend\server.py
```

## Publicando na web (Render, gratuito)

Isso coloca o site inteiro (página inicial + chat) num endereço público
tipo `https://uaifly.onrender.com`. É preciso de hospedagem de verdade
(não só um site estático) porque o backend em Python precisa rodar em
algum lugar pra guardar a chave do Gemini em segredo.

**1. Suba o projeto pro GitHub** (sem precisar usar git pelo terminal):
   - Crie uma conta em [github.com](https://github.com) se ainda não tiver.
   - Clique em **New repository**, dê um nome (ex: `uaifly`) e crie.
   - Na página do repositório, clique em **uploading an existing file** e
     arraste a pasta `uaifly-project` inteira (ou todos os arquivos dela).
   - Clique em **Commit changes**.

**2. Crie a conta no Render:**
   - Vá em [render.com](https://render.com) e crie uma conta gratuita
     (dá pra entrar direto com o GitHub, facilita o próximo passo).

**3. Crie o serviço a partir do `render.yaml`:**
   - No painel do Render, clique em **New +** → **Blueprint**.
   - Selecione o repositório que você acabou de criar.
   - O Render vai ler o `render.yaml` sozinho e já propor o serviço
     `uaifly` configurado (build e start command corretos).
   - Quando pedir a variável `GEMINI_API_KEY`, cole sua chave do Gemini.
   - Clique em **Apply** / **Create**.

   Se preferir configurar na mão em vez de usar o Blueprint: **New +** →
   **Web Service** → conecte o repositório → Build Command
   `pip install -r requirements.txt` → Start Command
   `gunicorn backend.server:app` → adicione a variável de ambiente
   `GEMINI_API_KEY` em **Environment**.

**4. Espere o deploy terminar** (alguns minutos na primeira vez) e abra
   o link que o Render mostra no topo da página do serviço — algo como
   `https://uaifly.onrender.com`. Esse link já serve a página inicial e
   o `/chat`.

**Sobre o plano gratuito:** depois de ~15 minutos sem uso, o site
"dorme" e a próxima visita demora uns 30–60 segundos pra acordar — é
normal, não é erro. Pra sempre ficar ativo é preciso um plano pago.

## Notas

- Modelo padrão: `gemini-3.5-flash` (troque com a variável `GEMINI_MODEL`).
- Se `GEMINI_API_KEY` não estiver definida, o `/api/chat` responde com
  erro 500 explicando o que falta — o resto do site carrega normalmente.
- Nunca coloque sua chave de verdade dentro de `render.yaml` nem de
  nenhum arquivo que vá pro GitHub — ela é digitada direto no painel do
  Render (ou fica só no seu `.env` local, que o `.gitignore` já ignora).
