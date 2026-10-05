# Métricas do Vi Um Achado

- Coleta: workflow n8n "Vi Um Achado - Métricas e cliques" (22h todo dia; histórico guardado no próprio n8n).
- Leitura: `GET /webhook/vua-dados?k=<chave>` devolve o histórico em JSON (chave fica só no prompt da rotina diária).
- Painel: `python3 painel/build.py metricas/ultimo.json` gera `painel/painel.html`.
- Link de redirecionamento do grupo: `/webhook/go?s=bio` (conta o clique e manda para o WhatsApp).
