| Grafo/subgrafo | Vértices | Arestas | Representação | Tempo de carga (s) | Memória (MB) | Pico na construção (MB) | Status |
|---|---|---|---|---|---|---|---|
| grafo_W_3_1-2000 | 2.000 | 2.396 | list | 0.01 | 1 | 1 | ok |
| grafo_W_3_1-2000 | 2.000 | 2.396 | matrix | 0.02 | 37 | 37 | ok |
| grafo_W_3_1-2000 | 2.000 | 2.396 | csr | 0.00 | 1 | 0 | ok |
| grafo_W_3_1-5000 | 5.000 | 15.033 | list | 0.03 | 2 | 2 | ok |
| grafo_W_3_1-5000 | 5.000 | 15.033 | matrix | 0.15 | 228 | 228 | ok |
| grafo_W_3_1-5000 | 5.000 | 15.033 | csr | 0.02 | 1 | 1 | ok |
| grafo_W_3_1-10000 | 10.000 | 61.193 | list | 0.11 | 4 | 4 | ok |
| grafo_W_3_1-10000 | 10.000 | 61.193 | matrix | 0.51 | 900 | 900 | ok |
| grafo_W_3_1-10000 | 10.000 | 61.193 | csr | 0.09 | 3 | 5 | ok |
| grafo_W_3_1-20000 | 20.000 | 244.168 | list | 0.41 | 14 | 14 | ok |
| grafo_W_3_1-20000 | 20.000 | 244.168 | matrix | 2.12 | 3.515 | 3.515 | ok |
| grafo_W_3_1-20000 | 20.000 | 244.168 | csr | 0.36 | 15 | 24 | ok |
| grafo_W_3 | 100.000 | 6.099.868 | list | 11.02 | 222 | 222 | ok |
| grafo_W_3 | 100.000 | - | matrix | - | - | - | not built: needs ~83.8 GiB > --matrix-max-gb |
| grafo_W_3 | 100.000 | 6.099.868 | csr | 9.12 | 144 | 377 | ok |

Memória = RSS após a carga menos o RSS do processo antes da carga (mesma medida da Parte 1). Pico na construção = maior RSS durante leitura + construção menos o mesmo ponto de partida; inclui buffers temporários (por exemplo, a lista de arestas antes da CSR).
