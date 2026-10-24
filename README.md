# Cívica · IA aberta de evidências públicas

**Versão:** MVP 0.1 • **Licença:** MIT • **Idioma:** português brasileiro

Um pesquisador conversacional que recupera trechos de **planos eleitorais completos**, ementas legislativas e indicadores públicos. Preserva origem, página, documento, data e SHA-256. Não ranqueia candidaturas, não recomenda voto e não confunde promessa com realização.

> **Estado atual real:** o código está implementado e tem testes locais. A base começa **vazia**. A importação ao vivo das fontes oficiais depende de uma máquina com acesso à internet. O modelo Ollama é opcional e não está incluído no pacote. Não há avaliação causal automatizada nem implantação pública pronta.

## O que já funciona

- Interface responsiva no navegador, API FastAPI e base SQLite com busca textual FTS5, sem exigir GPU.
- Importação de PDFs preservando a **página exata** e o arquivo original, indexando o texto de todas as páginas extraíveis.
- Download/importação dos pacotes presidenciais oficiais do TSE (`2022` e `2026`) com manifestos de identificação pelo número sequencial. O pacote de 2022 tem, nesta versão, **duas candidaturas mapeadas**; 2026 contém 13 identificadores no manifesto. A relação é editável em `app/ingest.py`.
- Importação opcional de **ementas** da API oficial da Câmara, com links à proposição. Uma ementa *não* significa que uma lei foi aprovada.
- Importação manual de CSV de indicadores com unidade, período, território, população, órgão, método e link oficial.
- Busca de evidências documentais com diversidade de fontes e busca de séries numéricas por indicador, **sem associar automaticamente indicadores a candidatos ou causalidade**.
- Respostas extrativas literais por padrão; síntese facultativa com modelo aberto Qwen3 (Apache 2.0) via Ollama, quando configurado.
- Bloqueio explícito de pedidos de ranqueamento/recomendação eleitoral e exibição de limites científicos.

## Início rápido no computador (Python 3.11+)

```bash
unzip civica_ia_aberta_mvp.zip
cd civica_mvp
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra **http://localhost:8000**. A página ficará inicialmente sem documentos; isso é intencional, para não exibir dados inventados.

## Importar documentos oficiais

Em outro terminal, com `.venv` ativado e dentro de `civica_mvp`:

```bash
# Planos presidenciais de 2022: manifestos de Lula e Jair Bolsonaro
python -m app.ingest tse --year 2022

# Planos presidenciais de 2026: 13 candidaturas mapeadas
python -m app.ingest tse --year 2026

# Proposições da Câmara: ementas, e não atos aprovados
python -m app.ingest camara --year 2025 --limit 60

# PDF já baixado de uma fonte pública e verificável
python -m app.ingest pdf \
  --file /caminho/documento.pdf \
  --title 'Título do documento' \
  --issuer 'Órgão emissor' \
  --source-url 'https://dominio-oficial.gov.br/documento.pdf' \
  --type documento_publico

# CSV de indicadores, com colunas definidas em sample_indicators.csv
python -m app.ingest indicators --file meus_indicadores.csv
```

**Importante:** `source-url` não é baixado automaticamente em `pdf`: identifica o local público que um auditor pode consultar. Verifique manualmente se o arquivo importado corresponde à URL indicada. `sample_indicators.csv` contém **somente o cabeçalho**, sem números hipotéticos apresentados como fatos.

### TSE: identificação e proveniência

- `https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2022_BR.zip`
- `https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip`
- Portal oficial: `https://dadosabertos.tse.jus.br/`

A rotina `tse` lê os PDFs diretamente de dentro do ZIP oficial, calcula SHA-256 e mantém os nomes internos em `source_notes`. O sistema mostra o ZIP público e a página do PDF; no navegador, o ZIP abre como pacote, não como link direto à página específica do PDF. Se a estrutura dos arquivos mudar, o importador avisará sobre os identificadores que não encontrou. Arquivos digitalizados sem camada textual podem ficar sem trechos pesquisáveis: não se executa OCR automático.

Os nomes/identificadores do manifesto devem ser revisados com o cadastro oficial a cada atualização eleitoral. O download não ocorreu no ambiente em que este pacote foi criado; logo, **não afirmamos que todos os arquivos foram importados nem que o manifesto é exaustivo**.

## Docker (sem necessidade de placa de vídeo)

```bash
cp .env.example .env
# Para iniciar somente o aplicativo:
docker compose up --build -d web
# http://localhost:8000

# Para importar planos dentro do container:
docker compose exec web python -m app.ingest tse --year 2022
# ou
docker compose exec web python -m app.ingest tse --year 2026
```

O volume `civica_data` preserva os dados. O modo padrão usa somente busca e trechos documentais, sem necessidade de IA generativa remota.

### Opcional: síntese local com Ollama

Depois de iniciar o serviço Ollama pelo `docker compose`, instale explicitamente o modelo em sua máquina/servidor:

```bash
docker compose --profile llm up --build -d
# Exemplo: modelo de pesos abertos, tamanho/recursos de acordo com o servidor.
docker compose exec ollama ollama pull qwen3:8b
```

Edite `.env`:

```ini
CIVICA_MODE=ollama
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=qwen3:8b
```

Recrie o serviço web para aplicar novas variáveis. O Qwen3-8B é disponibilizado sob Apache 2.0 (veja https://huggingface.co/Qwen/Qwen3-8B). **A IA generativa ainda não possui avaliação formal de fidelidade, vieses, ataques de prompt ou robustez.** Ela é opcional e não deve ser exposta em produção sem avaliação independente e camada adicional de validação das afirmações.

## Consultar API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/documents
curl -X POST http://localhost:8000/api/ask \
 -H 'Content-Type: application/json' \
 -d '{"question":"Quais documentos citam alfabetização?"}'
```

Cada resultado da API inclui `sources` com página, link e hash. `indicators` contém medições independentes encontradas por palavras-chave, **não efeitos atribuídos a um governante**.

## Modelo de dados

`documents` → fonte e integridade · `chunks` → texto e página · `chunk_search` → busca lexical · `commitments` → compromissos a validar · `outcome_series` → dados numéricos e metadados · `evidence_links` → ligação entre compromissos e resultados **somente mediante revisão e documentação metodológica**.

O banco de dados contém tabelas para a segunda etapa, mas **não** há um classificador automático de promessas cumpridas, nem ligação causal automática de políticas com indicadores.

## Próximas etapas priorizadas

1. **Pipeline de execução:** normas do Planalto, PPA/LOA, despesa efetivamente liquidada/paga e prestação de contas, preservando esferas e competências governamentais.
2. **Indicadores padronizados:** IBGE/SIDRA, DATASUS, INEP, Sinesp e CNJ com séries, denominadores, recortes e versionamento.
3. **Grafo de evidências:** compromisso → ato → execução → serviço → resultado, com estado `evidência insuficiente` e revisão humana.
4. **Inferência causal:** desenhos pré-registrados, confundidores, contrafactuais, incerteza, auditoria estatística e metodológica.
5. **Governança:** corpus não seletivo, logs de alterações, revisão externa, acessibilidade, testes políticos adversariais, avaliação de vieses e análise jurídica.

## Segurança, LGPD e limites

- Não pedir, armazenar nem inferir preferência eleitoral, religião ou outros dados sensíveis dos usuários.
- O MVP **não** coleta histórico de perguntas em banco. Ainda assim, provedores de hospedagem podem gerar logs de acesso; configure retenção mínima.
- O importador de rede só chama endereços oficiais fixos no código. A importação de PDFs arbitrários ocorre apenas por **CLI administrativa**, sem endpoint de upload público. PDFs não são executados, mas exigem limites de tamanho e atualização de bibliotecas.
- Não há autenticação administrativa, rate limit, proteção de infraestrutura pública, monitoramento, avaliações de segurança avançadas ou SLA. **Não publicar em produção sem reforços** (TLS, proxy, WAF/rate limits, backups, atualizações, política de privacidade e auditoria).
- A Resolução TSE nº 23.755/2026 veda ranquear ou recomendar candidaturas, inclusive por sistemas de IA. O produto evita a funcionalidade de orientação de voto e documenta as regras em `app/core.py`. Referência: https://www.tse.jus.br/legislacao/compilada/res/2026/resolucao-no-23-755-de-2-de-marco-de-2026
- **Não confundir:** fontes do TSE contêm alegações e promessas das candidaturas; não são endosso do tribunal nem provas de execução. Documentos legislativos não equivalem, necessariamente, a leis vigentes. Indicadores observacionais não bastam para atribuição causal.

## Testes

```bash
PYTHONPATH=. pytest -q
```

## Licença e contribuição

Código sob licença [MIT](LICENSE). Dados seguem suas próprias licenças e termos de uso; dê atribuição e verifique cada fonte. Commits públicos e revisão transparente são recomendados. O projeto é independente de campanhas e não possui pontuação política.
