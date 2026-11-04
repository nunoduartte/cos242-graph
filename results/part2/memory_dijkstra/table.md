| Grafo | Estratégia | Grafo carregado (MB) | RSS antes (MB) | Pico RSS (MB) | Aumento observado (MB) | Tempo (s) | Status |
|---|---|---|---|---|---|---|---|
| grafo_W_3 | vector | 145 | 162 | 167 | 5 | 159.36 | ok |
| grafo_W_3 | heap | 145 | 162 | 171 | 9 | 1.61 | ok |

Aumento observado = pico de RSS durante a chamada de Dijkstra menos o RSS imediatamente antes (grafo já carregado). É uma aproximação da memória adicional do algoritmo: inclui o resultado (distâncias e pais) e o que o alocador do Python reteve, e não é o tamanho exato das estruturas.
