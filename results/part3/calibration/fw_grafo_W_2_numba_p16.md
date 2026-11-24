# Calibração do Floyd-Warshall: grafo_W_2, engine numba (16 threads)

- n = 25,000, m = 824,964; matrizes: 6.99 GiB; pico de RSS do processo principal: 7.15 GiB
- **Trabalho exato (contagem, não estimativa):** 400,565,299 linhas processadas no total (64.1% de n(n−1)), 1.001e+13 células; contado em 42 s
- **Medido:** 600 s de execução real, etapas 1..10,093 de 25,000, 18.763% do trabalho; linhas por etapa iguais à contagem exata: sim
- **Modelo de custo (ajustado nas etapas 8244..10093, média de 14,371 linhas por etapa):** 0.32 ns por célula, 0.00 ms fixos por etapa
- **Estimativa (não é medição):** 0.9 h por rodada; 9 h (0.4 dias) para 10 rodadas

Suposição: o custo por linha medido no fim da calibração vale para as etapas restantes.
