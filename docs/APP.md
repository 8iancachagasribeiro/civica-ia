# Cívica App · versão PWA 0.4

## O que é

Aplicativo web progressivo (PWA), responsivo e instalável em celulares e desktops compatíveis. É uma interface de consulta **documental e factual**, não um aplicativo de recomendação eleitoral.

### Telas

1. **Pesquisar:** busca passagens literais dos documentos públicos, com título, trecho, página e link original.
2. **Cruzar fontes:** exibe separadamente compromissos eleitorais, ementas e indicadores publicados que tratam do mesmo tema. Esta recuperação conjunta **não estabelece relação causal**.
3. **Acervo oficial:** catálogo de documentos recuperados com hash de integridade e origem.
4. **Metodologia:** diferencia promessa, ato público, execução, observação e possível causalidade.

## Dados de verdade

O arquivo `app/static/data/evidence.json` não é editado manualmente nem inventado pelo frontend. É gerado em cada sincronização a partir do banco SQLite preenchido por importadores oficiais:
- Planos do TSE;
- Ementas da Câmara;
- IPCA (série 433 do Banco Central, originada no IBGE).

O relatório de coleta `data/official_snapshot.json` registra erros, períodos, quantidades e SHA da resposta do Banco Central. O JSON do app contém passagens e valores, sempre com URLs originais. Caso a fonte falhe, o relatório mostra a falha. Os documentos de planos são arquivados por página; a URL do TSE pode apontar ao ZIP, pois o PDF está dentro do pacote oficial.

A implantação estática pode não atualizar até que o fluxo de sincronização e publicação termine. O site deve exibir a data do acervo exportado.

## Executar localmente

~~~bash
git clone https://github.com/8iancachagasribeiro/civica-ia.git
cd civica-ia
pip install -r requirements.txt
python -m scripts.sync_official
python -m scripts.export_app_data
uvicorn app.main:app --host 0.0.0.0 --port 8000
~~~

Acesse http://localhost:8000, depois use "Instalar" no navegador compatível. A instalação exige HTTPS fora de localhost. No iPhone/Safari, use o menu Compartilhar → Adicionar à Tela de Início.

## Publicação no GitHub Pages

Fluxo de implantação: `.github/workflows/publicar-app.yml`. Para habilitar pela primeira vez, configure o repositório em **Settings → Pages → Build and deployment → Source: GitHub Actions**. Sem essa permissão/configuração do repositório, o workflow pode falhar mesmo com testes passando. O endereço será `https://8iancachagasribeiro.github.io/civica-ia/` **somente após confirmação do deploy**.

## Limitações atuais

- A edição estática **não executa LLM**. Pesquisa textual localmente em dados exportados da coleta; a API FastAPI continua oferecendo integração opcional com Ollama em servidor próprio.
- Sem serviço de backend hospedado, o banco real do GitHub Actions é um arquivo temporário de execução e o app consome uma cópia pública auditável.
- O acervo não contém ainda histórico completo de mandatos, execução orçamentária e indicadores de saúde, educação, segurança e justiça; por isso não há comparativo causal completo.
- Offline funciona após primeira visita com carregamento dos recursos e acervo pelo service worker, sujeito às políticas de armazenamento do navegador.
- O app não coleta perfil, posição ideológica ou intenção de voto; pesquisas locais não são salvas pelo próprio código. O provedor de hospedagem pode registrar logs técnicos.
- Não apresenta rankings, aconselhamento eleitoral ou inferência de benefício individual.

## Testes

O workflow CI verifica `pytest`, `node --check` do JavaScript e a validade do manifesto PWA. A publicação depende também da execução bem-sucedida do exportador.
