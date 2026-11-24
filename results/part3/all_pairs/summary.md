| Grafo | n | m | Bellman-Ford, todos os pares (s) | Floyd-Warshall (s) | FW / BF | Mesmas distâncias |
|---|---|---|---|---|---|---|
| grafo_W_1 | 25000 | 549953 | 0.0296 ± 0.0002 (10/10) | 0.9098 ± 0.0032 (10/10) | 30.69 | - |
| grafo_W_2 | 25000 | 824964 | 7600.7415 (1/1) | não executado | - | - |
| grafo_W_2_1-1000 | 1000 | 1291 | 0.0505 ± 0.0009 (10/10) | 0.2801 ± 0.0019 (10/10) | 5.54 | sim |
| grafo_W_2_1-2000 | 2000 | 5360 | 0.5214 ± 0.0026 (10/10) | 19.0694 ± 0.2520 (10/10) | 36.57 | sim |
| grafo_W_2_1-3000 | 3000 | 11973 | 6.4328 ± 0.0439 (10/10) | 277.5182 ± 1.8611 (10/10) | 43.14 | sim |
| grafo_W_2_1-4000 | 4000 | 21171 | 20.0368 ± 0.1763 (10/10) | 1043.4855 ± 47.7235 (10/10) | 52.08 | sim |
| grafo_W_2_1-500 | 500 | 307 | 0.0128 ± 0.0001 (10/10) | 0.0291 ± 0.0003 (10/10) | 2.27 | sim |

Média ± desvio-padrão amostral das rodadas concluídas (concluídas/rodadas). Mesmo escopo: matriz n x n de distâncias e de predecessores. Estimativas, não medições: extrapolação (Bellman-Ford) = tempo até a interrupção x n / origens concluídas; limite superior (Floyd-Warshall) = tempo até a interrupção + etapas restantes x (n - 1) linhas x (n + 1) células x custo por célula medido.
