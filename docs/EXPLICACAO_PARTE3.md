# Parte 3 explicada: grafos direcionados, Bellman-Ford e Floyd-Warshall

Este documento explica tudo o que foi implementado na Parte 3, para que a dupla consiga defender o
código oralmente. Cada afirmação aponta para o arquivo, a classe ou o método real do projeto. Os
números de exemplo foram conferidos executando o código; os números dos grafos oficiais só entram
no relatório depois dos experimentos.

Sumário: [A. O que o professor pediu](#a-o-que-o-professor-pediu) ·
[B. Arquitetura](#b-alterações-arquiteturais) · [C. Bellman-Ford](#c-bellman-ford) ·
[D. Floyd-Warshall](#d-floyd-warshall) · [E. Experimentos](#e-experimentos) ·
[F. Guia para a apresentação](#f-guia-para-a-apresentação)

---

## A. O que o professor pediu

O enunciado (`trabalho-P3.pdf`) pede quatro funcionalidades e quatro estudos de caso, relatório de
até 5 páginas com a URL do código e apresentação de 8 minutos.

| Requisito do enunciado | Onde está | Situação |
|---|---|---|
| 1. Grafos **direcionados** com pesos, em lista ou vetor de adjacência (matriz opcional); mesmo formato de arquivo; um parâmetro do usuário diz se é direcionado; a direção vai do 1º para o 2º vértice da linha | `GraphReader.read(path, representation, weighted, directed)`, `Graph(..., directed=...)`, as três representações em `graphs/representations.py` | lista, CSR **e** matriz |
| 2. BFS, DFS e Dijkstra em grafos direcionados | `graphs/search.py` e `graphs/shortest_paths.py`, sem mudança de código: passaram a receber só os vizinhos de saída | feito, com testes |
| 3. **Bellman-Ford** de **todos os vértices para um vértice específico**; retornar distâncias, árvore de caminhos mínimos e se há ciclo negativo; implementar as duas otimizações vistas em aula | `graphs/bellman_ford.py`: `BellmanFord.to_target`, `ShortestPathsTo`, `find_negative_cycle` | feito; ver a ressalva sobre as otimizações em [C.7](#c7-otimizações) |
| 4. **Floyd-Warshall** para todos os pares; retornar distâncias, as árvores de caminhos mínimos a partir de cada vértice e se há ciclo negativo; implementar a otimização de memória vista em aula | `graphs/floyd_warshall.py`: `FloydWarshall.run`, `AllPairsShortestPaths` | feito, matriz única atualizada no lugar |
| Estudo 1: distância de 10, 20 e 30 até 100 (Bellman-Ford), em tabela | `experiments/part3/bellman_ford.py` | script pronto |
| Estudo 2: distâncias entre {10, 20, 30, 40, 50} (Floyd-Warshall), em tabela | `experiments/part3/floyd_warshall.py` | script pronto |
| Estudo 3: tempo médio de cada algoritmo em 10 rodadas, sem leitura/escrita em disco | `experiments/part3/benchmark.py` | script pronto |
| Estudo 4: Bellman-Ford para todos os pares × Floyd-Warshall (média de 10 rodadas); quem foi mais eficiente e por quê | `experiments/part3/all_pairs.py` | script pronto |

**O que foi acrescentado:** o parâmetro `directed`, o grafo transposto (`Graph.reversed`), os
módulos `bellman_ford.py` e `floyd_warshall.py`, os resultados `ShortestPathsTo` e
`AllPairsShortestPaths`, as exceções `NegativeCycleError` e `GraphTooLargeError`, o pacote
`experiments/part3/` e 54 testes novos (de 66 para 120).

**O que foi modificado do código anterior:**
- `graphs/representations.py`: as três classes recebem `directed`; `add_edge` só grava a volta
  (v → u) quando o grafo não é direcionado; `finalize` conta duplicatas certo nos dois casos; a CSR
  ganhou `transposed()`.
- `graphs/graph.py`: parâmetro `directed`, atributo `representation`, `reversed()`, atalhos
  `shortest_paths_to` e `all_pairs_shortest_paths`; laços mantidos em grafo direcionado;
  `connected_components` e `diameter` recusam grafo direcionado.
- `graphs/graph_io.py`: `GraphReader.read(..., directed=False)`.
- `run.py`, `README.md`, `docs/ARCHITECTURE.md`.

Nada disso muda o comportamento das Partes 1 e 2: `directed` vale `False` por padrão, e os 66
testes anteriores continuam passando sem alteração.

---

## B. Alterações arquiteturais

### B.1 Como a biblioteca evoluiu

```
Graph (fachada) ──composição──> Representation      (lista | matriz | CSR; agora com `directed`)
   │                                 └─ transposed()   (CSR: transposição direta)
   ├─ reversed()  -> Graph transposto
   └─ algoritmos (classes externas, Strategy):
        BFS, DFS ............................ Parte 1 (inalterados)
        Dijkstra(queue) ..................... Parte 2 (inalterado; fila injetada)
        BellmanFord(early_stop, active_vertices, check_cycles) ... Parte 3
        FloydWarshall(max_vertices, max_memory_bytes) ............ Parte 3
   resultados: ShortestPaths (Parte 2), ShortestPathsTo, AllPairsShortestPaths (Parte 3)
```

### B.2 Novas classes e por que cada uma existe

| Classe (arquivo) | Para quê | Por que uma classe própria |
|---|---|---|
| `BellmanFord` (`bellman_ford.py`) | caminhos mínimos com pesos negativos e detecção de ciclo negativo | é outro algoritmo; as otimizações são parâmetros do construtor (cada uma pode ser desligada para medir o efeito) |
| `ShortestPathsTo` (`bellman_ford.py`) | resultado "de todos até t": `distance`, `successor`, `negative_cycle`, `path_from(v)` | a orientação é a inversa de `ShortestPaths` (lá, pai = vértice anterior; aqui, sucessor = próximo vértice rumo a t) |
| `NegativeCycleError` (`bellman_ford.py`) | sinaliza distâncias indefinidas e carrega o ciclo encontrado | mesmo padrão do `NegativeWeightError` da Parte 2 |
| `FloydWarshall` (`floyd_warshall.py`) | todos os pares | algoritmo O(n³) com limites de tamanho próprios |
| `AllPairsShortestPaths` (`floyd_warshall.py`) | matrizes `dist` e `pred`, `distance(u, v)`, `path(u, v)`, `tree(u)` | é a **mesma** saída do Floyd-Warshall e do Bellman-Ford de todos os pares, o que torna o estudo 4 uma comparação de mesmo escopo |
| `GraphTooLargeError` (`floyd_warshall.py`) | recusa grafos grandes demais antes de alocar | evita travar a máquina por engano (o W_3 exigiria 112 GiB) |

### B.3 Strategy e composição continuam iguais

- **Composição:** `Graph` continua delegando o armazenamento a uma `Representation`. A direção é um
  detalhe da representação (o que `add_edge` grava), então nenhum algoritmo precisou saber se o
  grafo é direcionado: todos leem `neighbors(u)` ou `weighted_neighbors(u)`.
- **Strategy:** os algoritmos são objetos externos que recebem o grafo (`algoritmo.run(grafo, ...)`),
  como `BFS().run(g, s)` e `Dijkstra(IndexedMinHeap).run(g, s)`. `BellmanFord` segue o mesmo
  formato, e suas otimizações são configuração do objeto.
- **Por que não reaproveitar o núcleo de Dijkstra?** Dijkstra fixa cada vértice ao extraí-lo da
  fila e nunca mais o revisita, o que só é correto com pesos não negativos. Bellman-Ford revisita
  vértices em rodadas até nada mudar, e Floyd-Warshall é programação dinâmica sobre uma matriz.
  Forçar os três num núcleo comum criaria ramificações artificiais. O que foi reaproveitado:
  `Graph`, as representações, `ShortestPaths` (devolvido por `BellmanFord.run` e por
  `AllPairsShortestPaths.tree`), a convenção pai = 0 na raiz e −1 se inalcançável, e o padrão de
  exceções.

### B.4 Como a compatibilidade foi preservada

- `directed=False` é o padrão em `Graph`, em `GraphReader.read` e nas representações.
- Grafo não direcionado: `add_edge` grava as duas direções, exatamente como antes; laços
  continuam descartados; `reversed()` devolve o próprio grafo.
- A API pública anterior não mudou de assinatura (só ganhou parâmetros opcionais no fim).
- Os 66 testes das Partes 1 e 2 rodam sem modificação (`python3 run.py test`).

### B.5 Decisões sobre o formato e casos especiais

| Situação | Decisão | Onde |
|---|---|---|
| Direção | linha `u v w` = só a aresta u → v | `Representation.add_edge` |
| Arestas paralelas (u → v repetida) | fica a de menor peso (a única que importa para caminho mínimo), como na Parte 2 | `finalize()` / `AdjacencyMatrix.add_edge` |
| u → v e v → u | são arestas diferentes; as duas ficam | idem |
| Laço u → u em grafo direcionado | **mantido**: um laço negativo é um ciclo negativo | `Graph.add_edge` |
| Laço em grafo não direcionado | descartado, como nas Partes 1 e 2 | `Graph.add_edge` |
| Vértice isolado | existe (1..n vêm da 1ª linha), sem vizinhos | — |
| Peso negativo em grafo **não** direcionado | a aresta pode ser percorrida u → v → u, então é um ciclo negativo de 2 arestas; Bellman-Ford o reporta | teste `test_undirected_negative_edge_is_a_negative_cycle` |
| Grau em grafo direcionado | `degree(u)` = grau de saída | `Representation.degree` |
| Componentes conexas e diâmetro | definidos na Parte 1 para grafos não direcionados; recusam grafo direcionado com `ValueError` | `Graph._require_undirected` |

**Os grafos fornecidos** (lidos com `directed=True`; conferidos antes de implementar):

| Arquivo | n | m (direcionado) | Pesos | Observação |
|---|---:|---:|---|---|
| `grafo_W_1.txt` | 25.000 | 549.953 | de −5,00 a 10,00; 4.998 negativos | 24.999 pares u ↔ v; em 2.446 deles a soma é negativa (ciclo negativo de 2 arestas) |
| `grafo_W_2.txt` | 25.000 | 824.964 | de 0,00 a 10,00 | nenhum negativo |
| `grafo_W_3.txt` | 100.000 | 6.099.941 | ≥ 0 | idêntico ao da Parte 2 |
| `grafo_W_4.txt` | 1.000.000 | ~31·10⁶ | ≥ 0 | idêntico ao da Parte 2 |
| `grafo_W_5.txt` | 10.000.000 | ~40·10⁶ | ≥ 0 | idêntico ao da Parte 2 |

Todos usam vértices 1..n, primeira linha = n, sem laços nem arestas repetidas no W_1 e no W_2.

### B.6 Como a direção é representada (por representação)

- **Lista** (`AdjacencyList`): `_adj[u]` contém só os destinos das arestas que saem de u.
- **CSR** (`CompactAdjacency`): `targets[offsets[u]:offsets[u+1]]` são os destinos de u. Uma aresta
  direcionada ocupa uma entrada; uma não direcionada, duas. O `finalize()` conta só `src` no grau.
- **Matriz** (`AdjacencyMatrix`): só `M[u][v]` é marcado; `M[v][u]` fica 0.
- **Transposto** (`Graph.reversed`): troca cada u → v por v → u. Na CSR é um counting sort direto
  sobre os vetores (`CompactAdjacency.transposed`, O(n + m)); nas outras, as arestas são
  reinseridas. No W_3, a transposição direta levou cerca de 1,8 s (contra ~4,5 s reinserindo).

---

## C. Bellman-Ford

### C.1 Ideia

Bellman-Ford encontra caminhos mínimos **mesmo com pesos negativos**, desde que não haja ciclo
negativo no caminho. Ele não escolhe "o vértice mais próximo" como Dijkstra; em vez disso, repete
rodadas em que tenta melhorar as distâncias usando cada aresta.

### C.2 O que é relaxar uma aresta

Relaxar a aresta (u, v) de peso w é perguntar: "chegar a v passando por u é melhor do que o que
já sei?". Em código (`BellmanFord._solve`):

```python
d = du + w
if d < dist[v]:
    dist[v], parent[v] = d, u
```

Se melhorar, `dist[v]` diminui e o pai de v passa a ser u.

### C.3 Por que n − 1 rodadas bastam (e por que pesos negativos funcionam)

Depois da rodada p, `dist[v]` é no máximo o peso do melhor caminho até v que usa **até p
arestas** (prova por indução: o último vértice antes de v num caminho de p arestas já estava certo
depois da rodada p − 1, e na rodada p a aresta final é relaxada). Sem ciclo negativo, todo caminho
mínimo é simples e tem no máximo n − 1 arestas, então depois de n − 1 rodadas tudo está certo. Em
nenhum momento o algoritmo assume que distâncias só crescem, por isso pesos negativos não
atrapalham. Dijkstra, ao contrário, fixa um vértice ao extraí-lo e nunca o revê; com uma aresta
negativa depois, essa decisão pode estar errada.

### C.4 Distâncias **até** um destino (o que o professor pediu)

O enunciado pede "a distância e caminho mínimo de **todos os vértices para um vértice
específico**". A observação-chave: **a distância de v até t em G é a distância de t até v no grafo
transposto Gᵀ** (todas as arestas invertidas), porque um caminho v → ... → t em G é exatamente um
caminho t → ... → v em Gᵀ, com os mesmos pesos.

Então `BellmanFord.to_target(g, t)`:
1. monta `rev = g.reversed()` (Gᵀ);
2. roda o núcleo de origem única `_solve(rev, t)`;
3. interpreta o resultado: em Gᵀ, o pai de v é o vértice u com aresta u → v em Gᵀ, ou seja,
   v → u em G. Logo **o pai em Gᵀ é o próximo vértice de v rumo a t em G**. Isso é guardado em
   `ShortestPathsTo.successor`, e os sucessores formam a **árvore de caminhos mínimos enraizada em
   t** que o enunciado pede.

Alternativa considerada: relaxar diretamente as arestas de entrada de cada vértice em G. É a mesma
coisa, mas exigiria uma segunda estrutura de adjacência (entrada) dentro de cada representação. O
transposto reaproveita todo o resto e funciona com as três representações. Um grafo não direcionado
é o próprio transposto, então `reversed()` não copia nada nesse caso. Quem roda vários destinos
pode montar Gᵀ uma vez e passá-lo (`to_target(g, t, reversed_graph=rev)`).

Também existem `BellmanFord.run(g, s)` (origem única clássica, devolve `ShortestPaths`) e
`BellmanFord.all_pairs(g)` (usado no estudo 4).

### C.5 Reconstrução do caminho

`ShortestPathsTo.path_from(v)` segue os sucessores: v, `successor[v]`, `successor[successor[v]]`,
… até chegar a t. Devolve `None` se v não alcança t (`distance = inf`) ou se o caminho passa por
um ciclo negativo (`distance = -inf`).

### C.6 Exemplo pequeno (conferido executando o código)

Grafo direcionado com 4 vértices, destino t = 4:

```
1 → 2 (4)    2 → 4 (−3)    1 → 4 (2)    1 → 3 (1)    3 → 4 (4)    4 → 3 (1)
```

Em Gᵀ, a partir de 4: 4 → 1 (2), 4 → 2 (−3), 4 → 3 (4), 2 → 1 (4), 3 → 1 (1), 3 → 4 (1).

| Rodada | Vértices ativos | O que muda | dist (1, 2, 3, 4) |
|---|---|---|---|
| início | {4} | dist[4] = 0 | ∞, ∞, ∞, 0 |
| 1 | {4} | 1 ← 2 (via 4→1), 2 ← −3, 3 ← 4 | 2, −3, 4, 0 |
| 2 | {1, 2, 3} | por 2: dist[1] = −3 + 4 = **1** < 2, sucessor de 1 vira 2 | 1, −3, 4, 0 |
| 3 | {1} | 1 não tem arestas em Gᵀ: nada muda → **para** | 1, −3, 4, 0 |

Resultado: `distance = [1, −3, 4, 0]`, `successor = [2, 4, 4, 0]`, caminho de 1 até 4 = 1 → 2 → 4
(peso 4 − 3 = 1, melhor que a aresta direta 1 → 4 de peso 2). Repare que a aresta negativa fez o
caminho com mais arestas ganhar.

Trabalho medido nesse exemplo (`relaxations` = arestas examinadas):

| Configuração | Rodadas | Relaxamentos |
|---|---:|---:|
| `BellmanFord()` (as otimizações ligadas) | 3 | 6 |
| só parada antecipada (`active_vertices=False`) | 3 | 15 |
| livro-texto (`early_stop=False, active_vertices=False, check_cycles=False`) | 4 | 21 |

Em todas as versões, vértices ainda com distância ∞ são pulados (relaxar a partir de ∞ nunca muda
nada).

### C.7 Otimizações

**Ressalva importante:** o enunciado diz "as duas otimizações discutidas em aula", mas não diz
quais são, e nenhum material do projeto as identifica. As escolhidas abaixo são as clássicas e
tecnicamente justificadas. Há uma evidência indireta: a formulação "de todos os vértices para um
destino t" é a do livro de Kleinberg & Tardos (*Algorithm Design*, seções 6.8 e 6.9), que discute
exatamente um vetor único de distâncias, a parada quando uma rodada não muda nada e a versão em que
só os vértices que mudaram propagam ("push-based"). **A correspondência com o que foi dito em aula
precisa ser confirmada pela dupla.**

As duas otimizações implementadas (parâmetros do construtor de `BellmanFord`):

1. **Parada antecipada (`early_stop=True`).** Se uma rodada inteira não melhora nenhuma distância,
   as próximas também não melhorarão (cada rodada só depende do estado anterior), então o
   algoritmo para. Benefício: em vez de sempre n − 1 rodadas, faz tantas quanto o número de arestas
   do caminho mínimo mais longo (em arestas) + 1. No W_2 (n = 25.000), a execução preliminar até o
   vértice 100 parou após 24 rodadas, contra as 24.999 do algoritmo de livro.
2. **Só os vértices que mudaram (`active_vertices=True`).** Uma aresta u → v só pode melhorar
   `dist[v]` se `dist[u]` mudou desde a última vez que foi relaxada. Então a rodada p só percorre as
   arestas dos vértices cuja distância mudou na rodada p − 1 (`active`), em vez de todas as m
   arestas. A lista `changed` é montada sem repetição (vetor `queued`). Benefício: o trabalho por
   rodada cai de O(m) para a soma dos graus dos vértices ativos; no exemplo acima, de 15 para 6
   relaxamentos.

Detalhes que acompanham as duas:
- **Vetor único, atualizado no lugar.** Há um só `dist` (O(n) de memória), e uma melhoria feita no
  meio da rodada já é usada no restante dela. A garantia "depois da rodada p, no máximo o melhor
  caminho com até p arestas" continua valendo (é um caso particular da mesma indução), então o
  limite de n − 1 rodadas e a detecção na rodada n continuam corretos.
- **Detecção antecipada de ciclo negativo (`check_cycles=True`).** Ver C.8. Não é uma das "duas";
  foi necessária porque, com ciclo negativo, a parada antecipada nunca acontece e o algoritmo
  faria n rodadas. No W_1 isso seriam 25.000 rodadas; com a verificação, a execução preliminar
  encontrou o ciclo em 4.

Cada otimização pode ser desligada (`BellmanFord(early_stop=False, active_vertices=False,
check_cycles=False)` é o algoritmo de livro), e os testes rodam as 8 combinações contra uma
implementação de referência (`tests/test_bellman_ford.py`, `VARIANTS`).

### C.8 Ciclos negativos

**Definição de comportamento.** Se existe um ciclo de peso negativo que um vértice v alcança e que
alcança t, a distância de v até t é **−∞** (dá para dar voltas no ciclo indefinidamente). Não existe
caminho mínimo nesse caso.

**Como detectar (duas formas, ambas implementadas em `_solve`):**
1. **Rodada n.** Sem ciclo negativo, nada muda depois da rodada n − 1. Se a rodada n ainda muda
   alguma distância, existe ciclo negativo. É a garantia clássica e está sempre ativa.
2. **Ciclo nos ponteiros de pai** (`_parent_cycle`). Se os ponteiros `parent` formam um ciclo, esse
   ciclo tem peso negativo: ao longo dele, cada `dist[v]` foi definido como `dist[pai] + w` e o pai
   só diminuiu depois; somando as desigualdades, a soma dos pesos é < 0. A verificação percorre os
   pais a partir dos vértices que mudaram, marcando o caminho; voltar a um vértice do mesmo
   percurso é um ciclo. Custa O(n) e é feita depois das rodadas 1, 2, 4, 8, … (O(log rodadas)
   verificações). Assim o ciclo é achado muito antes da rodada n.

**O que o resultado devolve** (`ShortestPathsTo`):
- `negative_cycle`: o ciclo encontrado, como lista fechada `[c0, c1, ..., c0]` na ordem das arestas
  de G (os testes conferem que o peso é negativo e que as arestas existem);
- `distance[v] = -inf` para todo v que **alcança esse ciclo** (busca em largura em Gᵀ a partir do
  ciclo, `_mark_minus_infinity`). Como o ciclo foi encontrado na árvore enraizada em t, ele alcança
  t, então esses vértices certamente têm distância −∞;
- `exact = False`. Os demais valores finitos passam a ser só limites superiores, porque outro ciclo
  negativo, ainda não encontrado, poderia afetá-los. (Nos grafos em que todo vértice alcança o
  ciclo, como na execução preliminar do W_1, todos ficam −∞ e não sobra valor incerto.)

**"O grafo possui ciclo negativo?"** `to_target` só enxerga ciclos que **alcançam t**: um ciclo
que t não alcança em Gᵀ não afeta nenhuma distância até t. Para responder sobre o grafo inteiro,
`BellmanFord.find_negative_cycle(g)` roda o mesmo núcleo a partir de uma **origem virtual** com
aresta de peso 0 para todos os vértices (todas as distâncias começam em 0 e todos os vértices
começam ativos). Qualquer ciclo negativo do grafo aparece. O estudo 1 informa as duas coisas.

### C.9 Complexidade

- **Tempo:** pior caso O(n · m) (n rodadas de m relaxamentos). Com as otimizações, o custo real é
  a soma, em todas as rodadas, dos graus dos vértices que mudaram; com parada após P rodadas, no
  máximo O(P · m). As verificações de ciclo somam O(n log P).
- **Espaço:** O(n) para `dist`, `parent` e `queued`, mais o grafo transposto (O(n + m)) em
  `to_target`.

---

## D. Floyd-Warshall

### D.1 Programação dinâmica

Numere os vértices 1..n. Seja D_k[i][j] o peso do melhor caminho de i a j cujos vértices
**intermediários** estão todos em {1, …, k}. Então:

- D_0[i][j] = 0 se i = j; w(i, j) se há aresta; ∞ caso contrário;
- **D_k[i][j] = min(D_{k−1}[i][j], D_{k−1}[i][k] + D_{k−1}[k][j])**: o melhor caminho com
  intermediários em {1..k} ou não usa k (primeiro termo), ou passa por k uma vez (segundo termo);
- D_n[i][j] é a distância de i a j.

### D.2 O que significam a matriz e o k

- `dist[i][j]` (em `AllPairsShortestPaths.dist`) é a estimativa atual de i até j.
- O laço externo `for k in range(1, n + 1)` é a **etapa**: depois da etapa k, `dist` contém D_k.
  O k é o "vértice que passa a poder ser usado como intermediário".
- `pred[i][j]` é o vértice **anterior a j** no melhor caminho de i até j. A linha `pred[i]` é a
  árvore de caminhos mínimos a partir de i (o enunciado pede "as árvores de caminhos mínimos a
  partir de cada vértice"); `AllPairsShortestPaths.tree(i)` a devolve como um `ShortestPaths`, o
  mesmo tipo do Dijkstra.

### D.3 Como a matriz é atualizada (`FloydWarshall.run`)

Para cada etapa k e cada linha i:

```python
dik = di[k]
if dik == INF or i == k:
    continue                      # nada a ganhar passando por k
for j in compress(columns, map(gt, di, map(add, repeat(dik), dk))):
    di[j] = dik + dk[j]           # D[i][j] = D[i][k] + D[k][j]
    pi[j] = pk[j]                 # o anterior a j agora é o anterior a j no caminho k -> j
```

A linha `compress(...)` encontra, em velocidade de C (sem laço Python por célula), os j em que
D[i][k] + D[k][j] < D[i][j]; o laço Python só passa pelas células que de fato melhoram. Linhas
com D[i][k] = ∞ são puladas inteiras, o que poupa muito trabalho em grafos pouco conectados.

### D.4 Exemplo pequeno (conferido executando o código)

Arestas: 1 → 2 (3), 2 → 3 (−2), 1 → 3 (4), 3 → 1 (1).

```
D_0:        1    2    3          Etapa k = 1: linha 3 (D[3][1] = 1):
   1        0    3    4            D[3][2] = min(∞, 1 + 3) = 4
   2        ∞    0   −2
   3        1    ∞    0          Etapa k = 2: linha 1 (D[1][2] = 3):
                                   D[1][3] = min(4, 3 + (−2)) = 1   <- o caminho 1→2→3 vence a aresta direta
                                   pred[1][3] = pred[2][3] = 2
                                 Etapa k = 3: linha 2 (D[2][3] = −2):
                                   D[2][1] = min(∞, −2 + 1) = −1
Final:      1    2    3
   1        0    3    1          pred:  1: [0, 1, 2]   2: [3, 0, 2]   3: [3, 1, 0]
   2       −1    0   −2          caminho 1 → 3: pred[1][3] = 2, pred[1][2] = 1  =>  1 → 2 → 3
   3        1    4    0
```

D[1][2] = 3 e D[2][1] = −1: o algoritmo **não assume simetria**.

### D.5 Reconstrução de caminhos

`AllPairsShortestPaths.path(u, v)` usa `tree(u).path_to(v)`: parte de v, vai para `pred[u][v]`,
depois `pred[u][pred[u][v]]`, … até u, e inverte a lista. `None` se `pred[u][v] = −1`
(inalcançável).

### D.6 Ciclos negativos

Um ciclo negativo que passa por i faz D[i][i] < 0 (ir de i a i custa menos que ficar parado). A
diagonal da linha i só muda quando a linha i é atualizada, então o teste `if di[i] < 0` logo
depois de cada linha detecta o primeiro ciclo. Um laço negativo é detectado antes da primeira
etapa. Ao detectar:
- o algoritmo **para** (`stopped_at` = etapa k);
- reconstrói, pelos predecessores da linha i, um passeio fechado i → … → i de peso negativo e o
  decompõe em ciclos simples, devolvendo um de peso negativo (`_negative_simple_cycle`; por
  segurança, se o passeio não for válido, usa `BellmanFord.find_negative_cycle`);
- `distance`, `path` e `tree` lançam `NegativeCycleError`, porque a matriz ficou parcial.

Por que parar em vez de completar as n etapas e marcar −∞ onde couber? Completar exigiria todas as
n³ atualizações; no W_1 (n = 25.000) isso é inviável em Python. Parar no primeiro ciclo responde à
pergunta do enunciado ("se o grafo possui um ciclo negativo") e é o mesmo critério do Bellman-Ford
de todos os pares, então o estudo 4 compara escopos iguais.

### D.7 Otimização de memória

A recorrência sugere uma matriz por etapa (n + 1 matrizes, Θ(n³) de memória). A implementação usa
**uma única matriz, atualizada no lugar**, com Θ(n²). Isso é correto porque a etapa k **não altera
a linha k nem a coluna k** (com D[k][k] = 0):

- D[k][j] = min(D[k][j], D[k][k] + D[k][j]) = D[k][j];
- D[i][k] = min(D[i][k], D[i][k] + D[k][k]) = D[i][k].

Logo, durante a etapa k, os valores lidos em D[i][k] e D[k][j] ainda são os de D_{k−1}, como exige a
recorrência. (É o argumento do exercício 25.2-4 do CLRS, 3ª edição.) Como o enunciado não diz qual
foi a otimização discutida em aula, **a correspondência deve ser confirmada pela dupla**; esta é a
otimização de memória clássica do algoritmo.

Além disso, as linhas são `array('d')` (8 bytes por célula) e `array('i')` (4 bytes), em vez de
listas Python (8 bytes de ponteiro + 24 do objeto float por célula): 12(n + 1)² bytes no total
(`FloydWarshall.memory_bytes`).

### D.8 Complexidade e limites

- **Tempo:** Θ(n³) atualizações de célula, independentemente de m (na prática, menos quando há
  muitas linhas com D[i][k] = ∞). Medição preliminar num grafo fortemente conexo pequeno: cerca de
  45 ns por célula em CPython.
- **Espaço:** Θ(n²): 12(n + 1)² bytes.
- **Limites:** `FloydWarshall(max_vertices=3000)` por padrão, e opcionalmente `max_memory_bytes`;
  acima disso, `GraphTooLargeError` antes de alocar. Nos estudos, o tamanho é conferido pela 1ª linha
  do arquivo antes de carregar, e cada execução roda num processo com limite de memória e de tempo.

| Grafo | n | Matrizes (12(n+1)² bytes) | n³ |
|---|---:|---:|---:|
| W_1, W_2 | 25.000 | 7,0 GiB | 1,6·10¹³ |
| W_3 | 100.000 | 111,8 GiB | 10¹⁵ |
| W_4 | 10⁶ | ~11 TiB | 10¹⁸ |
| W_5 | 10⁷ | ~1,1 PiB | 10²¹ |

A estimativa preliminar de "8 dias por rodada no W_2" (n³ × 45 ns) foi refeita com uma calibração
real (D.9): o trabalho efetivo é menor que n³ e a execução foi acelerada. Do W_3 em diante as
matrizes nem cabem na memória (31 GiB). No W_1, a execução para no primeiro ciclo negativo.

### D.9 Acelerando o Floyd-Warshall sem mudar o algoritmo

**Quanto trabalho existe de verdade.** A etapa k só processa as linhas i com D[i][k] finito no seu
início, isto é, os vértices i que alcançam k usando só intermediários em 1..k−1. Esse número é
contado **exatamente** (sem rodar o Floyd-Warshall) por uma busca em Gᵀ a partir de k que só expande
vértices < k (`experiments/part3/fw_calibrate.py`, `stage_rows`). No W_2: 400.565.299 linhas no
total (64,1% de n(n−1)), ou seja, 1,001·10¹³ células. As primeiras etapas quase não têm linhas
(etapa 1000: 19 linhas; etapa 25.000: 24.999), então "tempo × n / etapas feitas" **subestima muito**
o total. Por isso os scripts não usam mais essa conta para o Floyd-Warshall.

**O que não mudou em nenhuma versão:** a ordem das etapas k = 1..n, a comparação estrita
`D[i][j] > D[i][k] + D[k][j]`, a mesma soma em double e a cópia `P[i][j] = P[k][j]`. Por isso as
matrizes saem **bit a bit iguais** às do laço sequencial original, que continua sendo a referência
(`FloydWarshall()` sem argumentos). Variantes em blocos (tiled/blocked) foram descartadas porque
mudam a ordem em que os candidatos são testados.

**Por que dá para paralelizar:** dentro da etapa k, cada linha i lê só a si mesma e a linha k, e a
linha k não muda na etapa k (D.7). As linhas são independentes; dividi-las entre trabalhadores não
muda nenhuma célula. Com ciclo negativo na etapa k, reporta-se o menor i com D[i][i] < 0, a mesma
linha onde o laço sequencial para, logo o mesmo ciclo e a mesma `stopped_at`.

| Versão | Como | Dependências |
|---|---|---|
| `FloydWarshall()` | laço original, `compress`/`map` em C | nenhuma |
| `FloydWarshall(workers=16)` | linhas de cada etapa em 16 processos (`os.fork`), matrizes em `mmap` compartilhado, barreira por pipes | nenhuma (Linux/Unix) |
| `FloydWarshall(engine="numpy", workers=16)` | ufuncs NumPy por blocos de 256 linhas, em threads | NumPy |
| `FloydWarshall(engine="numba", workers=16)` | o mesmo laço de linhas compilado pelo Numba (`prange`, sem fast-math), chamado uma vez por etapa a partir do Python | NumPy + Numba |

As engines estão em `graphs/floyd_warshall_engines.py` e só são importadas quando pedidas; a
biblioteca continua funcionando só com a biblioteca padrão. `prepare()` importa e compila a engine
antes da medição (a compilação do Numba não entra no tempo). Como o laço de etapas continua em
Python, o timeout (SIGALRM) e `on_stage` funcionam entre etapas.

**Testes de equivalência** (`tests/test_floyd_warshall.py`): `ParallelFloydWarshallTest` e
`AcceleratedEnginesTest` comparam matrizes de distâncias e predecessores célula a célula com o
sequencial, caminhos, árvores, `rows_done`, ciclo negativo e etapa de parada, com 1 e 4
trabalhadores. Os de NumPy/Numba são pulados (skip) quando os pacotes não estão instalados.

**Medições** (Ryzen 7 5700X3D, 8 núcleos/16 threads, 31 GiB):

| Medição | Python sequencial | Python, 16 processos | NumPy, 16 threads | Numba, 16 threads |
|---|---:|---:|---:|---:|
| Subgrafo W_2 1..3000, execução completa (medido) | 274,0 s | 36,6 s | 8,5 s | 1,16 s |
| Etapa densa sintética n = 25.000 (medido, ns/célula) | ~54–62 | 7,0–9,3 | 2,0–2,5 | 0,63–0,91 |
| W_2, 10 min de execução real (medido) | 1967 etapas, 0,07% do trabalho | 3095 etapas, 0,81% | — | 10.093 etapas, 18,8% |
| W_2, uma rodada (**estimativa**) | ~150–170 h | ~20–26 h | ~6–11 h (pela etapa densa) | ~0,9 h (modelo); ≤ ~2,2 h (pior caso da etapa densa) |
| Pico de RSS | — | 7,03 GiB | 7,9 GiB (etapa densa) | 7,15 GiB (calibração), 7,3 GiB no worker |

Os quatro modos deram o mesmo digest SHA-1 da matriz no subgrafo 1..3000. A estimativa de uma
rodada vem de: tempo medido + Σ (custo por linha ajustado nas últimas etapas medidas) × linhas
exatas das etapas restantes. O pior caso usa o custo de uma etapa densa sintética com muitas
atualizações (0,91 ns/célula) para todo o trabalho restante. **Nenhuma estimativa é medição.**

**Como calibrar:** `python3 run.py part3-fw-calibrate --graph grafo_W_2 --engine numba --workers 16
--budget 600` grava `results/part3/calibration/fw_grafo_W_2_numba_p16.{json,md}`.

---

## E. Experimentos

Regras comuns (iguais às da Parte 2): grafos oficiais fora do repositório e nunca modificados;
leitura e escrita em disco **fora** do tempo medido; `time.perf_counter()` com o coletor de lixo
pausado; resultados gravados a cada execução; nada é inventado ou estimado sem rótulo.

### E.1 Estudo 1 — Bellman-Ford de 10, 20 e 30 até 100 (`experiments/part3/bellman_ford.py`)

- **O que mede:** uma execução de `to_target(g, 100)` por grafo, que responde as três origens de
  uma vez (destino comum, sem cálculo redundante).
- **O que registra:** distância, número de arestas, caminho e status por origem; se há ciclo
  negativo até o destino e no grafo todo (`find_negative_cycle`); rodadas e relaxamentos; tempo;
  quantos vértices ficaram com −∞ ou ∞.
- **Validação** (quando não há ciclo negativo): certificado de otimalidade em todas as arestas
  (`dist[u] ≤ w(u, v) + dist[v]`, e a aresta até o sucessor é justa) e, se não houver peso
  negativo, comparação com Dijkstra em Gᵀ.
- **Como ler a tabela:** "−∞ (ciclo negativo)" quer dizer que a origem alcança um ciclo negativo
  que alcança 100; "∞" quer dizer que 100 é inalcançável a partir dela.

### E.2 Estudo 2 — Floyd-Warshall entre {10, 20, 30, 40, 50} (`experiments/part3/floyd_warshall.py`)

- Matriz 5 × 5 por grafo, linha = origem, coluna = destino (sem simetria).
- Antes de rodar, o tamanho das matrizes é checado pela 1ª linha do arquivo. Grafos acima do limite
  são registrados como "não executado" com o motivo (memória necessária). O Floyd-Warshall roda num
  processo separado, com tempo e memória limitados; um timeout informa a etapa k alcançada.
- `--from-benchmark results/part3/benchmark`: se o estudo 3 já rodou rodadas completas do
  Floyd-Warshall no grafo, a matriz 5 × 5 vem da primeira rodada concluída (cada rodada grava os 25
  pares fora do tempo medido), em vez de rodar o algoritmo de novo. A tabela cita a rodada e diz se
  todas as rodadas deram os mesmos pares.
- Quando o Floyd-Warshall não produz matriz (não executado, timeout ou ciclo negativo), os mesmos
  25 pares são calculados com Bellman-Ford (uma execução por coluna), e a tabela diz **qual
  algoritmo produziu os números**. Isso não substitui o Floyd-Warshall: só garante que a tabela
  tenha os valores, com a origem explícita.

### E.3 Estudo 3 — Tempo médio em 10 rodadas (`experiments/part3/benchmark.py`)

- **Bellman-Ford:** escopo do estudo 1 (todos os vértices até 100), incluindo montar Gᵀ. Os dois
  tempos (`reverse_s`, `solve_s`) são gravados separadamente. O grafo é carregado uma vez.
- **Floyd-Warshall:** escopo do estudo 2 (todos os pares). Cada rodada roda num processo próprio;
  só a chamada é cronometrada. Depois dela (fora do tempo) a rodada grava os pares do estudo 2 e a
  primeira rodada concluída grava o digest da matriz (estudo 4). Assim, **cada execução completa
  serve aos estudos 2, 3 e 4**. `--fw-engine`, `--fw-workers`, `--fw-timeout-for` e `--fw-budget-for`
  escolhem a engine e os limites por grafo; ficam registrados nas configurações (o `--resume` recusa
  misturar rodadas com configurações diferentes).
- **Os escopos são diferentes** (um destino × todos os pares). Comparar diretamente esses dois
  tempos não diz qual algoritmo é melhor; isso é o estudo 4.
- **Saída:** cada rodada, média, desvio-padrão amostral, mínimo e máximo, e o ambiente (CPU, RAM,
  Python). Uma rodada interrompida por ciclo negativo é uma rodada **concluída** (o algoritmo
  respondeu "ciclo negativo") e aparece com esse rótulo.

### E.4 Estudo 4 — Todos os pares: Bellman-Ford × Floyd-Warshall (`experiments/part3/all_pairs.py`)

- **Mesmo escopo:** `BellmanFord.all_pairs` (n execuções do mesmo núcleo, uma por origem) e
  `FloydWarshall.run` devolvem o mesmo `AllPairsShortestPaths` (as duas matrizes n × n). Os dois
  param no primeiro ciclo negativo.
- **Conferência:** a primeira rodada concluída de cada algoritmo grava um *digest* da matriz de
  distâncias (`matrix_digest`); a tabela mostra se os dois são iguais.
- **Subgrafos:** além dos grafos oficiais, subgrafos induzidos pelos vértices 1..N
  (`--subgraphs grafo_W_2:500,1000,2000,3000,4000`), para mostrar o efeito de n e m com
  medições reais.
- **Timeouts:** uma rodada interrompida informa o progresso (etapa k ou origens concluídas). O
  relatório deriva uma estimativa, sempre rotulada: para o Bellman-Ford, tempo × n / origens
  concluídas; para o Floyd-Warshall, um **limite superior** (etapas restantes × (n − 1) linhas ×
  custo por célula medido), porque as etapas não custam o mesmo (D.9).
- `--fw-from-benchmark results/part3/benchmark` usa as rodadas do Floyd-Warshall já medidas no
  estudo 3 (mesma chamada, mesmo escopo) em vez de repeti-las.

### E.5 Medição × estimativa

| Rótulo | Significado |
|---|---|
| medido | rodada concluída; tempo lido do JSON |
| timeout | a rodada atingiu o limite; o tempo real é **maior** que o limite |
| não executado / recusado | não rodou (limite de memória, de vértices ou orçamento); o motivo está no registro |
| extrapolação | conta feita a partir de uma medição parcial ou de uma constante medida; nunca entra numa célula de "média" |

### E.6 Como explicar resultados inesperados

- **Floyd-Warshall "rápido" no W_1:** ele para no primeiro ciclo negativo; o tempo é quase só a
  alocação das matrizes de 7 GiB. Não é o custo de um Floyd-Warshall completo.
- **Bellman-Ford com poucas rodadas:** a parada antecipada termina quando o caminho mínimo mais
  longo (em arestas) foi encontrado, muitas vezes dezenas de rodadas, não n − 1.
- **Montar Gᵀ pesa no tempo do Bellman-Ford:** por isso `reverse_s` e `solve_s` são separados.
- **Bellman-Ford de todos os pares ganha do Floyd-Warshall em grafos esparsos:** ver F.6.

---

## F. Guia para a apresentação

### F.1 Por que Bellman-Ford suporta pesos negativos e Dijkstra não?
Dijkstra extrai o vértice de menor estimativa e o considera definitivo; isso só é seguro se
nenhum caminho que ainda não foi explorado puder diminuir essa estimativa, o que exige pesos ≥ 0.
Bellman-Ford não fixa ninguém: relaxa as arestas em rodadas até nada mudar, e a garantia de
correção ("depois da rodada p, melhor caminho com até p arestas") não depende do sinal dos pesos.
No código, `Dijkstra.run` lança `NegativeWeightError` se `graph.has_negative_weights()`.

### F.2 Qual a diferença entre o Bellman-Ford tradicional e a versão orientada a destino?
O tradicional calcula distâncias **de** uma origem **para** todos. A versão pedida calcula **de**
todos **para** um destino t. Implementamos rodando o tradicional em Gᵀ a partir de t
(`to_target` → `_solve(rev, t)`); o pai em Gᵀ vira o próximo vértice rumo a t em G. A árvore
resultante é enraizada em t, com as arestas apontando para t.

### F.3 Como detectar ciclos negativos?
Duas formas no código: (1) se a rodada n ainda melhora alguma distância, há ciclo negativo;
(2) se os ponteiros de pai formam um ciclo, ele é negativo (`_parent_cycle`, verificado nas rodadas
1, 2, 4, 8, …). Para o grafo todo, `find_negative_cycle` usa uma origem virtual ligada a todos com
peso 0. No Floyd-Warshall, D[i][i] < 0.

### F.4 Por que Floyd-Warshall é O(n³)?
São três laços aninhados sobre os vértices (k, i, j) com trabalho O(1) por célula: n etapas, cada
uma atualizando n² células. Não depende de m.

### F.5 Por que Floyd-Warshall usa O(n²) de memória?
A recorrência usa D_{k−1} para calcular D_k, mas a etapa k não muda a linha k nem a coluna k, então
uma única matriz pode ser atualizada no lugar (D.7). Ficam duas matrizes n × n (distâncias e
predecessores), 12(n + 1)² bytes.

### F.6 Quando Bellman-Ford para todos os pares é melhor que Floyd-Warshall?
Bellman-Ford de todos os pares custa no pior caso O(n · n · m) = O(n²m), pior que O(n³) quando
m ≫ n. Mas com as otimizações cada execução custa cerca de P · m (P = rodadas até estabilizar,
muitas vezes dezenas), ou seja, O(n · P · m) no total. Em grafos **esparsos** (m da ordem de n)
isso é muito menor que n³, e Bellman-Ford ganha; em grafos **densos** (m da ordem de n²) o
Floyd-Warshall, com seu laço simples e previsível, tende a ganhar. Além disso, o Floyd-Warshall
sempre faz as n³ verificações, enquanto o Bellman-Ford só trabalha onde algo muda.

**Resultado do estudo 4 (medido, 10 rodadas, mesma matriz nos dois algoritmos pelo digest):**

| Subgrafo do W_2 | n | m | BF todos os pares (Python) | FW (Python) | FW/BF | FW (Numba, 16 threads) |
|---|---|---|---|---|---|---|
| 1..500 | 500 | 307 | 0,0128 s | 0,0291 s | 2,3 | 0,068 s |
| 1..1000 | 1.000 | 1.291 | 0,0505 s | 0,280 s | 5,5 | 0,033 s |
| 1..2000 | 2.000 | 5.360 | 0,521 s | 19,07 s | 37 | 0,173 s |
| 1..3000 | 3.000 | 11.973 | 6,43 s | 277,5 s | 43 | 1,05 s |
| 1..4000 | 4.000 | 21.171 | 20,04 s | 1.043,5 s | 52 | 3,53 s |

- **No mesmo nível de implementação** (Python puro, 1 processo), o Bellman-Ford de todos os pares
  ganha em todos os subgrafos, e a vantagem cresce com n.
- **W_2 oficial:** Bellman-Ford de todos os pares em Python = 7.600,7 s (rodada 0, medido; demais
  rodadas em execução na entrega) contra Floyd-Warshall Numba = 2.735,99 ± 8,66 s (10/10, estudo 3).
  O Floyd-Warshall só fica à frente porque a engine Numba é ~300× mais rápida que Python puro
  (296× em n = 4.000). No mesmo nível, o Floyd-Warshall em Python levaria 150–170 h (**estimativa**),
  ou seja, o Bellman-Ford seria ~70–80× mais rápido. A matriz do Bellman-Ford tem o **mesmo digest**
  que a do Floyd-Warshall.
- **W_1:** os dois param no primeiro ciclo negativo (BF 0,03 s; FW 0,91 s, quase só a alocação).
- **Se perguntarem "então qual é melhor?":** em grafo esparso, o algoritmo Bellman-Ford; a
  implementação compilada do Floyd-Warshall venceu no W_2 por ser compilada, não por ser melhor
  algoritmo. Um Bellman-Ford compilado não foi testado (extensão natural).

### F.7 Como as otimizações alteram o desempenho?
Sem elas, Bellman-Ford sempre faz n − 1 rodadas de m relaxamentos (no W_2: 24.999 × 824.964 ≈
2·10¹⁰). Com a parada antecipada, faz P rodadas (24 na execução preliminar do W_2). Com os vértices
ativos, cada rodada só olha as arestas de quem mudou. No exemplo de C.6: 21 → 15 → 6 relaxamentos.
A verificação de ciclo nos pais é o que torna o W_1 viável (4 rodadas em vez de 25.000).

### F.8 Por que não reutilizamos o núcleo de Dijkstra?
Porque são algoritmos diferentes: Dijkstra precisa de fila de prioridade e fixa vértices; Bellman-
Ford trabalha em rodadas sem fila de prioridade; Floyd-Warshall é programação dinâmica em matriz.
Reutilizamos o que é comum de verdade: o grafo e suas representações, o tipo de resultado
(`ShortestPaths`), a convenção de pais e o padrão de exceções.

### F.9 Como garantimos a correção?
- 128 testes automatizados (`python3 run.py test`), dos quais 62 novos (os 4 das engines NumPy/Numba
  só rodam no ambiente com essas dependências; no ambiente `~/.venvs/cos242-accel`, nenhum é pulado), incluindo:
  - comparação com uma **implementação de referência independente** (`tests/helpers.py`,
    `reference_directed`: Bellman-Ford de livro sobre a lista de arestas, com propagação de −∞);
  - grafos aleatórios com pesos negativos **sem** ciclo negativo, gerados com potenciais
    (w = c + p(u) − p(v), c ≥ 0, então todo ciclo tem peso ≥ 0);
  - as 8 combinações de otimizações dão o mesmo resultado;
  - Bellman-Ford de todos os pares = Floyd-Warshall, e cada destino do Bellman-Ford = uma coluna do
    Floyd-Warshall;
  - os ciclos devolvidos existem no grafo e têm peso negativo (`cycle_weight`);
  - Dijkstra direcionado com vetor e heap contra a referência.
- Nos estudos: certificado de otimalidade em todas as arestas, comparação com Dijkstra em Gᵀ e
  igualdade dos *digests* das matrizes no estudo 4.

### F.10 Outras perguntas prováveis
- **"O que acontece se o grafo for não direcionado e tiver peso negativo?"** A aresta pode ir e
  voltar (u → v → u), o que é um ciclo negativo de 2 arestas; os algoritmos o reportam.
- **"E se o destino for inalcançável?"** `distance = inf`, `successor = -1`, `path_from` devolve
  `None`.
- **"Por que guardar sucessor e não predecessor no Bellman-Ford?"** Porque o destino é fixo: o
  natural é cada vértice saber o próximo passo rumo a t (como numa tabela de roteamento).
- **"Por que Python puro, se é lento?"** Continuidade com as Partes 1 e 2 (só a biblioteca padrão).
  No estudo 4 a comparação justa é no mesmo nível (os dois em Python puro, 1 processo); o
  Floyd-Warshall com Numba é uma adição nossa, usada para tornar o W_2 viável (45,6 min por rodada
  em vez de 150–170 h estimadas), e é sempre identificado como tal.
- **"Por que o Floyd-Warshall termina em 0,91 s no W_1?"** Ele para na etapa k = 2 ao achar
  D[i][i] < 0 (ciclo 17332 → 2 → 17332, −0,55); o tempo é quase só alocar 7 GiB.
- **"Por que os ciclos do W_1 diferem entre os estudos?"** Há vários ciclos negativos; cada
  algoritmo devolve o primeiro que encontra (BF até 100: 21005 ↔ 10756; grafo todo: 10663 ↔ 17332;
  BF de todos os pares: 12961 ↔ 22007; FW: 17332 ↔ 2). Todos existem no grafo e têm peso negativo.
- **"Por que não rodaram o Floyd-Warshall no W_3?"** As duas matrizes exigiriam 111,8 GiB
  (calculado) para 31 GiB de RAM; recusamos antes de alocar, sem swap. Em tempo, seriam ~49 h por
  rodada com Numba (estimado).
