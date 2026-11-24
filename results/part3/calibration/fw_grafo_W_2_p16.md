# Calibração do Floyd-Warshall: grafo_W_2 (16 processos)

- n = 25,000, m = 824,964; matrizes: 6.99 GiB; pico de RSS do processo principal: 7.03 GiB
- **Trabalho exato (contagem, não estimativa):** 400,565,299 linhas processadas no total (64.1% de n(n−1)), 1.001e+13 células; contado em 42 s
- **Medido:** 603 s de execução real, etapas 1..3,095 de 25,000, 0.813% do trabalho; linhas por etapa iguais à contagem exata: sim
- **Modelo de custo (ajustado nas etapas 2837..3095, média de 3,875 linhas por etapa):** 9.26 ns por célula, 0.00 ms fixos por etapa
- **Estimativa (não é medição):** 25.7 h por rodada; 257 h (10.7 dias) para 10 rodadas

Suposição: o custo por linha medido no fim da calibração vale para as etapas restantes.
