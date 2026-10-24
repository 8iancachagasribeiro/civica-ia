# Curadoria de evidências de impacto

Estado em 24/10/2026. O arquivo `app/static/data/impact_studies.json` só recebe estudo quando o resumo
na fonte primária foi lido e confere com o que está registrado. Estudo de impacto avalia **uma política em
um contexto e período**; não mede o que uma candidatura fará nem o que fez.

## Conferidos na fonte primária (resumo lido)

| Estudo | O que foi conferido |
|---|---|
| Rasella et al., *The Lancet* 382 (2013), DOI 10.1016/S0140-6736(13)60715-1 | Desenho, período, 2.853 municípios, razões de taxas e IC 95% (Europe PMC, PMID 23683599) |
| Assunção et al., *Review of Economic Studies* 90(4) (2023), DOI 10.1093/restud/rdac064 | Lista de municípios prioritários de 2008, redução de 43% e quase 50 Mt de carbono evitadas (Crossref) |
| Ribeiro et al., *Planejamento e Políticas Públicas* 60, DOI 10.38116/ppp60art8 | Painel 2006–2012, efeitos fixos, complementaridade PIM × PBF em causas externas (Crossref) |

## Existência confirmada, números não reconferidos

Ipea TD 2048 (Lei Maria da Penha), Garcia et al. 2013 (*Epidemiologia e Serviços de Saúde*),
Gerard, Naritomi e Silva (World Bank PRWP 9778) e Ipea TD 2363 (Prouca). Os títulos e fontes existem; os
números do JSON vieram da curadoria anterior e devem ser conferidos no texto completo antes de uso público.
Revisar também o ano da citação de Ribeiro et al. (o DOI indica o número 60 da revista, publicado em 2022).

## Pistas ainda não aceitas (não entram no app)

Cada item abaixo foi visto em reportagem ou página secundária e **não foi lido na fonte primária**.

- **Creche e emprego das mães:** avaliação por sorteio de vagas no Rio de Janeiro (Barros et al.; página do BID).
  Relevante para os dois planos (creche aparece em ambos). Falta ler o artigo e extrair a estimativa.
- **Estatuto do Desarmamento:** estimativa do Ipea (Cerqueira) de queda de 12,6% na taxa de homicídios em dez anos
  foi publicada pela imprensa; há debate metodológico. Falta o texto técnico original.
- **Pé-de-Meia:** só existe simulação *ex ante* (Insper/Centro de Evidências, 2026) estimando redução de cerca de 6,5
  pontos percentuais na evasão de jovens vulneráveis. Não é efeito observado; a avaliação oficial depende de coortes futuras.
- **Minha Casa Minha Vida:** estudo com diferenças em diferenças (repositório ENAP) indicaria que o programa não reduziu
  a favelização municipal. Cobre um único desfecho; página indisponível na coleta.
- **Mais Médicos:** achados mistos (tese UFPB local com redução de internações; estudo citado pela imprensa sem efeito
  significativo na mortalidade infantil). Sem estudo nacional revisado por pares verificado.

## Temas sem estudo curado

Segurança, Justiça e Habitação. A interface mostra isso como lacuna, não como evidência de que políticas funcionam
ou deixam de funcionar.

## Como adicionar um estudo

1. Ler o resumo na fonte primária (DOI, Europe PMC, Crossref, repositório da instituição).
2. Preencher todos os campos, incluindo `limits` substantivo e `policy_patterns` (expressões regulares sem acento,
   minúsculas) que descrevem a política citada em planos.
3. Rodar `pytest`: `tests/test_comparison.py` valida o esquema e a presença de fonte HTTPS.
