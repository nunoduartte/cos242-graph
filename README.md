# cos242-graph

Biblioteca de grafos não direcionados em Python (apenas a biblioteca padrão) para o trabalho de
Teoria dos Grafos (COS242/UFRJ).

- **Parte 1:** leitura de arquivos, lista e matriz de adjacência, BFS, DFS, distâncias, diâmetro
  e componentes conexas.
- **Parte 2:** grafos com pesos, representação compacta (CSR) para grafos grandes e Dijkstra com
  vetor ou heap (um único núcleo, com a fila de prioridade injetada).

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
with negative weights are not implemented yet"), como pede o enunciado.

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
```

Os JSON registram a seed, k, as origens sorteadas, os limites, o tempo de carga, a memória e o
ambiente (CPU, RAM, versão do Python).

## Documentação

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): arquitetura, decisões e complexidades.
- [`docs/relatorio_parte2.md`](docs/relatorio_parte2.md): rascunho do relatório (até 5 páginas).
- [`docs/apresentacao_parte2.md`](docs/apresentacao_parte2.md): roteiro da apresentação (8 min).

## Parte 1

```bash
python3 case_study.py ../grafo_1.txt [--matrix] [--exact-diameter]
python3 run_all.py --dir ..        # todos os grafos da Parte 1 -> results/
```
