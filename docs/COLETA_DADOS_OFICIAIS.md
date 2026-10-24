# Coleta real de dados públicos · v0.3

## Fontes diretamente consultadas

- **TSE 2022:** https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2022_BR.zip. PDF integral e páginas extraíveis dos identificadores verificados no manifesto. Planos eleitorais são promessas, não execução.
- **Câmara:** https://dadosabertos.camara.leg.br/api/v2/proposicoes?ano=2024&itens=25&pagina=1. Até 25 ementas. Ementa de proposição não é lei aprovada, e não demonstra autoria individual sem consulta específica.
- **IBGE/SIDRA:** https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/-36/variaveis/63?localidades=N1%5Ball%5D. IPCA mensal do Brasil, variável 63 do agregado 1737; valor observado, sem atribuição causal política.

- **Banco Central SGS 433:** https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/96?formato=json. Registros mensais do IPCA originado no IBGE, com URL, SHA-256, intervalo e método. Ativado para redundância quando a conexão IBGE estiver indisponível.

## Procedimento

O GitHub Actions faz download das fontes por conexões HTTPS oficiais, valida as respostas e indexa em SQLite. A base fica como artefato da execução por até 14 dias. O relatório de proveniência, com fontes, erros, datas, quantidade de registros e SHA-256 da resposta IBGE, fica em data/official_snapshot.json no repositório após a primeira execução concluída. Fontes falhas são declaradas como erro, nunca como observação zero. O processo se repete semanalmente e pode ser iniciado manualmente.

Com conexão à internet: instalar requirements.txt; executar python -m pytest -q; executar python -m scripts.sync_official.

## Primeiro cruzamento factual

GET /api/public-cross?tema=economia&ano=2024

A API consulta três camadas distintas: trechos documentais dos planos eleitorais, ementas legislativas da Câmara e indicadores agregados. São vinculadas somente por assunto; nenhuma ligação causal, pontuação de candidato ou estimativa de benefício individual é presumida.

## Lacunas explícitas

Ainda não importamos votações nominais, histórico executivo, orçamento pago, indicadores de saúde, educação, segurança ou justiça. As propostas integrais ainda não foram rotuladas manualmente como compromissos validados, e os documentos públicos importados podem ser incompletos. A produção de inferências causais exigirá estudos apropriados e revisão metodológica.

Ver https://github.com/8iancachagasribeiro/civica-ia/issues/1 para critérios adicionais de aceite.
