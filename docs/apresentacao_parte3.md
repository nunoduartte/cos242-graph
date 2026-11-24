# Apresentação – Parte 3: roteiro (até 8 minutos)

Arquivo: `docs/apresentacao_parte3.pptx` (12 slides, 16:9, mesma identidade visual da Parte 2), gerado por
`~/.venvs/cos242-accel/bin/python docs/build_presentation.py`. Todos os números dos slides são lidos de
`results/part3/`; as falas abaixo são as notas do apresentador de cada slide.

| # | Slide | Quem | Tempo |
|---|---|---|---|
| 1 | Capa | Nuno | 0:15 |
| 2 | O pedido e os dados | Nuno | 0:30 |
| 3 | Arquitetura: direção na representação | Nuno | 0:40 |
| 4 | Bellman-Ford até um destino | Nuno | 0:45 |
| 5 | Ciclos negativos (W_1) | Nuno | 0:40 |
| 6 | Floyd-Warshall: memória e aceleração | Nuno | 0:50 |
| 7 | Estudo 1 | Nicolas | 0:35 |
| 8 | Estudo 2 | Nicolas | 0:35 |
| 9 | Estudo 3 | Nicolas | 0:40 |
| 10 | Estudo 4: subgrafos do W_2 | Nicolas | 0:40 |
| 11 | Estudo 4: grafos oficiais | Nicolas | 0:35 |
| 12 | Conclusões e limitações | Nicolas | 0:45 |
| | **Total** | Nuno 1–6 · Nicolas 7–12 | **7:30** |

Margem de cerca de 30 s até o limite de 8 minutos.

## Falas

### 1. Capa — Nuno (0:15)

Apresentar a dupla. Nesta parte a biblioteca passou a aceitar grafos direcionados com pesos, ganhou Bellman-Ford e Floyd-Warshall, e rodamos os quatro estudos nos cinco grafos oficiais. Ao longo da fala dizemos sempre se um número é medido, calculado ou estimado.

### 2. O pedido e os dados — Nuno (0:30)

O enunciado pede quatro coisas: grafos direcionados com pesos, BFS/DFS/Dijkstra adaptados, Bellman-Ford até um destino com duas otimizações e detecção de ciclo negativo, e Floyd-Warshall com a otimização de memória. Os dados: dois grafos de 25 mil vértices — o W_1 é o único com pesos negativos e tem ciclos negativos — e três grafos grandes, até 10 milhões de vértices.

### 3. Arquitetura: direção na representação — Nuno (0:40)

A direção é um detalhe da representação: add_edge só grava u → v quando o grafo é direcionado. Como BFS, DFS e Dijkstra já percorriam só os vizinhos de saída, nenhum deles mudou uma linha — e os 66 testes das partes anteriores passam sem alteração, porque directed é falso por padrão. O que entrou foi o grafo transposto, que na CSR é uma transposição direta em O(n + m), e o Bellman-Ford usa isso.

### 4. Bellman-Ford até um destino — Nuno (0:45)

O Bellman-Ford clássico vai de uma origem para todos. O pedido é de todos para um destino: rodamos o clássico no grafo transposto a partir de t, e o pai em Gᵀ vira o próximo vértice rumo a t. Otimizações: parada antecipada — se uma rodada não muda nada, acabou — e só vértices ativos — uma rodada só relaxa as arestas de quem mudou. No W_2 isso deu 24 rodadas em vez de 24.999 e 2,8 milhões de relaxamentos em vez de cerca de 20 milhões. Não sabemos com certeza se são as duas otimizações da aula; escolhemos as clássicas do Kleinberg-Tardos.

### 5. Ciclos negativos (W_1) — Nuno (0:40)

Ciclo negativo: dá para dar voltas e baixar a distância indefinidamente, então a distância é −∞. Detectamos de duas formas: se a rodada n ainda muda algo, e — a otimização que faz o W_1 ser viável — se os ponteiros de pai formam um ciclo, que é sempre negativo. No W_1 o ciclo apareceu na rodada 4, em vez de 25 mil rodadas. Todos os 25.000 vértices alcançam esse ciclo, então as três distâncias até 100 são −∞. O Floyd-Warshall chega à mesma conclusão: na etapa k = 2, D[i][i] fica negativo e ele para.

### 6. Floyd-Warshall: memória e aceleração — Nuno (0:50)

Floyd-Warshall: etapa k, D[i][j] = min(D[i][j], D[i][k] + D[k][j]). A otimização de memória pedida: a etapa k não muda a linha nem a coluna k, então uma única matriz atualizada no lugar basta — duas matrizes n × n, 7 GiB para 25 mil vértices; o W_3 pediria 112 GiB, e recusamos antes de alocar. Em Python puro uma rodada no W_2 levaria 150 a 170 horas — isso é estimativa. Como as linhas de uma etapa são independentes, paralelizamos e compilamos com Numba o mesmo laço, com o mesmo resultado bit a bit. A rodada completa no W_2 levou 46 minutos, medido.

### 7. Estudo 1 — Nicolas (0:35)

Estudo 1: uma única execução por grafo responde as três origens, porque o destino é comum. No W_1 as três distâncias são −∞ por causa do ciclo negativo — não apresentamos número. Nos outros, distâncias finitas, conferidas com o certificado de otimalidade em todas as arestas e com Dijkstra no grafo transposto. O número de arestas do caminho cresce com o grafo, até 30 no W_5.

### 8. Estudo 2 — Nicolas (0:35)

Estudo 2: a matriz do W_2 saiu do próprio Floyd-Warshall, na primeira rodada completa do benchmark; as dez rodadas deram os mesmos pares, e conferimos as 25 distâncias com Bellman-Ford. Não é simétrica: o grafo é direcionado. No W_1 o Floyd-Warshall para no ciclo negativo, então não há matriz de caminhos mínimos. Do W_3 ao W_5 as matrizes não cabem na memória; os mesmos pares foram calculados com Bellman-Ford só como referência, e isso está identificado.

### 9. Estudo 3 — Nicolas (0:40)

Estudo 3: dez rodadas de cada algoritmo, só o tempo da chamada, sem disco e sem a compilação JIT. O Bellman-Ford cresce com o tamanho do grafo: de 0,2 segundo no W_1 a 97 segundos no W_5. O Floyd-Warshall completo do W_2 levou 46 minutos por rodada, com Numba e 16 threads. No W_1 ele termina em menos de um segundo porque para no ciclo negativo — esse tempo é quase só alocar as matrizes. Os escopos são diferentes: um destino contra todos os pares; a comparação justa é o estudo 4.

### 10. Estudo 4: subgrafos do W_2 — Nicolas (0:40)

Estudo 4, mesmo escopo: os dois algoritmos devolvem a mesma matriz de distâncias e de predecessores, e conferimos que as matrizes são idênticas pelo digest. Para comparar com o mesmo nível de implementação, rodamos os dois em Python puro, um processo, em subgrafos induzidos pelos vértices 1 a N do W_2, dez rodadas cada. O Floyd-Warshall cresce como n ao cubo; o Bellman-Ford de todos os pares, como n vezes as arestas visitadas, e esses subgrafos são esparsos. Por isso a diferença só aumenta com n: de 2 para 52 vezes. Já o Floyd-Warshall compilado com Numba e 16 threads é cerca de 300 vezes mais rápido que a mesma rotina em Python, e aí passa à frente do Bellman-Ford em Python: o ganho de implementação supera a vantagem do algoritmo.

### 11. Estudo 4: grafos oficiais — Nicolas (0:35)

Nos grafos oficiais. W_2: o Bellman-Ford de todos os pares, em Python puro e um processo, levou 2,1 horas por rodada, medido, em 1 de 10 rodadas; a mesma matriz do Floyd-Warshall, conferida pelo digest. O Floyd-Warshall levou 46 minutos, mas com Numba e 16 threads: níveis diferentes. No mesmo nível, Python puro, estimamos 150 a 170 horas para o Floyd-Warshall — estimativa, não medição. No W_1 os dois param no primeiro ciclo negativo, então não há matriz de caminhos mínimos para comparar.

### 12. Conclusões e limitações — Nicolas (0:45)

Conclusões. Para um destino, Bellman-Ford com as duas otimizações resolve até o grafo de 10 milhões de vértices em menos de dois minutos. Para todos os pares, em grafos esparsos como estes, n execuções de Bellman-Ford ganham do Floyd-Warshall no mesmo nível de implementação; o Floyd-Warshall esbarra primeiro na memória — n ao quadrado — e depois no tempo — n ao cubo. Pesos negativos exigem detectar ciclos, e com ciclo a resposta correta é −∞. Limitações: as otimizações da aula não foram confirmadas; o W_2 compara implementações de níveis diferentes, o que dizemos explicitamente; os subgrafos são mais esparsos que o W_2. Obrigado.

Perguntas prováveis e respostas: `docs/EXPLICACAO_PARTE3.md`, seção F.
