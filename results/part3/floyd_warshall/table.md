**grafo_W_1** — linha = origem, coluna = destino; calculado com Bellman-Ford (Floyd-Warshall: negative cycle)

| de \ para | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| **10** | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) |
| **20** | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) |
| **30** | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) |
| **40** | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) |
| **50** | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) | −∞ (ciclo negativo) |

**grafo_W_2** — linha = origem, coluna = destino; calculado com Floyd-Warshall (estudo 3, rodada 0 (results/part3/benchmark/grafo_W_2.json); pares iguais em 10/10 rodadas)

| de \ para | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| **10** | 0,00 | 11,73 | 8,14 | 9,49 | 7,08 |
| **20** | 3,84 | 0,00 | 7,03 | 8,30 | 4,70 |
| **30** | 5,79 | 12,55 | 0,00 | 8,30 | 6,33 |
| **40** | 5,05 | 12,32 | 5,36 | 0,00 | 5,71 |
| **50** | 4,48 | 12,23 | 7,79 | 8,26 | 0,00 |

**grafo_W_3** — linha = origem, coluna = destino; calculado com Bellman-Ford (Floyd-Warshall: não executado: n = 100000 exige 111.8 GiB nas duas matrizes (limites: 16 GiB, 25000 vértices))

| de \ para | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| **10** | 0,00 | 4,99 | 5,71 | 7,49 | 4,31 |
| **20** | 3,48 | 0,00 | 6,19 | 8,27 | 4,32 |
| **30** | 3,96 | 5,80 | 0,00 | 8,30 | 3,17 |
| **40** | 3,58 | 5,59 | 6,10 | 0,00 | 3,84 |
| **50** | 3,25 | 5,41 | 6,12 | 8,10 | 0,00 |

**grafo_W_4** — linha = origem, coluna = destino; calculado com Bellman-Ford (Floyd-Warshall: não executado: n = 1000000 exige 11,175.9 GiB nas duas matrizes (limites: 16 GiB, 25000 vértices))

| de \ para | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| **10** | 0,00 | 10,52 | 10,15 | 10,69 | 8,24 |
| **20** | 7,79 | 0,00 | 9,19 | 9,67 | 7,58 |
| **30** | 7,61 | 10,25 | 0,00 | 8,77 | 6,55 |
| **40** | 7,94 | 8,65 | 9,22 | 0,00 | 7,75 |
| **50** | 7,99 | 11,41 | 8,80 | 8,55 | 0,00 |

**grafo_W_5** — linha = origem, coluna = destino; calculado com Bellman-Ford (Floyd-Warshall: não executado: n = 10000000 exige 1,117,587.3 GiB nas duas matrizes (limites: 16 GiB, 25000 vértices))

| de \ para | 10 | 20 | 30 | 40 | 50 |
|---|---|---|---|---|---|
| **10** | 0,00 | 40,20 | 39,56 | 41,55 | 44,91 |
| **20** | 39,17 | 0,00 | 39,98 | 49,82 | 45,16 |
| **30** | 34,46 | 42,64 | 0,00 | 47,04 | 43,85 |
| **40** | 38,73 | 43,91 | 47,30 | 0,00 | 45,24 |
| **50** | 44,06 | 40,62 | 45,25 | 49,11 | 0,00 |

| Grafo | n | Matrizes (GiB) | Floyd-Warshall | Tempo FW (s) | Etapa k alcançada | Ciclo negativo |
|---|---|---|---|---|---|---|
| grafo_W_1 | 25000 | 6.99 | negative cycle | 0.9 | 2 | sim (2 arestas, etapa k = 2) |
| grafo_W_2 | 25000 | 6.99 | ok | 2760.2 | 25000 | - |
| grafo_W_3 | 100000 | 111.76 | não executado: n = 100000 exige 111.8 GiB nas duas matrizes (limites: 16 GiB, 25000 vértices) | - | - | - |
| grafo_W_4 | 1000000 | 11175.89 | não executado: n = 1000000 exige 11,175.9 GiB nas duas matrizes (limites: 16 GiB, 25000 vértices) | - | - | - |
| grafo_W_5 | 10000000 | 1117587.31 | não executado: n = 10000000 exige 1,117,587.3 GiB nas duas matrizes (limites: 16 GiB, 25000 vértices) | - | - | - |
