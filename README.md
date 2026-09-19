# Virtual Race Engineer

O Virtual Race Engineer foi desenvolvido com o intuito de ser uma solução fácil
para pilotos virtuais criarem e refinarem seus setups, **sem precisar conhecer
detalhadamente cada ajuste do carro**.

A proposta é permitir que o piloto descreva o que sente ao dirigir — por exemplo,
“a traseira escapa quando acelero na saída da curva” — e receba ajuda para entender
o problema, testar soluções e evoluir o setup. O engenheiro deve explicar os
motivos e os efeitos de cada mudança em uma linguagem acessível. O foco inicial
é Assetto Corsa Competizione (ACC) e iRacing.

## Estado atual

O projeto está em desenvolvimento. Atualmente, é possível criar uma sessão,
informar simulador, carro e pista, conversar com a IA local e retomar a conversa
salva. O chat analisa sintomas, pede informações e orienta testes de observação.

O setup inicial do ACC pode ser importado em JSON ao criar uma sessão. O sistema
preserva o arquivo original no banco e salva uma representação normalizada como
a primeira versão. O engenheiro pode recomendar ajustes direcionais com base nos
valores importados, explicando benefícios, efeitos negativos e um plano de teste.
**A aplicação de ajustes de setup ainda não está disponível.** Novos valores
numéricos permanecem bloqueados até existirem limites validados por carro e
simulador. Importação de iRacing, exportação de setups, voz e
telemetria ainda não estão conectadas. As telas demonstrativas de setup e
comparação não representam resultados da IA local.

O objetivo futuro é completar o ciclo: relato do piloto → diagnóstico → mudanças
explicadas → aprovação do piloto → nova versão do setup → voltas de teste.
Um setup existente nunca deve ser sobrescrito silenciosamente.

## Como o projeto funciona

Nesta etapa, a interface abre no navegador e os serviços rodam no computador:

```text
Interface React → Backend FastAPI → Ollama → Modelo Qwen 2.5 3B
                         ↓
                       SQLite
```

Ollama é o programa que executa o modelo. Qwen e Llama são famílias diferentes;
o modelo configurado neste projeto é **qwen2.5:3b**. Não é necessário treinar um
modelo, criar um Modelfile ou configurar uma chave de API de IA em nuvem.
O empacotamento como aplicativo desktop com Tauri é uma etapa futura.

## Requisitos

Este passo a passo usa **Windows e PowerShell**, inclusive o terminal do VS Code.

| Requisito | Para que serve / versão |
| --- | --- |
| Python | 3.11 ou superior; o ambiente local de referência usa 3.12 |
| uv | Instala e gerencia as dependências do backend |
| Node.js e npm | Use Node.js 22 com npm para executar o frontend |
| Ollama | Executa a IA local |
| Modelo qwen2.5:3b | Baixado pelo Ollama no primeiro preparo |
| Navegador | Acessa a interface local |
| Internet no preparo inicial | Baixa ferramentas, dependências e modelo |
| Git (opcional) | Para clonar e atualizar o repositório; também é possível baixar o ZIP |

Instale as ferramentas pelas páginas oficiais:
[Python](https://www.python.org/downloads/),
[uv](https://docs.astral.sh/uv/getting-started/installation/),
[Node.js](https://nodejs.org/en/download) e
[Ollama para Windows](https://ollama.com/download/windows).
Após instalar, abra um novo terminal para que os comandos sejam reconhecidos.

Confira a instalação:

```powershell
python --version
uv --version
node --version
npm --version
ollama --version
```

Se o Python estiver disponível pelo launcher do Windows, use `py --version`
para conferir. O uv também pode instalar Python 3.12 com `uv python install 3.12`.

Ainda não há requisitos mínimos de RAM, GPU e armazenamento validados para o
projeto. Reserve espaço para as dependências e os pesos do modelo e memória livre
para executar a IA junto com o simulador. A configuração de referência é um
i3-10100F com RX 6600; isso não é um requisito mínimo nem uma garantia de
aceleração pela GPU. A primeira resposta pode demorar mais para carregar o modelo.

Depois de instalar as dependências e baixar o modelo, o fluxo de chat usa os
serviços locais. Não é necessário manter o simulador aberto para testar o chat.

## Primeiro preparo

Baixe ou clone este repositório e abra a pasta no VS Code. A **raiz do projeto**
é a pasta que contém este README, `backend` e `frontend`.
Os terminais abaixo começam nessa pasta, salvo indicação contrária.

### 1. Preparar o Ollama

Abra **Ollama** pelo menu Iniciar. Em um PowerShell, execute:

```powershell
ollama pull qwen2.5:3b
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

O modelo deve aparecer na lista e a última chamada deve retornar os modelos
disponíveis. Se já estiver instalado, não é preciso baixá-lo novamente.
Se o aplicativo não iniciar o servidor, execute em um terminal separado:

```powershell
ollama serve
```

Mantenha esse terminal aberto. Se a porta 11434 já estiver ocupada pelo Ollama,
use a instância existente. Não é necessário deixar `ollama run` aberto para
usar o projeto.

### 2. Preparar e iniciar o backend

Em um terminal na raiz do projeto:

```powershell
cd backend
uv sync --extra dev --locked
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O uv cria o ambiente `.venv` e instala as dependências fixadas em `uv.lock`.
Não é necessário ativar o ambiente virtual nem alterar a política do PowerShell.
Se já estiver na pasta `backend`, não repita `cd backend`.

Deixe o terminal aberto e confira:

- [Saúde do backend](http://127.0.0.1:8000/api/v1/health).
- [Disponibilidade do Ollama e do modelo](http://127.0.0.1:8000/api/v1/health/llm).
- [Documentação interativa da API](http://127.0.0.1:8000/docs).

### 3. Preparar e iniciar o frontend

Abra **outro terminal**, na raiz do projeto:

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

`npm ci` instala as dependências registradas em `package-lock.json`.
Deixe o terminal aberto e acesse **http://127.0.0.1:5173**.
O uso de `--strictPort` impede que o frontend mude silenciosamente para uma porta
não permitida pelo backend.

### 4. Usar o chat

1. Clique em **Nova sessão**.
2. Selecione ACC ou iRacing e informe carro, pista e tipo de sessão.
3. Descreva o comportamento do carro, incluindo onde e quando o problema ocorre.
4. Aguarde a resposta e siga as perguntas ou os testes de observação sugeridos.
5. Use **Retomar minha sessão local** para recuperar a última sessão deste navegador.

Exemplo: “No ACC, a traseira do carro escapa na saída das curvas lentas quando
começo a acelerar. O que devo observar para entender a causa?”

## Como ligar nas próximas vezes

Com o preparo concluído, abra o **Ollama** no menu Iniciar e inicie estes dois
terminais a partir da raiz do projeto. Não é necessário reinstalar as dependências
a cada uso.

**Terminal 1 — backend:**

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend:**

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abra **http://127.0.0.1:5173**. Para parar, pressione **Ctrl+C** em cada terminal.
Fechar a aba do navegador não encerra os serviços. Se iniciou o Ollama com
`ollama serve`, encerre esse terminal com Ctrl+C; se abriu pelo aplicativo,
encerre-o pelo ícone na bandeja do Windows quando desejar.

## Configuração e dados locais

O backend lê `backend/.env`. A configuração inicial está em
[`backend/.env.example`](backend/.env.example):

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `VRE_DATABASE_PATH` | `data/virtual_race_engineer.db` | Banco SQLite local |
| `VRE_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Endereço do Ollama |
| `VRE_OLLAMA_MODEL` | `qwen2.5:3b` | Modelo usado no chat |
| `VRE_OLLAMA_TEMPERATURE` | `0.2` | Variação das respostas |
| `VRE_OLLAMA_NUM_CTX` | `4096` | Janela de contexto em tokens |
| `VRE_OLLAMA_NUM_PREDICT` | `700` | Limite de tokens da resposta estruturada |
| `VRE_OLLAMA_KEEP_ALIVE` | `5m` | Tempo para manter o modelo carregado |
| `VRE_OLLAMA_TIMEOUT_SECONDS` | `180` | Tempo máximo de espera pela IA |

Reinicie o backend após editar `.env`. O modelo e o prompt são configurados no
backend; o frontend acessa apenas a API FastAPI.

O frontend usa `http://127.0.0.1:8000/api/v1` por padrão. Se precisar mudar esse
endereço, copie `frontend/.env.example` para `frontend/.env`, ajuste
`VITE_API_BASE_URL` e reinicie o frontend. As origens permitidas pelo backend são
localhost e 127.0.0.1 na porta 5173; outra porta exige ajustar o CORS no backend.

As sessões ficam no SQLite em `backend/data/virtual_race_engineer.db`, criado
na primeira inicialização. Os pesos do modelo são gerenciados pelo Ollama fora
do repositório, normalmente em `%USERPROFILE%\.ollama\models`.
Não copie pesos para o repositório, GitHub ou OneDrive.

A API é local e não possui autenticação. Mantenha os serviços em `127.0.0.1`;
não é necessário abrir portas no roteador.

## Problemas comuns

| Problema | O que conferir |
| --- | --- |
| Comando `uv`, `node`, `npm` ou `ollama` não reconhecido | Instale a ferramenta e reabra o terminal; confira se ela está no PATH. |
| PowerShell bloqueia `npm.ps1` | Use `npm.cmd ci` e `npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort`. |
| `.venv\\Scripts\\python.exe` não encontrado | Confira se está em `backend` e execute `uv sync --extra dev --locked`. |
| Ollama offline / erro 503 | Abra o Ollama e confira `ollama list` e o endpoint `/api/v1/health/llm`. |
| Modelo ausente | Execute `ollama pull qwen2.5:3b`. |
| Porta 11434 ocupada | Verifique se o Ollama já está rodando; não inicie outra instância. |
| Porta 8000 ou 5173 ocupada | Encerre a instância anterior do projeto antes de iniciar outra. |
| Interface abre, mas não conversa | Confira backend na porta 8000, Ollama na 11434 e frontend na 5173. |
| Resposta lenta / erro 504 | O primeiro carregamento pode demorar; confira a carga do computador e os parâmetros do modelo. |
| Erro 409 | Já existe uma geração em andamento; aguarde a conclusão. |
| Erro 502 | A resposta foi inválida, truncada ou propôs um ajuste não validado; veja os detalhes no terminal do backend. |

Se o navegador atingir o tempo limite, recarregue a conversa antes de reenviar:
o backend pode ainda concluir a solicitação. Durante uma resposta, `ollama ps`
mostra a distribuição de execução entre CPU e GPU.

## Verificações de desenvolvimento

Na pasta `backend`, execute os testes automatizados, que usam IA simulada:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Para testar o fluxo com o Ollama real e banco temporário, com o modelo instalado
e o Ollama ligado (pode levar alguns minutos):

```powershell
.\.venv\Scripts\python.exe -m scripts.check_local
```

Na pasta `frontend`, valide a compilação:

```powershell
npm run build
```

## Documentação

- [Guia técnico do backend](backend/README.md): API, desempenho e diagnóstico.
- [Contexto canônico do projeto](PROJECT_CONTEXT.md): produto, arquitetura, UX e proteções de setup.
