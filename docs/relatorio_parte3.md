<p class="eyebrow">Teoria dos Grafos · COS 242 · 2026/2 · Trabalho de disciplina – Parte 3</p>

# Relatório – Trabalho de Grafos COS 242 (Parte 3)

**Dupla:** Nuno Correia e Nicolas Viana · **Código-fonte:** https://github.com/nunoduartte/cos242-graph

## 1. Introdução e objetivos

A biblioteca das Partes 1 e 2 (Python 3, só a biblioteca padrão) representava grafos não direcionados, com e sem pesos, em lista, matriz e CSR, e oferecia BFS, DFS, componentes e Dijkstra (vetor e heap). Nesta parte acrescentamos **grafos direcionados com pesos**, adaptamos BFS, DFS e Dijkstra, e implementamos **Bellman-Ford** (de todos os vértices **até** um destino) e **Floyd-Warshall** (todos os pares), ambos com detecção de ciclo negativo e com as otimizações pedidas. Rodamos os quatro estudos de caso nos cinco grafos oficiais (W_1 a W_5, de 2,5·10⁴ a 10⁷ vértices). Todos os números vêm de `results/part3/` e estão rotulados como **medido**, **calculado** (contagem exata a partir dos dados), **estimado**, **recusado por memória** ou **não executado**.

## 2. Projeto e implementação

Mantivemos a arquitetura anterior: `Graph` guarda uma `Representation` (composição) e os algoritmos são objetos externos que recebem o grafo (Strategy). A direção é um detalhe da representação, então nenhum algoritmo precisou saber se o grafo é direcionado.

| Módulo | Decisão principal |
|---|---|
| `representations.py`, `graph.py`, `graph_io.py` | Parâmetro `directed` (padrão `False`, o que preserva as Partes 1 e 2): a linha `u v w` grava só u → v. Laços são mantidos em grafo direcionado (um laço negativo é um ciclo negativo); arestas paralelas ficam com o menor peso. `Graph.reversed()` devolve Gᵀ; na CSR é uma transposição direta O(n + m). `degree` = grau de saída; componentes e diâmetro recusam grafo direcionado. |
| BFS, DFS, Dijkstra | **Sem mudança de código**: já percorriam só `neighbors(u)`/`weighted_neighbors(u)`, que agora devolvem as arestas de saída. Testes novos conferem alcançabilidade assimétrica e Dijkstra direcionado contra uma referência. |
| `bellman_ford.py` | `BellmanFord.to_target(g, t)`: distância de todos até t em G = distância a partir de t em Gᵀ. O pai em Gᵀ é o **sucessor** rumo a t, então a árvore devolvida (`ShortestPathsTo`) é enraizada em t; `path_from(v)` reconstrói o caminho. Com ciclo negativo que alcança t, devolve o ciclo, marca −∞ em quem o alcança e `exact = False`. `find_negative_cycle(g)` (origem virtual com arestas de peso 0) responde se o **grafo** tem ciclo negativo. `all_pairs` = n execuções do mesmo núcleo. |
| `floyd_warshall.py` | `FloydWarshall.run(g)` → `AllPairsShortestPaths`: matrizes de distâncias e de predecessores, `distance`, `path(u, v)` e `tree(u)` (a árvore de caminhos mínimos a partir de cada vértice). Para no primeiro D[i][i] < 0 e devolve o ciclo. Recusa, antes de alocar, grafos cujas matrizes passam do limite de memória (`GraphTooLargeError`). |

O Bellman-Ford de todos os pares devolve **o mesmo tipo** (`AllPairsShortestPaths`) que o Floyd-Warshall, o que torna o estudo 4 uma comparação de mesmo escopo. A correção é verificada por 128 testes automatizados (`python3 run.py test`), entre eles: comparação com uma implementação de referência independente, grafos aleatórios com pesos negativos sem ciclo negativo, as 8 combinações de otimizações do Bellman-Ford, Bellman-Ford de todos os pares = Floyd-Warshall, e as engines aceleradas célula a célula contra a versão sequencial.

## 3. Otimizações

**Pedidas no enunciado.** O enunciado não diz quais são "as duas otimizações discutidas em aula" do Bellman-Ford; implementamos as duas clássicas (Kleinberg & Tardos, seções 6.8–6.9, a mesma formulação "até um destino"). **A correspondência exata com a aula não foi confirmada.** Cada uma pode ser desligada para medir seu efeito.

1. **Parada antecipada:** se uma rodada não melhora nenhuma distância, nenhuma posterior melhora. No W_2 o algoritmo parou após 24 rodadas, em vez de n − 1 = 24.999.
2. **Só vértices ativos:** a rodada p só relaxa as arestas dos vértices cuja distância mudou na rodada p − 1. No W_2 foram 2,8·10⁶ relaxamentos (≈ 3,4 m), contra 24 m ≈ 2,0·10⁷ sem essa otimização.
3. **Memória do Floyd-Warshall:** a recorrência usa D<sub>k−1</sub> para obter D<sub>k</sub>, mas a etapa k não altera a linha nem a coluna k. Basta **uma** matriz de distâncias, atualizada no lugar, e uma de predecessores: Θ(n²) de memória, 12(n + 1)² bytes (7,0 GiB para n = 25.000), em vez de uma matriz por etapa.

**Adicionais, por decisão nossa** (não mudam o resultado):

- **Ciclo nos ponteiros de pai** (verificado nas rodadas 1, 2, 4, 8, …). Um ciclo nos pais é sempre negativo. Sem isso, um grafo com ciclo negativo faria n rodadas: no W_1, o ciclo foi achado na rodada 4.
- **Linhas inalcançáveis puladas no Floyd-Warshall.** A etapa k só percorre as linhas i com D[i][k] finito. A quantidade exata dessas linhas é **calculada** por uma busca em Gᵀ: no W_2, 64,1 % de n(n − 1), ou 1,0·10¹³ células.
- **Floyd-Warshall paralelo e compilado.** Na etapa k as linhas são independentes, porque a linha k não muda. Dividi-las entre processos (engine `python`) ou threads (engines `numpy` e `numba`) dá matrizes **idênticas**: mesma soma IEEE-754, mesma comparação estrita e mesma ordem de k.
    - Descartamos as variantes em blocos, que podem trocar o predecessor em caso de empate.
    - NumPy e Numba são dependências **opcionais**, num ambiente virtual separado; sem elas a biblioteca continua só com a biblioteca padrão.
    - A compilação JIT ocorre antes da medição.

## 4. Metodologia experimental

- **Máquina:** AMD Ryzen 7 5700X3D (8 núcleos, 16 threads, L3 de 96 MiB), 31 GiB de RAM, Ubuntu 26.04 (Linux 7.0), CPython 3.14.4; NumPy 2.5.5, Numba 0.68.1 (llvmlite 0.50.0).
- **Grafos** lidos como **direcionados**, em CSR.
    - Só o W_1 tem pesos negativos: 4.998 arestas, de −5,00 a 10,00.
- **Tempo:** `time.perf_counter()` só em volta da chamada do algoritmo, com o coletor de lixo pausado. Leitura e escrita em disco ficam **fora** da medição.
    - Bellman-Ford: o tempo inclui montar Gᵀ.
    - Floyd-Warshall: cada rodada roda num processo próprio, com limite de memória (RLIMIT_AS de 18 GiB).
- **Limites:**
    - Bellman-Ford: 3.600 s por rodada e 4 h por grafo.
    - Floyd-Warshall no W_2: 14.400 s por rodada.
    - Matrizes até 16 GiB; acima disso, o Floyd-Warshall é **recusado** sem alocar.
    - Após um timeout, as rodadas seguintes não rodam. Médias usam **só rodadas concluídas**.
    - Uma parada por ciclo negativo é uma rodada concluída, com esse rótulo.
- **Uma rodada completa serve a três estudos.** Fora do tempo medido, cada rodada do Floyd-Warshall grava os 25 pares do estudo 2 e o *digest* (SHA-1) da matriz de distâncias, usado no estudo 4. O Floyd-Warshall não é repetido.
- **Validação:**
    - Estudo 1: certificado de otimalidade em todas as arestas e comparação com Dijkstra em Gᵀ.
    - Estudo 4: igualdade dos digests das matrizes dos dois algoritmos.
    - Entre estudos (`run.py part3-consistency`): médias só com rodadas concluídas; pares iguais em todas as rodadas; matriz do estudo 2 = rodada do estudo 3; as 25 distâncias do estudo 2 recalculadas com Bellman-Ford; ciclo negativo no estudo 1 ⇔ no Floyd-Warshall; rodadas reaproveitadas no estudo 4 idênticas às do estudo 3.

## 5. Resultados dos estudos de caso

### 5.1 Estudo 1 — Bellman-Ford: distância de 10, 20 e 30 até 100

Uma execução de `to_target` por grafo, destino 100, com as distâncias de 10, 20 e 30 lidas da mesma árvore (**medido**; caminhos completos em `results/part3/bellman_ford/table.md`).

| Grafo | Origem | Distância | Arestas | Caminho (abreviado) | Ciclo negativo | Status |
|---|---|---|---|---|---|---|
| W_1 | 10, 20, 30 | −∞ | – | – | sim: 21005 → 10756 → 21005 (−2,61) | ciclo negativo |
| W_2 | 10 | 10,47 | 11 | 10 → 22754 → 23713 → … → 14144 → 100 | não | ok |
| W_2 | 20 | 8,48 | 6 | 20 → 6795 → 7737 → 11988 → 7094 → 14144 → 100 | não | ok |
| W_2 | 30 | 8,71 | 11 | 30 → 23783 → 439 → … → 14144 → 100 | não | ok |
| W_3 | 10 | 4,63 | 8 | 10 → 2858 → 9370 → … → 74552 → 100 | não | ok |
| W_3 | 20 | 5,42 | 8 | 20 → 2526 → 8495 → … → 74552 → 100 | não | ok |
| W_3 | 30 | 4,67 | 7 | 30 → 29698 → 43059 → … → 74552 → 100 | não | ok |
| W_4 | 10 | 9,04 | 13 | 10 → 91829 → 417272 → … → 351045 → 100 | não | ok |
| W_4 | 20 | 8,83 | 11 | 20 → 775000 → 859374 → … → 351045 → 100 | não | ok |
| W_4 | 30 | 9,23 | 14 | 30 → 124400 → 225008 → … → 351045 → 100 | não | ok |
| W_5 | 10 | 37,85 | 22 | 10 → 8226464 → 8398644 → … → 4484876 → 100 | não | ok |
| W_5 | 20 | 42,63 | 22 | 20 → 8885874 → 9172974 → … → 4484876 → 100 | não | ok |
| W_5 | 30 | 37,86 | 30 | 30 → 792746 → 8357921 → … → 4484876 → 100 | não | ok |

- **W_1:** o ciclo 21005 → 10756 → 21005 (peso −2,61) alcança o destino 100, e as três origens alcançam o ciclo. Por isso as três distâncias são **−∞**: não existe caminho mínimo. Nenhuma distância foi trocada por um valor finito.
    - O algoritmo achou o ciclo na rodada 4, com 16.884 relaxamentos e 0,19 s.
    - A busca no grafo inteiro (`find_negative_cycle`) acha outro ciclo, 10663 → 17332 → 10663 (−2,63).
    - Os 25.000 vértices alcançam um ciclo negativo antes do destino.
- **W_2 a W_5:** sem ciclo negativo e com distâncias finitas. Duas validações independentes passaram:
    - certificado de otimalidade: nenhuma aresta relaxa e cada aresta da árvore é justa;
    - comparação com Dijkstra em Gᵀ, válida porque os pesos são não negativos.
- **Nenhum resultado** ficou inalcançável nem foi interrompido.

### 5.2 Estudo 2 — Floyd-Warshall: distâncias entre &#123;10, 20, 30, 40, 50&#125;

<div class="two" markdown="1"><div markdown="1">

**W_2 — Floyd-Warshall** (linha = origem, coluna = destino; **medido**)

| de \ para | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| **10** | 0,00 | 11,73 | 8,14 | 9,49 | 7,08 |
| **20** | 3,84 | 0,00 | 7,03 | 8,30 | 4,70 |
| **30** | 5,79 | 12,55 | 0,00 | 8,30 | 6,33 |
| **40** | 5,05 | 12,32 | 5,36 | 0,00 | 5,71 |
| **50** | 4,48 | 12,23 | 7,79 | 8,26 | 0,00 |

</div><div markdown="1">

| Grafo | n | Matrizes | Floyd-Warshall |
|---|---|---|---|
| W_1 | 25.000 | 7,0 GiB | **ciclo negativo** na etapa k = 2: 17332 → 2 → 17332 (−0,55); 0,91 s |
| W_2 | 25.000 | 7,0 GiB | ok, 25.000 etapas |
| W_3 | 10⁵ | 111,8 GiB | **recusado por memória** |
| W_4 | 10⁶ | 11.176 GiB | **recusado por memória** |
| W_5 | 10⁷ | 1,1·10⁶ GiB | **recusado por memória** |

</div></div>

- **Origem da matriz do W_2:** é a da rodada 0 do estudo 3. A rodada completa durou 2.760 s com 16 threads, e o Floyd-Warshall não foi executado de novo. As 10 rodadas deram os mesmos 25 pares.
- **Conferência com Bellman-Ford:** as 25 distâncias foram recalculadas com Bellman-Ford até cada um dos 5 vértices. A maior diferença foi 2,7·10⁻¹⁵ (arredondamento de ponto flutuante), e o peso de cada caminho devolvido é igual à sua distância (verificação de consistência, seção 4).
- **W_1:** a matriz não tem significado, porque a distância é −∞ para todos os pares do conjunto.
- **W_3 a W_5:** "Matrizes" é a memória **calculada** das duas matrizes, 12(n + 1)² bytes. O limite configurado é 16 GiB, abaixo dos 31 GiB de RAM e **sem swap**. A máquina não comporta nem a matriz de distâncias do W_3 sozinha (75 GiB).
    - Os valores 5 × 5 desses grafos foram calculados com **Bellman-Ford (não são do Floyd-Warshall)** e estão em `results/part3/floyd_warshall/table.md`.

### 5.3 Estudo 3 — Tempo médio de 10 rodadas (segundos)

| Grafo | n | m | Bellman-Ford até o destino 100 | Floyd-Warshall (todos os pares, Numba, 16 threads) |
|---|---|---|---|---|
| W_1 | 25.000 | 549.953 | 0,1909 ± 0,0012 (10/10) | 0,9098 ± 0,0032 (10/10) — **parou no ciclo negativo** (k = 2) |
| W_2 | 25.000 | 824.964 | 0,5117 ± 0,0027 (10/10) | **2.735,99 ± 8,66 (10/10)** ≈ 45,6 min por rodada |
| W_3 | 100.000 | 6.099.941 | 4,205 ± 0,039 (10/10) | recusado por memória (111,8 GiB) |
| W_4 | 1.000.000 | 30.999.978 | 36,42 ± 0,15 (10/10) | recusado por memória (11.176 GiB) |
| W_5 | 10.000.000 | 39.999.995 | 97,29 ± 0,43 (10/10) | recusado por memória (1,1·10⁶ GiB) |

- **Formato dos tempos:** **medido**, média ± desvio-padrão amostral das rodadas concluídas (concluídas/10). Nenhuma rodada estourou o tempo.
- **Escopos diferentes:** o Bellman-Ford calcula as distâncias de todos até **um** destino, e o tempo inclui montar Gᵀ: 80 % do total no W_1 e 23 % no W_5. O Floyd-Warshall calcula **todos** os pares. A comparação de mesmo escopo é o estudo 4.
- **W_1:** o tempo do Floyd-Warshall é quase todo a alocação das matrizes de 7,0 GiB. O algoritmo parou após processar 2 linhas.
- **W_2:** pico de 7,36 GiB no processo; desvio-padrão de 0,3 % entre as rodadas.
    - Em todas as rodadas foram processadas 400.565.299 linhas, que é a contagem **calculada** de linhas alcançáveis, 64,1 % das 25.000².

### 5.4 Estudo 4 — Todos os pares: Bellman-Ford × Floyd-Warshall

Mesmo escopo: os dois algoritmos devolvem `AllPairsShortestPaths` (matrizes n × n de distâncias e predecessores) e param no primeiro ciclo negativo. Os subgrafos são induzidos pelos vértices 1..N do W_2 (reprodutíveis, gravados em `results/part3/all_pairs/subgraphs/`); **não são grafos oficiais**. Tempo em segundos, média ± desvio-padrão (concluídas/10), **medido** salvo indicação.

| Grafo | n | m | m/n | BF todos os pares (Python, 1 proc.) | FW (Python, 1 proc.) | FW/BF | FW (Numba, 16 threads) | Mesma matriz |
|---|---|---|---|---|---|---|---|---|
| W_2[1..500] | 500 | 307 | 0,6 | 0,0128 ± 0,0001 (10/10) | 0,0291 ± 0,0003 (10/10) | 2,3 | 0,068 ± 0,112 (10/10) | sim |
| W_2[1..1000] | 1.000 | 1.291 | 1,3 | 0,0505 ± 0,0009 (10/10) | 0,280 ± 0,002 (10/10) | 5,5 | 0,033 ± 0,021 (10/10) | sim |
| W_2[1..2000] | 2.000 | 5.360 | 2,7 | 0,521 ± 0,003 (10/10) | 19,07 ± 0,25 (10/10) | 37 | 0,173 ± 0,043 (10/10) | sim |
| W_2[1..3000] | 3.000 | 11.973 | 4,0 | 6,43 ± 0,04 (10/10) | 277,5 ± 1,9 (10/10) | 43 | 1,049 ± 0,065 (10/10) | sim |
| W_2[1..4000] | 4.000 | 21.171 | 5,3 | 20,04 ± 0,18 (10/10) | 1.043,5 ± 47,7 (10/10) | 52 | 3,53 ± 0,14 (10/10) | sim |
| **W_2** | 25.000 | 824.964 | 33 | **7.600,7 (1/10)**; rodadas 1–9 em execução | não executado; **estimado** 150–170 h | ≈ 70–80 (estimado) | **2.735,99 ± 8,66 (10/10)**, do estudo 3 | **sim** |
| **W_1** | 25.000 | 549.953 | 22 | 0,0296 ± 0,0002 (10/10), **ciclo negativo** | não executado | – | 0,9098 ± 0,0032 (10/10), **ciclo negativo** | – |

- **Mesma matriz:** igualdade do SHA-1 da matriz de distâncias. No W_2, o digest da rodada 0 do Bellman-Ford de todos os pares é idêntico ao do Floyd-Warshall do estudo 3. Nos subgrafos, o FW Python e o FW Numba também deram o mesmo digest.
- **W_2, Floyd-Warshall:** as 10 rodadas são as do estudo 3, mesma chamada e mesmo escopo, e não foram repetidas. A versão em Python puro não foi executada: a **estimativa** de 150–170 h vem da calibração (custo por célula medido × 1,0·10¹³ células **calculadas**).
- **W_2, Bellman-Ford:** a rodada 0 levou 2,11 h. Isso é coerente com o estudo 3, em que cada destino custa 0,285 s × 25.000 ≈ 7.100 s (**calculado**). As 9 rodadas restantes ainda estavam rodando na entrega e serão anexadas em `results/part3/all_pairs/grafo_W_2.json`.
- **W_1:** os dois param no primeiro ciclo negativo, e não há matriz de caminhos mínimos para comparar.
    - O Bellman-Ford acha o ciclo 12961 → 22007 → 12961 (−3,23) já na primeira origem.
    - O Floyd-Warshall acha 17332 → 2 → 17332 (−0,55) na etapa k = 2.
    - Os ciclos são diferentes, mas ambos são negativos e existem no grafo.

## 6. Análise e comparação

**Qual algoritmo foi mais eficiente, e por quê.** Para um destino, só o Bellman-Ford se aplica (com pesos negativos, Dijkstra não serve), e ele resolveu todos os grafos, até 10⁷ vértices em 97 s. Para todos os pares, **no mesmo nível de implementação o Bellman-Ford foi mais eficiente em todos os casos medidos**:

- nos subgrafos, de 2,3× (n = 500) a 52× (n = 4.000);
- no W_2, cerca de 70–80× (**estimado**, porque o Floyd-Warshall em Python puro não foi executado).

O motivo é o custo. O Floyd-Warshall faz Θ(n³) atualizações qualquer que seja m: mesmo pulando as linhas inalcançáveis, sobram 1,0·10¹³ células no W_2. O Bellman-Ford de todos os pares custa cerca de n · P · m′, onde:

- P é o número de rodadas até estabilizar, 24 no W_2;
- m′ é o número de arestas dos vértices ativos.

Em grafo esparso, isso é ordens de grandeza menor. No W_2 oficial o Floyd-Warshall terminou antes (2.736 s contra 7.601 s), **mas só porque foi compilado e paralelizado**: a engine Numba com 16 threads é 296× mais rápida que a mesma rotina em Python puro (n = 4.000, medido). Esse ganho é maior que a vantagem algorítmica do Bellman-Ford. Não comparamos um Bellman-Ford compilado; seria a extensão natural.

**Efeito do tamanho e da densidade.**

- **Floyd-Warshall:** de n = 3.000 para 4.000 (n³ × 2,4), o tempo subiu 3,8×. Com mais arestas, mais linhas ficam alcançáveis, e a otimização que pula linhas ajuda menos.
- **Bellman-Ford de todos os pares:** subiu 3,1×. Depende de m e de P, e não de n³.
- **Razão FW/BF:** cresce com n (2,3 → 52). Isso mostra que a vantagem do Bellman-Ford se mantém para os grafos esparsos destes testes: m/n ≤ 33, contra n = 25.000.
- **Grafos densos** (m da ordem de n²): o Bellman-Ford de todos os pares tende a O(n² · m) = O(n⁴) no pior caso, e o Floyd-Warshall voltaria a ser preferível. Não testamos esse regime.
- **Bellman-Ford até um destino:** o número de rodadas cresce devagar com n (24, 25, 36, 42). O tempo segue o número de relaxamentos, com um custo por relaxamento que sobe de 0,10 µs (W_2, W_3) para 0,65 µs (W_5) (**calculado**: tempo de solução ÷ relaxamentos). A causa provável é que, com 10⁷ vértices, os vetores não cabem no cache. Montar Gᵀ responde por 23 % a 80 % do tempo.

**Efeito dos pesos negativos.**

- Pesos negativos impedem o uso de Dijkstra, mas não mudam o custo do Bellman-Ford.
- Ciclos negativos mudam a **resposta**: no W_1, todos os 25.000 vértices alcançam um ciclo, e as distâncias até 100 e entre {10, …, 50} são −∞.
- Os dois algoritmos param cedo, em vez de devolver números sem sentido:
    - o Bellman-Ford na rodada 4, graças à checagem de ciclo nos ponteiros de pai (sem ela, seriam n rodadas);
    - o Floyd-Warshall na etapa k = 2, mas só depois de alocar 7 GiB, o que corresponde a quase todo o 0,91 s.

**Por que o Floyd-Warshall é inviável nos grafos maiores.**

- **Memória primeiro:** 12(n + 1)² bytes. São 112 GiB no W_3, 11 TiB no W_4 e 1,1 PiB no W_5 (**calculado**), contra 31 GiB de RAM. Sem swap, recusamos antes de alocar.
- **Tempo depois:** mesmo com memória suficiente, o W_3 teria 64× as células do W_2. Na proporção medida no W_2, seriam cerca de 49 h por rodada com Numba (**estimado**, supondo a mesma fração de linhas alcançáveis).
- **Bellman-Ford até um destino:** resolve o W_3 em 4,2 s.

**Contribuição das otimizações** (medidas no W_2):

- **Parada antecipada:** 24 rodadas em vez de 24.999.
- **Vértices ativos:** 2,8·10⁶ relaxamentos em vez de 2,0·10⁷.
- **Ciclo nos pais** (adicional): 4 rodadas em vez de 25.000 no W_1.
- **Floyd-Warshall:**
    - a matriz única no lugar é o que permite rodar o W_2 (7 GiB em vez de uma matriz por etapa);
    - pular linhas inalcançáveis evita 35,9 % do trabalho (**calculado**);
    - a engine Numba (adicional) reduz o tempo de 150–170 h (**estimado**) para 45,6 min (**medido**). O resultado é idêntico bit a bit (digest).

## 7. Conclusão

Implementamos grafos direcionados com pesos, Bellman-Ford até um destino (com parada antecipada, vértices ativos e detecção de ciclo negativo) e Floyd-Warshall com uma única matriz.

- Os estudos 1 a 3 foram executados por completo nos cinco grafos oficiais. O estudo 4 foi executado nos subgrafos e no W_1; no W_2, o Bellman-Ford de todos os pares tem 1 de 10 rodadas concluída na data deste relatório.
- **Correção:** 28 verificações cruzadas passaram (`results/part3/consistency.md`). Entre elas, as matrizes idênticas nos dois algoritmos, em todos os casos em que ambos terminaram.
- **Conclusão principal:** para grafos esparsos como os do trabalho, o Bellman-Ford otimizado é a escolha certa.
    - Para um destino, é o único viável com pesos negativos e escala até 10⁷ vértices.
    - Para todos os pares, ganha do Floyd-Warshall no mesmo nível de implementação.
    - O Floyd-Warshall esbarra na memória Θ(n²) antes do tempo Θ(n³), e só é viável em n = 25.000 graças à aceleração compilada.
- **Limitações:**
    - não confirmamos se as duas otimizações correspondem às da aula;
    - a comparação no W_2 oficial envolve níveis de implementação diferentes (dito explicitamente);
    - os subgrafos induzidos são mais esparsos que o W_2;
    - a estimativa do Floyd-Warshall em Python puro não é medição.

Código, resultados e scripts de reprodução: https://github.com/nunoduartte/cos242-graph.
