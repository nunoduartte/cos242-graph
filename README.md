# cos242-graph

Biblioteca de grafos em Python (apenas a biblioteca padrão) para o trabalho de Teoria dos Grafos
(COS242/UFRJ).

- **Parte 1:** leitura de arquivos, lista e matriz de adjacência, BFS, DFS, distâncias, diâmetro
  e componentes conexas.
- **Parte 2:** grafos com pesos, representação compacta (CSR) para grafos grandes e Dijkstra com
  vetor ou heap (um único núcleo, com a fila de prioridade injetada).
- **Parte 3:** grafos direcionados (BFS, DFS e Dijkstra seguem a direção), Bellman-Ford de todos
  os vértices até um destino (pesos negativos, ciclos negativos, otimizações) e Floyd-Warshall
  (todos os pares, matriz única atualizada no lugar).

Requisitos: Python 3.10+ (testado em 3.14). Não há dependências externas nem etapa de compilação;
`run.py` é o ponto de entrada único para testes e estudos de caso.

## Uso da biblioteca

```python
from graphs import Graph, GraphReader, Dijkstra, VectorQueue, IndexedMinHeap

g = GraphReader.read("grafo_W_3.txt", "csr")   # "list" | "matrix" | "csr"; pesos detectados pela 3ª coluna
r = Dijkstra(IndexedMinHeap).run(g, 10)        # ou Dijkstra(VectorQueue)
r.distance_to(20), r.path_to(20)               # distância e caminho [10, ..., 20]; inf e None se inalcançável

g = Graph(5, [(1, 2, 0.1), (2, 5, 0.2), (1, 5, 1.0)], "list", weighted=True)
g.weight(1, 2), g.shortest_path(1, 5)          # 0.1, (0.30000000000000004, [1, 2, 5])
```

Um grafo com qualquer peso negativo faz Dijkstra lançar `NegativeWeightError` ("shortest paths
with negative weights are not implemented yet"), como pede o enunciado da Parte 2.

### Parte 3: grafos direcionados, Bellman-Ford e Floyd-Warshall

```python
from graphs import GraphReader, BellmanFord, FloydWarshall

g = GraphReader.read("grafo_W_1.txt", "csr", directed=True)  # "u v w" = só a aresta u -> v
r = BellmanFord().to_target(g, 100)     # de TODOS os vértices até 100 (pesos negativos permitidos)
r.distance_from(10), r.path_from(10)    # -inf se 10 alcança um ciclo negativo que alcança 100
r.negative_cycle                        # None, ou o ciclo [c0, c1, ..., c0] encontrado
BellmanFord().find_negative_cycle(g)    # qualquer ciclo negativo do grafo, onde quer que esteja

small = GraphReader.read("pequeno.txt", "list", directed=True)
fw = FloydWarshall().run(small)         # recusa n > 3000 por padrão (GraphTooLargeError)
FloydWarshall(workers=16).run(small)    # mesmas matrizes, linhas de cada etapa em 16 processos
FloydWarshall(engine="numba", workers=16).run(small)  # opcional (NumPy + Numba): mesmas matrizes
fw.distance(1, 2), fw.path(1, 2), fw.tree(1)   # tree(1) = árvore de caminhos mínimos a partir de 1
fw.negative_cycle                       # com ciclo negativo, distance() lança NegativeCycleError
BellmanFord().all_pairs(small)          # mesmo resultado (AllPairsShortestPaths), n execuções
```

Sem `directed=True` tudo continua como nas Partes 1 e 2 (grafo não direcionado). Em grafo
direcionado, `neighbors(u)` são os vizinhos de saída e `degree(u)` é o grau de saída; componentes
conexas e diâmetro (Parte 1) recusam grafos direcionados.

## Testes

```bash
python3 run.py test               # tudo (unidade + integração)
python3 run.py test-unit          # regressão da Parte 1, grafos ponderados, filas e Dijkstra
python3 run.py test-integration   # scripts de experimento ponta a ponta em arquivos pequenos gerados
python3 -m unittest discover -s tests -t .   # equivalente, direto no unittest
```

## Estudos de caso da Parte 2

Os arquivos do professor ficam fora do repositório. Por padrão são lidos de `../T2`
(altere com `--data-dir` ou com a variável de ambiente `DATA_DIR`) e nunca são modificados.

```bash
python3 run.py shortest-paths     # A: distância e caminho de 10 até 20, 30, 40, 50, 60 em grafo_W_3..7
python3 run.py benchmark          # B: vetor x heap, k=100 origens, seed 42
python3 run.py collaboration      # C: Edsger W. Dijkstra até os 5 pesquisadores
python3 run.py report             # junta tudo em results/part2/report/
python3 run.py studies            # A + C + B + report
python3 run.py studies --skip-benchmark            # sem o benchmark (marcado como pendente no relatório)
python3 run.py benchmark --graphs grafo_W_3 --k 10 --budget 600 --run-timeout 300
python3 run.py shortest-paths --validate-timeout 0 # sem a validação cruzada com o vetor
```

Os argumentos depois do nome do estudo vão direto para o script
(`python3 -m experiments.benchmark --help` lista todos).

### Benchmarks longos

O Dijkstra com vetor é O(n²). Em Python puro, uma execução no grafo_W_3 (n = 10⁵) leva cerca de
2,5 min, e do grafo_W_4 em diante leva horas ou dias. Por isso o benchmark tem dois limites:

- `--run-timeout` (padrão 900 s): limite de cada execução. Ao estourar, a execução é interrompida (SIGALRM),
  registrada como `timeout (> X s)`, e as demais origens daquela estratégia não são executadas.
- `--budget` (padrão 1200 s): tempo máximo somado por (grafo, estratégia). Uma execução também não
  começa se o que resta do orçamento for menor que a mais longa já concluída. As origens que não couberem ficam como
  `not run (budget)`.

Cada execução é gravada assim que termina. Um benchmark interrompido continua de onde parou, com
as mesmas configurações, sem repetir execuções:

```bash
python3 run.py benchmark --resume
# benchmark (retomável) + estudo A com validações + relatório, desacoplado do terminal:
setsid nohup python3 run.py pipeline > results/part2/pipeline.log 2>&1 < /dev/null &
```

Nada é estimado. A média usa só as execuções concluídas, e o speedup só usa as origens concluídas
pelas duas estratégias. `runs.csv` guarda cada execução individual.

### Experimentos de memória (separados do benchmark de tempo)

Cada medição roda em um processo Python próprio, como na Parte 1, para que alocações anteriores não
contaminem a próxima. O pico de RSS vem do contador do kernel (`VmHWM`), zerado imediatamente antes
do trecho medido (`/proc/self/clear_refs`), então ele é observado de fato durante o algoritmo, e
não confundido com o RSS final. Se o kernel não permitir zerar, há uma amostragem a cada 5 ms
(registrada no campo `peak_method`).

```bash
# memória adicional de Dijkstra: vetor x heap, mesma origem (10), grafo_W_3
python3 run.py memory-dijkstra
# opcional: peso exato dos objetos Python do algoritmo (tracemalloc; o tempo fica inflado)
python3 run.py memory-dijkstra --strategies heap vector --tracemalloc
# grafos maiores só com heap (o vetor não termina): uma origem por grafo, limite de 900 s
python3 run.py memory-dijkstra --graphs grafo_W_4 grafo_W_5 grafo_W_6 grafo_W_7 --strategies heap
# lista x matriz x CSR: subgrafos induzidos por 1..N do grafo_W_3 + o grafo_W_3 inteiro
python3 run.py memory-representations
```

Limitações: o RSS é do processo inteiro. O aumento observado inclui o resultado (distâncias e pais)
e a memória que o alocador do Python reteve, então é uma aproximação, não o tamanho exato das
estruturas. A matriz não é construída quando 9(n+1)² bytes passam de `--matrix-max-gb` (4 GiB por
padrão). Cada processo tem um limite de espaço de endereçamento (`--max-memory-gb`, 20 por padrão).

## Estudos de caso da Parte 3

Os grafos `grafo_W_1..5.txt` ficam fora do repositório e nunca são modificados. Os scripts leem de
`../T3` por padrão; use `--data-dir` (ou `DATA_DIR_P3`). Todos os grafos são lidos como
**direcionados** (`--undirected` muda isso). Os resultados vão para `results/part3/`;
`results/part2/` não é tocado.

```bash
D=~/Downloads/graphs
python3 run.py test                                       # 128 testes (Partes 1, 2 e 3)
python3 run.py part3-bellman-ford   --data-dir $D         # 1: distância de 10, 20, 30 até 100
python3 run.py part3-floyd-warshall --data-dir $D         # 2: matriz 5 x 5 de {10, 20, 30, 40, 50}
python3 run.py part3-benchmark      --data-dir $D         # 3: 10 rodadas de cada algoritmo
python3 run.py part3-all-pairs      --data-dir $D         # 4: Bellman-Ford todos os pares x Floyd-Warshall
python3 run.py part3-report                               # consolida em results/part3/report/
python3 run.py part3-studies        --data-dir $D         # 1, 2, 3, 4 e o relatório, em sequência
python3 run.py part3-consistency    --data-dir $D         # verificações cruzadas entre os estudos
```

Execução oficial usada no relatório (uma etapa pesada por vez, todas retomáveis; logs em
`results/part3/logs/`): `experiments/part3/official_runs.sh ETAPA`, com ETAPA em `study1`,
`study3-bf`, `study3-fw-small`, `study3-fw-w2`, `study2`, `study4-sub`, `study4-sub-numba`,
`study4-official`, `report`, `consistency`. Relatório e apresentação são gerados a partir dos
resultados (precisam de `markdown` e `python-pptx` no ambiente virtual, e de Chrome/Chromium para o PDF):

```bash
~/.venvs/cos242-accel/bin/python docs/build_report_pdf.py     # docs/relatorio_parte3.md -> .pdf (≤ 5 páginas)
~/.venvs/cos242-accel/bin/python docs/build_presentation.py   # docs/apresentacao_parte3.pptx
```

Opções úteis (`python3 -m experiments.part3.<estudo> --help` lista todas):

```bash
python3 run.py part3-bellman-ford --data-dir $D --graphs grafo_W_1 grafo_W_2 --target 100 --sources 10 20 30
python3 run.py part3-floyd-warshall --data-dir $D --graphs grafo_W_1 --timeout 3600 --max-memory-gb 16
python3 run.py part3-benchmark --data-dir $D --rounds 10 --run-timeout 1800 --budget 7200 --resume
python3 run.py part3-benchmark --data-dir $D --algorithms bellman-ford --graphs grafo_W_4 grafo_W_5
python3 run.py part3-all-pairs --data-dir $D --graphs grafo_W_1 --subgraphs grafo_W_2:500,1000,2000,3000,4000
# longo: desacoplado do terminal, retomável com --resume
mkdir -p results/part3 && setsid nohup python3 run.py part3-benchmark --data-dir $D --resume > results/part3/benchmark.log 2>&1 < /dev/null &
```

Floyd-Warshall no W_2 (n = 25.000): calibre antes de rodar o estudo completo. A calibração conta
exatamente quantas linhas cada etapa processa, mede alguns minutos de execução real e estima o
tempo de uma rodada (estimativa rotulada como tal, em `results/part3/calibration/`):

```bash
python3 run.py part3-fw-calibrate --data-dir $D --graph grafo_W_2 --workers 16 --budget 600
# engine acelerada opcional (NumPy + Numba; mesmas matrizes, ver docs/EXPLICACAO_PARTE3.md, D.9):
# PY = python de um ambiente virtual com numpy e numba instalados; sem eles, use a engine python
$PY run.py part3-fw-calibrate --data-dir $D --graph grafo_W_2 --engine numba --workers 16 --budget 600
# limites maiores só para o W_2 (os outros grafos mantêm os padrões); --fw-workers = processos por etapa
python3 run.py part3-floyd-warshall --data-dir $D --graphs grafo_W_2 --timeout-for grafo_W_2=172800
python3 run.py part3-benchmark --data-dir $D --graphs grafo_W_2 --algorithms floyd-warshall \
  --fw-timeout-for grafo_W_2=172800 --fw-budget-for grafo_W_2=0 --resume
```

Limites de segurança: o Floyd-Warshall (e o Bellman-Ford de todos os pares, que devolve as mesmas
matrizes) não roda quando as duas matrizes, 12(n+1)² bytes, passam de `--max-memory-gb` (16 por
padrão) ou n passa de `--max-vertices`. O registro diz por quê. Cada rodada desses dois roda num
processo próprio, com limite de memória e de tempo (`--run-timeout`), e cada par (grafo, algoritmo)
tem um orçamento (`--budget`). Depois de um timeout ou de uma recusa, as rodadas seguintes ficam
como `not run`. Toda rodada é gravada quando termina, e `--resume` continua de onde parou.

## Resultados

```
results/            Parte 1 (inalterada)
results/part2/
  shortest_paths/   <grafo>.json, table.csv, table.md   (estudo A)
  benchmarks/       <grafo>.json, runs.csv, summary.csv, summary.md   (estudo B)
  collaboration/    result.json, table.csv, table.md   (estudo C)
  memory_dijkstra/  runs.json, runs.csv, table.md   (memória vetor x heap)
  representations/  runs.json, runs.csv, table.md, subgraphs/   (lista x matriz x CSR)
  report/           results.md (estudos A-C e Tabelas A-D), benchmark.svg, representations.svg,
                    construction_peak.svg, status.json   (consolidado; só lê os resultados)
results/part3/
  bellman_ford/     <grafo>.json, table.csv, table.md   (estudo 1)
  floyd_warshall/   <grafo>.json, table.md   (estudo 2)
  benchmark/        <grafo>.json, runs.csv, summary.csv, summary.md   (estudo 3)
  all_pairs/        <grafo>.json, summary.csv, summary.md, subgraphs/   (estudo 4)
  calibration/      fw_<grafo>_p<P>.json, .md   (calibração do Floyd-Warshall; estimativas rotuladas)
  report/           results.md, all_pairs.svg, status.json   (consolidado)
```

Os JSON registram a seed, k, as origens sorteadas, os limites, o tempo de carga, a memória e o
ambiente (CPU, RAM, versão do Python).

## Documentação

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): arquitetura, decisões e complexidades.
- [`docs/relatorio_parte2.md`](docs/relatorio_parte2.md): rascunho do relatório (até 5 páginas).
- [`docs/apresentacao_parte2.md`](docs/apresentacao_parte2.md): roteiro da apresentação (8 min).
- [`docs/EXPLICACAO_PARTE3.md`](docs/EXPLICACAO_PARTE3.md): explicação didática da Parte 3.
- [`docs/relatorio_parte3.md`](docs/relatorio_parte3.md) e
  [`docs/apresentacao_parte3.md`](docs/apresentacao_parte3.md): estrutura do relatório e da
  apresentação da Parte 3 (preenchidos depois dos experimentos).

## Parte 1

```bash
python3 case_study.py ../grafo_1.txt [--matrix] [--exact-diameter]
python3 run_all.py --dir ..        # todos os grafos da Parte 1 -> results/
```
