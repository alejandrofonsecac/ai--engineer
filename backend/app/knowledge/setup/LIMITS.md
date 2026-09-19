# Limites de referência e recomendações em cliques

O JSON de setup armazena valores atuais. Ele não informa mínimo, máximo, passo,
unidade nem versão do ACC. Um valor pequeno não prova que o ajuste está no mínimo;
uma coleção de setups também não estabelece os limites permitidos pelo jogo.

`limits.json` é um catálogo revisado, separado dos arquivos enviados e do LLM.
O modelo escolhe parâmetro e direção. O backend confere carro, versão configurada,
BoP, valor atual e passo, e calcula **um clique por teste**. Os textos explicativos
e os efeitos por direção são controlados pelo backend. Sem perfil correspondente,
não há número-alvo. Uma nova proposta não modifica o setup salvo.

## Cobertura atual

Perfil de uso: `ford_mustang_gt3`, ACC `1.10.3`, `trackBopType=35` do arquivo
fornecido pelo usuário. `VRE_ACC_GAME_VERSION=1.10.3` seleciona a versão declarada
pelo usuário; a aplicação não detecta a versão do jogo automaticamente.

| Parâmetro | Caminho no JSON ACC | Mínimo | Máximo | Passo | Valor no menu |
| --- | --- | ---: | ---: | ---: | --- |
| TC1 | `basicSetup.electronics.tC1` | 0 | 11 | 1 | Igual ao JSON |
| Barra traseira | `advancedSetup.mechanicalBalance.aRBRear` | 0 | 9 | 1 | Igual ao JSON |
| Asa traseira | `advancedSetup.aeroBalance.rearWing` | 0 | 8 | 1 | Igual ao JSON |

Esses intervalos vêm do catálogo comunitário do Simulator Controller. Não são
documentação oficial da Kunos nem foram medidos nesta máquina dentro do jogo.
A vinculação à versão 1.10.3 é o escopo de uso declarado nesta integração, não
uma certificação da versão pela fonte. Não generalizar para outros carros,
parâmetros, BoPs ou versões; se o menu divergir, revisar o perfil antes de usá-lo.

Fontes consultadas em 19/09/2026, fixadas por revisão:

- [Definições do Mustang, Simulator Controller](https://github.com/SeriousOldMan/Simulator-Controller/blob/2dc2f8e724eb3d876f5c7b00cbc7a7e727feee6c/Resources/Garage/Definitions/Cars/Assetto%20Corsa%20Competizione.Ford%20Mustang%20GT3.ini): intervalos.
- [Mapeamento dos campos ACC](https://github.com/SeriousOldMan/Simulator-Controller/blob/2dc2f8e724eb3d876f5c7b00cbc7a7e727feee6c/Resources/Garage/Definitions/Assetto%20Corsa%20Competizione.ini): parâmetros para caminhos JSON.
- [Tratamento dos cliques](https://github.com/SeriousOldMan/Simulator-Controller/blob/2dc2f8e724eb3d876f5c7b00cbc7a7e727feee6c/Sources/Garage/Setup%20Workbench.ahk): significado dos argumentos de `ClicksHandler` e `IntegerHandler`.
- [Conversões do Mustang, Race Element](https://github.com/RiddleTime/Race-Element/blob/00fe775fc11ecf980a6fc35fe5797439db8f6235/Race_Element.Data.ACC/SetupParser/Cars/GT3/FordMustangGT3.cs): confirmação de asa e barras sem offset. Outros parâmetros usam transformações diferentes.

As direções iniciais de TC e barra traseira para investigar perda sob aceleração
também são coerentes com os [testes do Mustang de Nils Naujoks](https://popometer.io/acc/setups/7393).
São hipóteses de teste: patinagem e excesso de intervenção do TC exigem decisões
diferentes. Aumentar TC pode ajudar a conter patinagem, mas também cortar potência.

## Como ampliar

Adicionar somente dados revisados com fonte, identificação exata do carro,
versão, BoP, mínimo/máximo bruto, passo bruto e offset de exibição. O formato
atual atende controles inteiros com offset; parâmetros com escalas físicas ou
conversões não lineares precisam de um adaptador próprio antes de serem liberados.
O JSON importado e a resposta da IA nunca podem registrar ou alterar limites.

Para avaliar qualidade, testar também relatos de frenagem, negação da perda de
traseira, TC cortando demais, ausência de setup e ajustes já no extremo. Os
exemplos no prompt ensinam formato e raciocínio durante a chamada; não constituem
fine-tuning dos pesos do Qwen.
