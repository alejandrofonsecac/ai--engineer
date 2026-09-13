# Backend — Virtual Race Engineer

Backend FastAPI do engenheiro virtual. Ele persiste sessões e histórico em SQLite
e conversa com um LLM local por meio da API do Ollama. Nenhuma chave de API ou
serviço em nuvem é necessário.

## Pré-requisitos

- Python 3.11 ou superior
- [Ollama para Windows](https://ollama.com/download/windows)
- Um modelo Llama baixado no Ollama, recomendado inicialmente: `llama3.2`

## Configuração rápida no Windows

Abra um novo PowerShell na pasta `backend`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
ollama run llama3.2
```

O último comando baixa o modelo na primeira execução e inicia uma conversa de
teste. Depois dele, o Ollama continua expondo a API local em
`http://127.0.0.1:11434`. Encerre a conversa com `/bye` ou `Ctrl+C`.

Em outro terminal, com o ambiente virtual ativado:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Confira `http://127.0.0.1:8000/docs` e
`http://127.0.0.1:8000/api/v1/health/llm`.

## Endpoints iniciais

- `GET /api/v1/health`
- `GET /api/v1/health/llm`
- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/sessions/{session_id}/messages`
- `GET /api/v1/sessions/{session_id}/setup/history`

A resposta do chat usa um contrato estruturado: diagnóstico, até cinco
alterações, motivos, trade-offs e plano de teste. O backend valida o máximo de
cinco mudanças e não aplica alterações automaticamente.

## Observação sobre setup importado

O endpoint de importação de arquivos específicos de ACC/iRacing ainda não foi
implementado. Nesta primeira etapa, a API aceita um snapshot de setup
normalizado ao criar a sessão. Os parsers específicos serão a próxima camada.
