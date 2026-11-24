| Grafo | n | m | Bellman-Ford, todos os pares (s) | Floyd-Warshall (s) | FW / BF | Mesmas distâncias |
|---|---|---|---|---|---|---|
| grafo_W_2_1-1000 | 1000 | 1291 | não executado | 0.0325 ± 0.0205 (10/10) | - | - |
| grafo_W_2_1-2000 | 2000 | 5360 | não executado | 0.1733 ± 0.0434 (10/10) | - | - |
| grafo_W_2_1-3000 | 3000 | 11973 | não executado | 1.0490 ± 0.0650 (10/10) | - | - |
| grafo_W_2_1-4000 | 4000 | 21171 | não executado | 3.5272 ± 0.1444 (10/10) | - | - |
| grafo_W_2_1-500 | 500 | 307 | não executado | 0.0682 ± 0.1122 (10/10) | - | - |

Média ± desvio-padrão amostral das rodadas concluídas (concluídas/rodadas). Mesmo escopo: matriz n x n de distâncias e de predecessores. Estimativas, não medições: extrapolação (Bellman-Ford) = tempo até a interrupção x n / origens concluídas; limite superior (Floyd-Warshall) = tempo até a interrupção + etapas restantes x (n - 1) linhas x (n + 1) células x custo por célula medido.
