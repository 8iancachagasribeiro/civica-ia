# Cívica IA: contrato de evidências v0.2

## Propósito

O produto explica, com rastreabilidade, **o conteúdo de um plano oficial**, **atos documentados em mandatos anteriores** e **indicadores públicos observados**. Não recomenda voto, ranqueia candidaturas ou atribui vantagens políticas personalizadas.

## Entidades do grafo

1. `documents`: fonte original do plano; identificação da candidatura, eleição, páginas e SHA-256.
2. `commitments`: trecho literal e página da promessa, associado ao documento de origem; estado de revisão humana.
3. `office_terms`: histórico de cargos efetivamente ocupados, jurisdição e período; uma pessoa pode ter vários mandatos.
4. `documented_actions`: ato atribuído a órgão competente com fonte primária, data, natureza do ato e situação de verificação.
5. `commitment_action_links`: vínculo revisado entre compromisso e ação, com documento comprobatório; nunca gerado automaticamente por similaridade textual.
6. `outcome_series`: medição com período, unidade, território, população e metodologia, separada da ação.
7. `action_outcome_links`: hipótese de relação entre ação e indicador, identificando se é mera coincidência temporal, associação estatística ou evidência de estudo causal; inclui limitações e referência do método.

## Principais regras metodológicas

- **Identidade:** nome e cargo não bastam para atribuição automática; validar identificador, mandato, competências do ente federativo e origem do documento.
- **Eleição e mandato:** distinguir plano apresentado em eleição N de atos em mandato anterior; um candidato sem exercício anterior pode ter exclusivamente promessas documentadas.
- **Planos integrais:** preservar o PDF inteiro e número de página; registrar compromissos de todas as áreas sem seleção favorável de trechos.
- **Execução:** distinguir projeto, voto, norma aprovada, orçamento autorizado, despesa paga e serviço entregue. Estes estágios não são equivalentes.
- **Impactos:** taxa e contagem exigem denominador e definição; apontar período de referência, mudanças de metodologia, defasagem, fatores externos e revisão de dados.
- **Causalidade:** atribuir status `estudo_causal` somente com estudo explícito, estimando pressupostos, contrafactual e incerteza. Não derivar causalidade da cronologia.
- **Vínculos ausentes:** mostrar **não verificado**, nunca “não fez” ou “fracassou” por falta de dados.
- **Cobertura:** publicar relatório sobre fontes consultadas, lacunas, datas e escopo em vez de anunciar exaustividade não verificada.

## Impactos na vida cotidiana sem microdirecionamento eleitoral

A análise pode descrever dados **agregados** para população e território definidos pela fonte (por exemplo, evolução anual de um indicador numa cidade), ou explicar regras documentadas de acesso a um programa. Não solicitar, persistir ou inferir preferência eleitoral, opinião política ou outra característica sensível; não produzir “melhor candidato para seu perfil” nem pontuação personalizada. Efeitos individuais dependem de elegibilidade, implementação concreta e variáveis que séries agregadas não observam.

## Fontes para a próxima ingestão

- TSE: https://dadosabertos.tse.jus.br/
- Câmara: https://dadosabertos.camara.leg.br/
- Senado: https://www12.senado.leg.br/dados-abertos
- Orçamento e execução federal: https://portaldatransparencia.gov.br/download-de-dados/
- IBGE: https://sidra.ibge.gov.br/
- Saúde: https://datasus.saude.gov.br/
- Educação: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos
- Segurança: https://dados.mj.gov.br/
- Justiça: https://www.cnj.jus.br/pesquisas-judiciarias/

## Escopo do incremento

Esta etapa entrega **o esquema SQL e uma API de leitura do grafo**, mas não importa automaticamente atos ou avalia impacto causal. A base do grafo começa vazia; inserções exigem revisão editorial/metodológica e devem ocorrer por fluxo administrativo futuro (não existe endpoint público de edição).

## Normas

Regra eleitoral de referência: https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-755-de-2-de-marco-de-2026
