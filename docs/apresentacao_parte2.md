# Roteiro da apresentação – Trabalho Parte 2 (≈ 7 minutos)

Dupla: Nuno Correia e Nicolas Viana. Este roteiro acompanha a versão definitiva dos slides: o arquivo
`docs/apresentacao_parte2.pptx` (12 slides) e o deck web, com as mesmas notas de fala. Divisão sugerida:
Nuno nos slides 1 a 6 e Nicolas nos slides 7 a 12.

Tempo total das notas: 7 min 05 s, com folga para o limite de 8 minutos. Todos os números vêm de
`results/part2/` (consolidados em `results/part2/report/results.md`); os pesos dos três caminhos desenhados
(slides 5 e 6) foram lidos dos arquivos de entrada e somam exatamente as distâncias publicadas. Ao falar,
diga o tipo de cada número: **medido**, **limite inferior**, **extrapolação teórica** ou **hipótese**.

| Slide | Título | Tempo |
|---|---|---|
| 1 | Capa | 0:15 |
| 2 | O pedido e a escala dos dados | 0:20 |
| 3 | Representação e fila são estratégias independentes | 0:45 |
| 4 | Um laço de relaxamento, duas filas | 0:35 |
| 5 | Distância mínima de 10 até 20, 30, 40, 50 e 60 | 0:40 |
| 6 | Mais arestas não significa mais longe | 0:45 |
| 7 | Tempo médio de Dijkstra por origem (s, escala log) | 0:40 |
| 8 | Quatro tipos de número, sempre identificados | 0:45 |
| 9 | Dijkstra custa pouco perto do grafo | 0:30 |
| 10 | A matriz cresce com n²; lista e CSR, com n + m | 0:30 |
| 11 | Trade-off da CSR: menos memória, pico maior | 0:40 |
| 12 | O que os experimentos mostram, e até onde | 0:40 |

## 1. Capa (0:15)

**Na tela:** Título, dupla e link do repositório.

**Fala:** Apresentar a dupla. Mostramos como estendemos a biblioteca da Parte 1 para grafos com pesos e Dijkstra, e o que medimos em grafos de até 50 milhões de vértices. Ao longo da fala, dizemos sempre se um número é medido, um limite inferior, uma extrapolação ou uma hipótese.

## 2. O pedido e a escala dos dados (0:20)

**Na tela:** Quatro números: 5 grafos, 5·10⁷ vértices (W_7), 73,4 mi arestas (W_6), 722 mil pesquisadores.

**Fala:** O enunciado pede pesos reais, distância e caminho mínimo, e Dijkstra com vetor e com heap sem implementar o algoritmo duas vezes. A dificuldade é a escala: até 50 milhões de vértices e 73 milhões de arestas, em Python puro.

## 3. Representação e fila são estratégias independentes (0:45)

**Na tela:** Código `GraphReader.read(arq, representation="csr")` + `Dijkstra(IndexedMinHeap).run(g, 10)`; tabela 3 × 2 das combinações (todas testadas; usadas nos estudos: CSR+heap, CSR+vetor, lista+heap).

**Fala:** A arquitetura tem dois eixos independentes. Por composição, o Graph contém uma Representation, escolhida por nome: lista, matriz ou CSR. Pelo padrão Strategy, o Dijkstra recebe a classe da fila: vetor ou heap. Um não conhece o outro. A tabela mostra o resultado: as seis combinações rodam o mesmo código e todas são testadas, inclusive contra Floyd-Warshall. Nos estudos usamos três delas: CSR com heap e com vetor nos grafos grandes, e lista com heap na rede de colaboração. Foi essa separação que permitiu acrescentar a CSR sem tocar em nenhum algoritmo.

## 4. Um laço de relaxamento, duas filas (0:35)

**Na tela:** O laço de Dijkstra com `pop_min`, `insert` e `decrease_key` destacados; tabela de complexidades; faixa de validação (certificado, vetor = heap no W_3, 66 testes).

**Fala:** Este é o único laço de Dijkstra. As três operações destacadas são o contrato da fila. Com o vetor, pop_min varre o vetor inteiro: O(n² + m). Com o heap indexado, pos[v] localiza o vértice e decrease_key custa O(log n), sem entradas duplicadas. Correção: certificado de otimalidade em todas as arestas dos cinco grafos, vetor e heap idênticos no W_3, e 66 testes.

## 5. Distância mínima de 10 até 20, 30, 40, 50 e 60 (0:40)

**Na tela:** Tabela dos 5 grafos; caminho completo do W_3, 10 → 50, com o peso de cada aresta (0,16 + 0,06 + 0,23 + 0,08 + 0,08 + 0,11 + 0,07 + 0,05 + 0,03 = 0,87).

**Fala:** Estudo 1: distâncias do vértice 10 até 20, 30, 40, 50 e 60; entre parênteses, o número de arestas. Embaixo, um caminho completo do W_3, de 10 até 50: nove arestas, com o peso de cada uma. A soma dos pesos, 0,87, é a distância da tabela. Repare que o caminho tem 9 arestas, enquanto outros destinos no mesmo grafo precisam de até 18: o que se minimiza é a soma dos pesos, não o número de saltos.

## 6. Mais arestas não significa mais longe (0:45)

**Na tela:** Barras segmentadas dos caminhos até Kleinberg (9 arestas, 2,7070, média 0,30 por aresta) e Kruskal (8 arestas, 3,4804, média 0,44); outros destinos e Turing inalcançável.

**Fala:** Na rede de colaboração, o exemplo que mais ensina é Kleinberg contra Kruskal. Cada barra é um caminho mínimo a partir de Edsger W. Dijkstra, e cada segmento é uma aresta, com comprimento proporcional ao peso. Kruskal está a 8 arestas, Kleinberg a 9, mas Kleinberg está mais perto: 2,71 contra 3,48, porque as arestas do caminho dele são, em média, mais leves. Distância ponderada não é número de arestas. Outros destinos embaixo; Turing é inalcançável: a única coautoria dele na base é com M. H. A. Newman.

## 7. Tempo médio de Dijkstra por origem (s, escala log) (0:40)

**Na tela:** Gráfico vetor × heap com tracejado nos timeouts de 900 s; painel **96×** (medido); rodapé com as execuções concluídas.

**Fala:** Estudo 2, em escala logarítmica, com as mesmas 100 origens sorteadas para as duas filas. No W_3, o único grafo em que as duas terminaram, o heap foi 96 vezes mais rápido: 154,6 contra 1,61 segundo por origem, nas mesmas 7 origens. Do W_4 ao W_7, a primeira execução do vetor passou de 900 segundos e foi interrompida; é o tracejado. Nada foi estimado para preencher o gráfico.

## 8. Quatro tipos de número, sempre identificados (0:45)

**Na tela:** Cartões: medido (96×; CV 0,2% a 7,0%), limite inferior (> 43,4× a > 1,6×), extrapolação teórica (≈ 4,3 h a ≈ 1,2 ano), hipótese (16 → 206 ns por (n+m) log₂ n).

**Fala:** Como ler os números do estudo 2. Medido: os 96 vezes do W_3, e o heap em todos os grafos; o coeficiente de variação, desvio-padrão sobre a média, ficou entre 0,2 e 7 por cento, o maior no W_4. Limite inferior: nos grafos maiores só sabemos que o ganho passa de 43,4; 6,2; 5,3 e 1,6 vezes; esses valores caem porque o teto de 900 segundos é fixo, não porque o ganho diminui. Extrapolação teórica: com O(n²) e a constante do W_3, o vetor levaria horas no W_4 e cerca de um ano no W_7; não medimos. Hipótese: o custo do heap por unidade de (n + m) log n cresce com o grafo; atribuímos à cache, sem medir.

## 9. Dijkstra custa pouco perto do grafo (0:30)

**Na tela:** +4,7 MB (vetor) e +9,1 MB (heap) no W_3; tabela da carga em CSR, medido × 8(n+2) + 24m bytes.

**Fala:** Memória, como na Parte 1: cada medição em um processo separado, com o pico do kernel zerado antes da chamada. No W_3, Dijkstra somou 4,7 MB com vetor e 9,1 MB com heap, de 3 a 6 por cento do grafo; os dois são O(n). Nos grafos maiores, não medimos. À direita, a carga em CSR bate com a fórmula; no W_6 e no W_7, exatamente.

## 10. A matriz cresce com n²; lista e CSR, com n + m (0:30)

**Na tela:** Tabela dos subgrafos 1..N do W_3 e do W_3 completo; matriz nos grafos oficiais (teórico).

**Fala:** Para comparar representações, usamos subgrafos do W_3 induzidos pelos vértices 1 a N. A matriz cresce com n²: 3,5 GB com só 20 mil vértices, perto da fórmula. Lista e CSR crescem com n + m e ficam próximas. Nos grafos oficiais a matriz excederia em muito os 31 GiB desta máquina; esses valores são da fórmula, não medidos.

## 11. Trade-off da CSR: menos memória, pico maior (0:40)

**Na tela:** Gráfico lista × CSR (após a carga e pico); destaques −35% e +70%; explicação do pico (estimativa ≈ 375 MB, medido 377 MB).

**Fala:** O trade-off da CSR, medido no W_3. Depois da carga, ela ocupa 35 por cento menos que a lista: 144 contra 222 MB. Mas, durante a construção, o pico é 70 por cento maior: 377 contra 222. A CSR guarda as arestas lidas e depois monta os arrays finais; com as 73 arestas repetidas do W_3, monta uma segunda cópia. Nossa estimativa dá 375 MB. O pico é passageiro: Dijkstra roda sobre os 144 MB. Nos outros grafos o pico não foi medido.

## 12. O que os experimentos mostram, e até onde (0:40)

**Na tela:** Quatro cartões: núcleo único, tempo (k = 100 só no W_3), memória, limitações.

**Fala:** Para fechar, conclusões restritas ao que medimos. Separar a fila do algoritmo tornou a comparação justa: os 96 vezes refletem só a troca da fila. O heap terminou todas as execuções que começou dentro do orçamento de 1.200 segundos, mas só o W_3 chegou às 100; nos outros, foram 58, 8, 6 e 2. O vetor não terminou nenhuma em 900 segundos a partir de um milhão de vértices. Em memória, a CSR carregou todos os grafos nesta máquina e a matriz excederia a RAM. As limitações estão à direita. Obrigado.

## Perguntas prováveis

- *Por que o speedup cai do W_4 ao W_7?* Não cai: são limites inferiores com um teto fixo de 900 s.
- *O que é o "CV" do slide 8?* Coeficiente de variação, desvio-padrão amostral dividido pela média dos tempos
  do heap: 0,5% (W_3), 7,0% (W_4), 1,5% (W_5), 0,2% (W_6) e 0,2% (W_7, só 2 execuções).
- *Por que não `heapq`?* Ele não tem `decrease_key`.
- *Por que não a matriz?* No W_3 ela precisaria de 83,8 GiB (teórico), contra 31 GiB de RAM.
- *O heap fez as 100 execuções em todos os grafos?* Não: só no W_3. Nos demais, o orçamento de 1.200 s
  permitiu 58, 8, 6 e 2; todas as execuções iniciadas terminaram.
