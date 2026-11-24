| Grafo | n | m | Bellman-Ford até o destino (s) | Floyd-Warshall (s) |
|---|---|---|---|---|
| grafo_W_1 | 25000 | 549953 | 0.1909 ± 0.0012 (10/10) | 0.9098 ± 0.0032 (10/10) |
| grafo_W_2 | 25000 | 824964 | 0.5117 ± 0.0027 (10/10) | 2735.9881 ± 8.6573 (10/10) |
| grafo_W_3 | 100000 | 6099941 | 4.2049 ± 0.0387 (10/10) | refused: n = 100000 needs 111.8 GiB for the matrices (limits 16 GiB, 25000 vertices) |
| grafo_W_4 | 1000000 | 30999978 | 36.4215 ± 0.1478 (10/10) | refused: n = 1000000 needs 11,175.9 GiB for the matrices (limits 16 GiB, 25000 vertices) |
| grafo_W_5 | 10000000 | 39999995 | 97.2871 ± 0.4251 (10/10) | refused: n = 10000000 needs 1,117,587.3 GiB for the matrices (limits 16 GiB, 25000 vertices) |

grafo_W_2: distâncias e caminhos do estudo 2 iguais nas 10 rodadas do Floyd-Warshall: sim

Média ± desvio-padrão amostral das rodadas concluídas (concluídas/rodadas). Escopos diferentes: Bellman-Ford calcula as distâncias de todos os vértices até um destino; Floyd-Warshall, todos os pares.
