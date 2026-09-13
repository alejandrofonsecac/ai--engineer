# Virtual Race Engineer — Contexto do Projeto

## Status e como trabalhar neste repositório

Este repositório está na fase de planejamento: ainda não há estrutura da aplicação
nem código de produto. **Não** introduza implementação, dependências,
infraestrutura ou funcionalidades especulativas, a menos que o usuário peça
explicitamente a próxima entrega.

Este é o documento canônico do projeto. Tanto `AGENTS.md` quanto `CLAUDE.md`
apontam para ele. Mantenha as instruções desses arquivos alinhadas caso este
documento seja alterado.

## Produto

O Virtual Race Engineer é um aplicativo desktop que ajuda pilotos de simuladores
a desenvolver setups de carro. Os simuladores inicialmente suportados são
**Assetto Corsa Competizione (ACC)** e **iRacing**. Assetto Corsa e outros
simuladores serão extensões futuras.

É um engenheiro virtual focado no desenvolvimento de setup, e não uma interface
de chat genérica. Ele não pilota o carro, não controla o simulador e não fornece
instruções de curva em tempo real durante uma volta.

O ciclo central do produto é:

```text
Feedback do piloto → diagnóstico técnico → recomendação de setup justificada
→ voltas de teste → novo feedback → setup refinado
```

O produto é bem-sucedido quando um piloto consegue criar uma sessão, importar um
setup, descrever o comportamento do carro, receber uma recomendação fundamentada,
aplicá-la como uma nova versão de setup, testá-la e continuar o ciclo de
refinamento.

## Princípios de engenharia

- Trate o feedback como um problema de diagnóstico, não como uma associação
  direta entre sintoma e ajuste.
- Considere o contexto completo: simulador, carro, características da pista,
  objetivo da sessão, setup atual, alterações anteriores, resultado dos testes
  e feedback do piloto.
- Explique benefícios esperados e trade-offs. Nunca esconda um efeito negativo
  provável.
- Prefira a menor intervenção útil. Uma recomendação propõe **de 1 a 5**
  parâmetros; cinco é o limite absoluto, não uma meta.
- Quando as evidências forem ambíguas, faça uma pergunta de esclarecimento em
  vez de adivinhar.
- Nunca recomende valores fora dos limites do simulador ou do carro.
- Nunca sobrescreva silenciosamente um setup importado ou existente. Aplicar uma
  recomendação sempre cria uma versão nova e imutável do setup.
- O LLM é uma camada de interpretação e comunicação. Ele não é a única fonte de
  conhecimento técnico e não pode estar acoplado a um modelo específico.

### Níveis de intervenção

| Nível | Parâmetros | Quando usar |
| --- | ---: | --- |
| BAIXO | 1–2 | O diagnóstico é incerto ou a correção é pontual. |
| MÉDIO | 2–3 | O problema está razoavelmente identificado. |
| ALTO | 4–5 | É necessária uma mudança de direção de setup coordenada e claramente justificada. |

Várias alterações precisam ter o mesmo objetivo, evitar contradições e efeitos
colaterais combinados excessivos, e ainda permitir que o teste posterior seja
interpretável.

## Escopo do MVP

O primeiro MVP funcional contempla:

1. Criar uma sessão para ACC ou iRacing com simulador, carro, pista, tipo de
   sessão e setup importado opcional.
2. Fazer o parse de um arquivo de setup do simulador para uma representação
   interna normalizada.
3. Oferecer chat de texto com o engenheiro; a entrada de voz é transcrita para
   texto antes de entrar no mesmo fluxo de chat.
4. Gerar recomendações estruturadas e sensíveis ao contexto, com explicação,
   trade-offs e plano de teste.
5. Aplicar recomendações como alterações de setup versionadas.
6. Exibir valores do setup, histórico e diferenças entre versões.
7. Exibir claramente os estados de disponibilidade da IA local/Ollama.

Não adicione telemetria automática, comparação de voltas, análise de pneus, voz
do engenheiro, perfis de piloto ou preferências aprendidas enquanto esse ciclo
não estiver sólido. Telemetria será uma fonte de contexto futura, e não o
propósito inicial do produto.

## Fluxo da sessão

1. O piloto seleciona **Simulador → Carro → Pista → Tipo de sessão**.
2. O aplicativo armazena essas informações como contexto permanente da sessão.
3. O piloto pode importar o setup atual.
4. Antes de alterações relevantes, o engenheiro pede voltas consistentes de base
   (normalmente 5; cerca de 5 a 10 antes da primeira alteração significativa).
5. O piloto descreve o comportamento naturalmente, como instabilidade na
   entrada, sob aceleração, sobre zebras ou em determinada faixa de velocidade.
6. O engenheiro diagnostica, solicita dados ausentes quando necessário, ou
   propõe de 1 a 5 alterações limitadas.
7. Após aprovação explícita do piloto, cria-se uma nova versão de setup e as
   alterações ficam registradas.
8. O engenheiro prescreve um teste focado: em geral 3 a 5 voltas para pequenas
   mudanças e 5 a 10 para mudanças mais amplas.
9. O novo feedback é comparado ao resultado pretendido e ao histórico completo
   da sessão.

Sempre que possível, identifique a fase relevante: frenagem, entrada de curva,
meio de curva, ápice, saída de curva, aceleração, comportamento sobre zebra,
estabilidade em baixa ou em alta velocidade.

## Contrato da recomendação

As respostas do engenheiro devem ser concisas e operacionais, sem teoria
excessiva. Quando uma recomendação for apropriada, estruture-a assim:

1. **Diagnóstico** — problema provável e grau de confiança/incerteza.
2. **Alterações recomendadas** — até cinco parâmetros nomeados, com valores
   anterior e novo permitidos.
3. **Por quê** — mecanismo que conecta cada alteração ao problema relatado.
4. **Trade-offs** — efeitos adversos plausíveis e consequências relevantes para
   a pista.
5. **Plano de teste** — quantidade de voltas, trechos/condições a observar e o
   que comparar.

Exemplo de raciocínio: para instabilidade traseira em alta velocidade, aumentar
um clique de asa traseira pode melhorar a estabilidade aerodinâmica traseira,
mas adiciona arrasto e pode reduzir a velocidade final. Em uma pista cuja reta é
importante, esse trade-off precisa aparecer na resposta. Da mesma forma, baixar
a altura do carro para melhorar a aerodinâmica exige considerar piso irregular,
zebras, compressões, mudanças de elevação e risco de tocar o assoalho.

Se o piloto disser que a traseira está solta, determine se isso ocorre antes ou
depois de aplicar o acelerador quando essa diferença afetar o diagnóstico. Não
afirme certeza quando as evidências forem incompletas.

## Modelo de domínio

As entidades conceituais são:

- `Session`: simulador, carro, pista, tipo de sessão, versão atual do setup e
  histórico da conversa.
- `Setup`: valores normalizados por categoria e limites específicos do
  simulador.
- `SetupVersion`: snapshot imutável derivado de um setup importado ou de uma
  recomendação aceita.
- `SetupChange`: parâmetro, valor anterior, novo valor, justificativa e versão.
- `DriverFeedback`: texto/transcrição brutos e sinais estruturados quando
  disponíveis.
- `EngineerRecommendation`: diagnóstico, justificativa, alterações, riscos,
  plano de teste e estado de aceitação.
- `TestResult`: feedback após um teste definido e comparação com o objetivo.
- `CarProfile`, `TrackProfile` e `SetupKnowledge`: dados técnicos
  versionados.

Use uma estrutura de setup normalizada depois do parse; o LLM nunca deve
interpretar diretamente arquivos arbitrários de simuladores. Exemplo conceitual:

```json
{
  "simulator": "ACC",
  "car": "Porsche 992 GT3 R",
  "track": "Nordschleife",
  "setup": {
    "tyres": {},
    "electronics": {},
    "mechanical_grip": {},
    "dampers": {},
    "aero": {},
    "alignment": {}
  }
}
```

Os adaptadores de simulador são responsáveis por parse de arquivos, nomes de
parâmetros, intervalos válidos e restrições específicas. A fronteira inicial de
adaptadores inclui `ACCSetupParser` e `IRacingSetupParser`;
`ACSetupParser` e parsers adicionais serão extensões futuras sob a mesma
interface compartilhada.

## Direção técnica

A stack pretendida é uma orientação para a implementação futura, não uma
solicitação para criá-la agora:

| Camada | Tecnologia planejada |
| --- | --- |
| Shell desktop | Tauri |
| Frontend | React, TypeScript estrito, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI, Pydantic |
| Persistência | SQLite inicialmente |
| LLM local | Ollama por meio de uma abstração de provider |
| Speech-to-text | faster-whisper |
| Base de conhecimento | JSON/YAML versionados inicialmente |
| Comunicação | HTTP/REST inicialmente |

Mantenha a lógica de domínio e de negócio fora de componentes React e handlers
de rotas FastAPI. As rotas validam requests, chamam services e retornam
responses. Use contratos Pydantic nas fronteiras do backend.

Serviços dependentes de provider devem usar interfaces. Conceitualmente, um
`LLMProvider` terá hoje uma implementação `OllamaProvider` e poderá ganhar
OpenAI, Anthropic, Gemini ou outros no futuro, sem mudar a lógica do engenheiro.

A voz utiliza um único caminho:

```text
Microfone → áudio gravado → faster-whisper → texto editável → EngineChatService
Texto digitado ───────────────────────────────────────────────→ EngineChatService
```

Direções prováveis para a API — não é obrigatório implementar tudo de uma vez:

```text
POST /sessions
GET  /sessions/:id
POST /sessions/:id/setup
POST /sessions/:id/messages
POST /sessions/:id/feedback
GET  /sessions/:id/setup/history
POST /speech/transcribe
```

## Arquitetura de inteligência e conhecimento

Sempre que possível, use uma camada determinística de relevância. Ela seleciona
o conhecimento técnico antes de o LLM raciocinar sobre ele. Por exemplo,
sobresterço em baixa velocidade ao acelerar pode priorizar conhecimento sobre
diferencial, suspensão traseira, toe traseiro, controle de tração e condição dos
pneus traseiros.

`EngineerContextBuilder` é uma fronteira fundamental. Ele monta um prompt
limitado a partir de:

```text
simulador + perfil do carro + perfil da pista + tipo de sessão + setup atual
+ conhecimento técnico relevante + histórico da sessão/versões + feedback do piloto
```

Não dependa de uma grande tabela de receitas por carro e pista. Modele três
camadas:

1. Conhecimento físico geral de setup — causa, efeito e trade-offs por parâmetro.
2. Características da pista — irregularidade da superfície, importância das
   zebras, elevação, trechos de alta, necessidade de conformidade mecânica e
   importância de reta.
3. Características do carro — posição do motor, sensibilidade aerodinâmica,
   tração e tendências de equilíbrio de base.

Os arquivos de conhecimento devem codificar os dois sentidos e as consequências.
Por exemplo, aumentar a asa traseira pode elevar carga aerodinâmica e
estabilidade traseira em alta, ao mesmo tempo em que aumenta arrasto e reduz
velocidade final.

Evite prematuramente bancos vetoriais, treinamento de modelo, orquestração no
estilo LangChain ou frameworks complexos de agentes. Comece com JSON/YAML
versionados e services claros.

## Direção de UX e visual

Este é um aplicativo desktop na classe de 1440×900: software profissional de
engenharia de corrida com a clareza de ferramentas modernas de IA, sem aparência
de jogo chamativo.

A imagem de referência da Home estabelece esta linguagem visual:

- Fundo quase preto e painéis grafite de baixo contraste.
- Sidebar estreita de ícones à esquerda.
- Texto quase branco e texto secundário em cinza frio e discreto.
- Um único destaque vermelho, usado com moderação para ações primárias, estado
  ativo, avisos e alterações de setup; sem neon saturado ou gradientes
  decorativos.
- Cards compactos, com cantos de pouco a moderadamente arredondados, bordas
  sutis, sombras leves, alinhamento preciso e bastante espaço vazio.
- Fonte sans serif limpa como Inter, Geist ou SF Pro; rótulos técnicos em caixa
  alta podem usar espaçamento entre letras.

As seis telas prioritárias são:

1. **Home / Sessões** — boas-vindas, cards de sessões recentes, continuação e
   ação para criar sessão.
2. **Nova Sessão** — seletores de simulador/carro/pista, tipo de sessão, importação
   de setup e ação de início.
3. **Chat do Engenheiro** — tela principal. O chat ocupa aproximadamente 75% e
   uma sidebar compacta de contexto/sessão ocupa 25%. Cards de recomendação são
   o elemento dominante.
4. **Setup Atual** — categorias compactas e legíveis para pneus, eletrônica,
   aderência mecânica, amortecedores, aerodinâmica e alinhamento; mostre
   discretamente as alterações recentes de antes → depois.
5. **Histórico de Setups** — timeline vertical de versões com feedback e
   controles de restauração.
6. **Comparar Setups** — tabela clara de diferenças por parâmetro e toggle para
   exibir somente parâmetros alterados.

Estados obrigatórios da UI incluem: IA local analisando, Ollama offline com
tentativa de reconexão, nenhum setup importado (a assistência continua possível,
mas menos precisa), setup carregado, voz ouvindo e transcrição editável antes do
envio.

Não transforme o MVP em um dashboard de telemetria. A recomendação do
engenheiro — diagnóstico, alterações, motivo, riscos e plano de teste — deve
sempre ser o foco visual e de produto.

## Proteções para trabalhos futuros

- Comece pelo menor recorte vertical que valide o ciclo principal.
- Proponha a próxima etapa mínima de implementação antes de adicionar
  arquitetura ampla.
- Preserve os dados de origem e o histórico do setup; restaurar deve ser uma
  transição explícita de estado, nunca uma exclusão de histórico.
- Mantenha o estado da sessão no frontend coeso, sem espalhá-lo por componentes
  não relacionados.
- Torne estados de falha e offline explícitos. A disponibilidade da IA local
  nunca deve parecer bem-sucedida quando não estiver.
- Use componentes reutilizáveis e um design system consistente; evite excesso de
  dashboards, gráficos pesados, divisores, brilho ou balões de chat arredondados.
- Priorize restrições válidas de setup e explicação dos trade-offs, não apenas
  fluência superficial da IA.

## Deliberadamente fora de escopo por enquanto

- Ingestão automática ou em tempo real de telemetria.
- Orientação automática de pilotagem por volta.
- Treinamento ou fine-tuning de modelos.
- Banco vetorial ou infraestrutura RAG.
- Dependência de providers cloud como caminho principal.
- Suporte além de ACC e iRacing.
- Receitas de setup pré-definidas por combinação individual de carro e pista.
