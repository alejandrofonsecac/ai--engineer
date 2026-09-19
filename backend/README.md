# Backend e IA local — Virtual Race Engineer

Para conhecer o objetivo do projeto, os requisitos e o passo a passo completo
de instalação e execução do frontend, backend e Ollama, leia o
[README principal](../README.md). Este guia detalha a operação do backend.

O modelo padrão é **qwen2.5:3b**, conforme os testes locais do usuário.
Ollama é o programa que executa os modelos; Qwen e Llama são famílias de modelos
diferentes. Este projeto usa Qwen pelo Ollama, sem precisar treinar ou criar
outro modelo.

## Onde fica cada coisa

- Ollama e os pesos ficam fora do repositório, gerenciados pelo Ollama.
- Por padrão, os modelos ficam em `%USERPROFILE%\.ollama\models`.
  Não copie esses arquivos para GitHub ou OneDrive.
- `backend/.env`: endereço, nome e parâmetros de execução; ignorado pelo Git.
- `backend/.env.example`: configuração de referência versionada.
- `app/ai/prompts/engineer_system_prompt.py`: personalidade e regras do engenheiro.
- `app/ai/context_builder.py`: sessão, setup, conhecimento selecionado e histórico.
- `app/ai/provider.py`: interface e erros independentes de fornecedor.
- `app/ai/ollama_provider.py`: somente transporte HTTP para Ollama.
- `app/services/engineer_service.py`: coordenação e validação da conversa.
- `app/knowledge/`: base ilustrativa inicial, ainda sem catálogo de limites validado.
- `backend/data/virtual_race_engineer.db`: banco local criado na primeira inicialização.

Não é necessário criar um Modelfile: os parâmetros são enviados em cada chamada
e o prompt fica versionado no backend. Não altere o modelo por meio do frontend.

## Executar no seu Windows

Ollama e Qwen 3B já foram detectados neste computador. Abra o aplicativo Ollama
pelo menu Iniciar e confira em um PowerShell:

```powershell
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Se `qwen2.5:3b` não estiver listado, execute `ollama pull qwen2.5:3b`.
Não precisa deixar uma conversa `ollama run` aberta. Se o aplicativo não iniciar
o servidor, execute `ollama serve` em um terminal separado. Não execute outro
servidor se a porta 11434 já estiver ocupada pelo Ollama.

Na raiz do projeto, para preparar ou atualizar o backend:

```powershell
cd backend
uv sync --extra dev --locked
# Somente se .env ainda não existir:
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Não é necessário ativar o ambiente virtual nem alterar a política do PowerShell.
O arquivo `uv.lock` fixa as dependências. O Python precisa ser 3.11 ou superior;
o ambiente preparado neste computador usa 3.12.

Em outro terminal, a partir da raiz:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Abra o endereço exibido pelo Vite (normalmente `http://127.0.0.1:5173`).
Clique em **Nova sessão**, informe ACC ou iRacing, carro e pista e envie seu relato.
A aplicação usa `React → FastAPI → EngineerService → ContextBuilder → Ollama → Qwen`.
**Retomar minha sessão local** recupera a última sessão deste navegador.
As telas antigas de setup/comparação e os exemplos de sessões estão identificados
como demonstração e não são resultados da IA local.

O frontend usa `http://127.0.0.1:8000/api/v1`. Para mudar, copie
`frontend/.env.example` para `frontend/.env`, edite `VITE_API_BASE_URL` e
reinicie o Vite. As origens permitidas são localhost/127.0.0.1 na porta 5173;
mudar a porta exige ajustar também o CORS do backend.

## Configuração e desempenho

Os padrões são `temperature=0.2`, `num_ctx=4096`, `num_predict=700`,
`keep_alive=5m`, `stream=False` e timeout de 180 segundos.
O modelo de 3B foi escolhido pelos testes relatados pelo usuário: cerca de
5,84 tokens/s, contra 1,82 tokens/s no 7B. Não são benchmarks deste backend.
A primeira resposta pode levar mais tempo para carregar o modelo e avaliar o prompt.

O histórico enviado ao LLM é curto: até quatro mensagens anteriores, limitadas
a 1.600 caracteres. Setup excessivamente grande é omitido explicitamente.
A interface envia até 1.200 caracteres por mensagem. Há uma geração por vez
nesta instância do backend; mantenha um único processo/worker no desenvolvimento.

O limite de 700 tokens comporta diagnóstico, efeitos positivos e negativos e o
plano de teste. Reduzi-lo pode truncar o JSON estruturado.
Para liberar memória após cada resposta, use `VRE_OLLAMA_KEEP_ALIVE=0`
(a próxima chamada precisará recarregar o modelo). Reinicie o backend após editar
o arquivo .env. Um timeout HTTP não garante que o Ollama interrompeu a geração.

Execute `ollama ps` durante uma geração para ver a distribuição CPU/GPU.
Não há garantia de aceleração pela RX 6600 nesta configuração. Avalie latência
e FPS com ACC aberto antes de aumentar contexto ou modelo.

## Diagnóstico e testes

- `GET http://127.0.0.1:8000/api/v1/health`: backend.
- `GET http://127.0.0.1:8000/api/v1/health/llm`: Ollama e modelo instalado.
  Disponibilidade não mede velocidade nem confirma carregamento na GPU.
- `http://127.0.0.1:8000/docs`: documentação interativa da API.
- `POST /api/v1/sessions`: criar sessão, com upload opcional de setup JSON do ACC.
- `GET /api/v1/sessions/{id}`: recuperar contexto.
- `GET /api/v1/sessions/{id}/messages`: últimas 100 mensagens.
- `POST /api/v1/sessions/{id}/messages`: corpo `{"content":"seu relato"}`.
- `GET /api/v1/sessions/{id}/setup/history`: snapshot inicial.

Na pasta backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.check_local
```

O primeiro comando usa respostas simuladas para testes automatizados.
O segundo usa o Ollama real e verifica criação, resposta e persistência em banco
temporário; requer dependências de desenvolvimento. Pode levar alguns minutos.

Erros: 409 = geração em andamento; 503 = Ollama/modelo indisponível;
504 = tempo excedido; 502 = saída inválida, truncada ou ajuste não validado.
Falhas não criam mensagens órfãs. Em timeout no navegador, recarregue a conversa
antes de reenviar, pois o backend pode ainda concluir a solicitação.

## Limites desta etapa

O chat real analisa sintomas, pede informações e orienta observações.
O backend conserva o contrato estruturado e permite recomendações direcionais
com até cinco mudanças, valor atual, benefício e possível efeito negativo.
Valores numéricos novos e aplicação automática continuam bloqueados enquanto
não houver limites validados por carro/simulador. O setup JSON inicial do ACC pode ser importado ao
criar a sessão. O arquivo original e uma representação normalizada ficam
preservados no SQLite como a versão 1. Importação de iRacing,
aplicação/exportação de alterações, voz e telemetria ainda não estão conectadas.
Nenhum arquivo de setup é modificado por este fluxo.

A API é local, sem autenticação; mantenha os serviços em loopback.
Não é preciso abrir portas no roteador.

Referências oficiais: [API chat](https://docs.ollama.com/api/chat),
[parâmetros](https://docs.ollama.com/modelfile),
[FAQ, memória e armazenamento](https://docs.ollama.com/faq).
