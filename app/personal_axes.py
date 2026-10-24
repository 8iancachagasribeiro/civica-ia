"""Eixos de vida para a página "Meu cenário": o que cada plano e registro oficial diz sobre cada um.

A personalização é só um FILTRO de quais eixos exibir; roda no navegador e nada é enviado ou salvo.
Não há pontuação, peso nem ordem de mérito: cada eixo mostra, lado a lado, o que já é lei/ato,
o que o plano promete, dados nacionais, estudos e lacunas. A ordem dos eixos é fixa.
"""
from __future__ import annotations
import re
from .core import norm
from .themes import THEME_INDICATORS, anchor_regex

PROFILE = [
    {"key": "vinculo", "type": "radio", "label": "Como você trabalha", "options": [
        {"value": "clt", "label": "CLT (carteira assinada)"}, {"value": "pj", "label": "PJ (pessoa jurídica)"},
        {"value": "mei", "label": "MEI"}, {"value": "informal", "label": "Autônomo(a) ou informal"},
        {"value": "sem", "label": "Não trabalho no momento"}]},
    {"key": "renda_baixa", "type": "check", "label": "Renda familiar de até 2 salários mínimos"},
    {"key": "aluguel", "type": "check", "label": "Pago aluguel"},
    {"key": "comprar", "type": "check", "label": "Quero comprar imóvel"},
    {"key": "filhos_pequenos", "type": "check", "label": "Tenho filhos de até 6 anos"},
    {"key": "mulher", "type": "check", "label": "Mostrar também temas voltados a mulheres"},
    {"key": "pet", "type": "check", "label": "Tenho animais de estimação"},
]

_GERAL = {"Índice geral": "IBGE_7060_IPCA12M_INDICE_GERAL"}
SERIES = {
    "ipca": {"label": "IPCA acumulado em 12 meses (%)", "codes": _GERAL},
    "casa": {"label": "IPCA 12 meses: itens das contas da casa (%)",
             "note": "Mede preços ao consumidor; não atribui causa a nenhum governo.",
             "codes": {"Alimentação no domicílio": "IBGE_7060_IPCA12M_ITEM_ALIMENTACAO_NO_DOMICILIO",
                       "Energia elétrica": "IBGE_7060_IPCA12M_ITEM_ENERGIA_ELETRICA_RESIDENCIAL",
                       "Gás de botijão": "IBGE_7060_IPCA12M_ITEM_GAS_DE_BOTIJAO", **_GERAL}},
    "aluguel": {"label": "IPCA 12 meses: aluguel e condomínio (%)",
                "note": "Variação de preços; não é o seu reajuste, que segue o seu contrato.",
                "codes": {"Aluguel residencial": "IBGE_7060_IPCA12M_ITEM_ALUGUEL_RESIDENCIAL",
                          "Condomínio": "IBGE_7060_IPCA12M_ITEM_CONDOMINIO", **_GERAL}},
    "rendimento": {"label": "Rendimento médio real habitual do trabalho principal (R$)",
                   "codes": {"Total": "IBGE_5436_RENDIMENTO_TOTAL"}},
    "desocupacao": {"label": "Taxa de desocupação (%)", "codes": {"Total": "IBGE_4093_DESOCUPACAO_TOTAL"}},
    "informalidade": {"label": "Taxa de informalidade (%)", "codes": {"Total": "IBGE_8529_INFORMALIDADE"}},
    "selic": {"label": "Meta da Selic no fim do mês (% ao ano)",
              "note": "Taxa básica de juros; não é a taxa cobrada de uma pessoa.",
              "codes": {"Selic": "BCB_SGS_432_SELIC_META"}},
    "imob": {"label": "Juros de financiamento imobiliário (% ao ano, acima da TR quando pós-fixado)",
             "note": "Médias mensais das instituições, não oferta a você. A CAIXA é a referência dos programas habitacionais.",
             "codes": {"Regulada, mediana": "BCB_OLINDA_IMOB_REGULADA_TR_MEDIANA",
                       "Regulada, CAIXA": "BCB_OLINDA_IMOB_REGULADA_TR_CAIXA",
                       "Mercado prefixado, mediana": "BCB_OLINDA_IMOB_MERCADO_PREFIXADO_MEDIANA",
                       "Mercado prefixado, CAIXA": "BCB_OLINDA_IMOB_MERCADO_PREFIXADO_CAIXA"}},
    "plano_saude": {"label": "IPCA 12 meses: plano de saúde (%)",
                    "note": "Preço do plano privado; não mede qualidade nem acesso ao SUS.",
                    "codes": {"Plano de saúde": "IBGE_7060_IPCA12M_ITEM_PLANO_DE_SAUDE", **_GERAL}},
    "mulheres_renda": THEME_INDICATORS["mulheres"][0],
    "mulheres_desocupacao": THEME_INDICATORS["mulheres"][1],
}

_EMPREGO = [["vinculo", "pj"], ["vinculo", "mei"], ["vinculo", "informal"]]
AXES = [
    {"id": "custo_vida", "title": "Custo de vida e contas da casa", "applies": {"always": True},
     "why": "Alimentos, energia e gás pesam no orçamento de quase todo mundo.",
     "plan": r"cesta basica|conta de luz|tarifa social|gas do povo|auxilio gas|botijao|cashback|comida mais barata|"
             r"preco dos alimentos|reduzir impostos|menos imposto|inflacao",
     "records": r"auxilio gas|tarifa social|energia eletrica|cesta basica|programa de aquisicao de alimentos|"
                r"reduz\w* (?:as )?aliquotas.*(?:gasolina|alcool|diesel|combustiv|gas natural)",
     "series": ["casa", "ipca"], "studies": [],
     "caveats": ["Preços variam por câmbio, clima, tributos e mercado; a série não atribui causa a governo nenhum."],
     "check": "Compare com as suas contas: o que mais pesa no seu mês?"},
    {"id": "salario_renda", "title": "Salário mínimo, imposto de renda e renda do trabalho",
     "applies": {"any": [["renda_baixa", True], ["vinculo", "clt"]]},
     "why": "Quem ganha perto do mínimo sente primeiro a política de reajuste e a tributação da renda.",
     "plan": r"salario[- ]minimo|valorizacao do salario|imposto de renda|isencao|renda do trabalho",
     "records": r"salario minimo|imposto (?:sobre a|de) renda d[ae]s? pessoas? fisicas?|tabela progressiva|"
                r"legislacao do imposto sobre a renda|reducao do imposto devido",
     "series": ["rendimento", "desocupacao"], "studies": [],
     "caveats": ["A política de valorização do salário mínimo está em lei desde 2023 (MPV 1172/2023, virou norma). "
                 "Promessa de manter, ou silêncio do plano, não muda a lei; mudar exige nova lei."],
     "check": "Veja se você já estava na faixa de isenção do imposto de renda antes de contar esse benefício."},
    {"id": "transferencias", "title": "Programas de transferência de renda", "applies": {"any": [["renda_baixa", True]]},
     "why": "Bolsa Família, Gás do Povo e similares dependem da renda da família e do cadastro.",
     "plan": r"bolsa familia|auxilio brasil|cadunico|cadastro unico|programas? sociais?|transferencia de renda|"
             r"gas do povo|auxilio gas|\bbpc\b",
     "records": r"bolsa familia|auxilio brasil|auxilio gas|programa social|assistencia social|prestacao continuada",
     "series": [], "studies": ["pbf-economia-2009", "pbf-mortalidade-infantil-2013"],
     "caveats": ["A elegibilidade depende da renda por pessoa e da inscrição no CadÚnico; confirme no CRAS da sua cidade.",
                 "Estudos medem efeitos em populações e períodos específicos, não o que ocorrerá com a sua família."],
     "check": "Procure o CRAS para saber se a sua família se enquadra."},
    {"id": "trabalho_clt", "title": "Jornada, direitos e emprego com carteira", "applies": {"any": [["vinculo", "clt"]]},
     "why": "Jornada, escala e direitos trabalhistas valem em regra para empregados CLT.",
     "plan": r"6\s?x\s?1|jornada de trabalho|jornada flexivel|negociado sobre|carteira assinada|custo do trabalho|"
             r"reforma trabalhista|igualdade salarial|trabalho decente",
     "records": r"jornada de trabalho|jornada semanal|igualdade salarial|trabalhistas?|aprendizagem",
     "series": ["desocupacao", "informalidade"], "studies": [],
     "caveats": ["Mudar a jornada exige emenda constitucional (PEC) ou lei; depende do Congresso."],
     "check": "Veja se a sua empresa ou categoria já tem acordo próprio sobre jornada."},
    {"id": "trabalho_pj", "title": "Contrato PJ, pejotização e tributação de serviços", "applies": {"any": [["vinculo", "pj"]]},
     "why": "Quem presta serviço como PJ pode ser afetado por fiscalização de vínculo e pela reforma tributária.",
     "plan": r"pejotiz|pessoa juridica|reforma tributaria|\bibs\b|\bcbs\b|trabalho por aplicativo|plataformas? digita",
     "records": r"pejotiz|relacao de trabalho|trabalhadores? por aplicativo|reforma tributaria|lei complementar n. 214",
     "series": ["informalidade"], "studies": [],
     "caveats": ["Se o CNPJ foi exigido pela empresa que contrata, a fiscalização contra a 'pejotização' pode alterar o seu "
                 "contrato; avalie o seu caso com contador ou advogado trabalhista.",
                 "Os planos não detalham o efeito da reforma tributária sobre PJ prestadora de serviço."],
     "check": "Confira se o seu contrato PJ tem subordinação, horário e exclusividade."},
    {"id": "mei_pequeno_negocio", "title": "MEI, pequenos negócios e crédito para empreender",
     "applies": {"any": [["vinculo", "mei"], ["vinculo", "pj"]]},
     "why": "Crédito, burocracia e regras do Simples e do MEI afetam quem tem CNPJ.",
     "plan": r"\bmei\b|microempreended|pequenos negocios|micro e pequen|pronampe|desenrola|credito para empreender|"
             r"minha primeira empresa|banco da prosperidade|burocracia|simples nacional",
     "records": r"microempreended|\bmei\b|pronampe|desenrola|simples nacional|lei complementar n. 123|"
                r"pequen[oa]s? (?:negocio|empresa|porte)|fundo garantidor",
     "series": ["selic"], "studies": [],
     "caveats": ["Plano que promete crédito não garante concessão: depende de banco, garantia e histórico."],
     "check": "Veja se o seu faturamento está dentro do limite da sua categoria (MEI ou Simples)."},
    {"id": "protecao_autonomo", "title": "Previdência e proteção de quem contribui por conta própria",
     "applies": {"any": _EMPREGO},
     "why": "Doença, acidente e aposentadoria dependem de contribuir na categoria certa.",
     "plan": r"previdencia|\binss\b|aposentadoria|protecao social|auxilio[- ]doenca|acidentes?",
     "records": r"previdenci|\binss\b|auxilio[- ]doenca|incapacidade|seguro[- ]desemprego",
     "series": [], "studies": [],
     "caveats": ["A cobertura depende da categoria e da contribuição; consulte o Meu INSS."],
     "check": "Verifique no Meu INSS se as suas contribuições estão em dia."},
    {"id": "comprar_imovel", "title": "Comprar a casa própria", "applies": {"any": [["comprar", True]]},
     "why": "Programas habitacionais, juros e a forma de comprovar renda decidem se o financiamento fecha.",
     "plan": r"minha casa|casa verde|financiamento (?:da|de) casa|credito imobiliario|casa propria|compra assistida|"
             r"habitacao|moradia digna|taxa de juros|juros menores|\bfgts\b|fundo garantidor",
     "records": r"minha casa|habitacao popular|habitacao de interesse social|moradia digna|credito imobiliario|"
                r"financiamento imobiliario|casa propria|regularizacao fundiaria|uso especial para fins de moradia",
     "series": ["selic", "imob"], "studies": [],
     "caveats": ["Taxas do Banco Central são médias de mercado, não oferta para você.",
                 "Quem comprova renda como PJ ou autônomo apresenta documentos próprios; nenhum plano muda isso diretamente.",
                 "Faixa e subsídio dos programas dependem da renda familiar; simule na CAIXA."],
     "check": "Simule o financiamento na CAIXA com a renda que você consegue comprovar."},
    {"id": "aluguel", "title": "Quem paga aluguel", "applies": {"any": [["aluguel", True]]},
     "why": "Reajuste, garantia e custo de morar afetam o orçamento e a capacidade de juntar entrada.",
     "plan": r"\balugue\w*|\blocacao\b|\binquilin\w*|\blocatari\w*",
     "records": r"\balugue\w*|\blocacao\b|\blocaticio|\binquilin\w*|\blocatari\w*",
     "series": ["aluguel"], "studies": [],
     "caveats": ["O seu reajuste segue o contrato, não a média nacional."],
     "check": "Veja o índice e a data de reajuste do seu contrato de locação."},
    {"id": "creche_filhos", "title": "Filhos pequenos, creche e primeira infância", "applies": {"any": [["filhos_pequenos", True]]},
     "why": "Vaga em creche e apoio à primeira infância mudam a rotina e a renda de quem cuida.",
     "plan": r"\bcreches?\b|primeira infancia|pre-escola|educacao infantil|voucher[- ]creche|licenca[- ]maternidade|"
             r"licenca[- ]paternidade",
     "records": r"creche|primeira infancia|educacao infantil|pre-escola|licenca[- ]maternidade|licenca[- ]paternidade",
     "series": [], "studies": ["pim-pbf-saude-2021", "pbf-mortalidade-infantil-2013"],
     "caveats": ["A oferta de vagas é municipal; a União apoia com recursos e obras."],
     "check": "Veja a fila de creche e a regra de matrícula na secretaria de educação do seu município."},
    {"id": "violencia_mulher", "title": "Proteção contra a violência de gênero", "applies": {"any": [["mulher", True]]},
     "why": "Medida protetiva, rede de acolhimento e punição aparecem nos dois planos de formas diferentes.",
     "plan": r"maria da penha|medidas? protetivas?|feminicid|violencia contra a mulher|violencia domestica|"
             r"casa da mulher|tornozeleira",
     "records": r"maria da penha|violencia domestica|medida protetiva|feminicid|violencia contra a mulher",
     "series": [], "studies": ["lmp-ipea-2015", "lmp-garcia-2013"],
     "caveats": ["Estudos sobre a Lei Maria da Penha divergem por desfecho e método."],
     "check": "Em risco imediato, ligue 180 (Central de Atendimento à Mulher) ou 190."},
    {"id": "trabalho_mulher", "title": "Trabalho e renda das mulheres", "applies": {"any": [["mulher", True]]},
     "why": "Igualdade salarial, qualificação e crédito para mulheres aparecem em propostas e leis.",
     "plan": r"igualdade salarial|empreendedorismo feminino|mulheres empreendedoras|trabalho para elas|mulheres mil|"
             r"autonomia economica|ganha[, ]+ganha|escola brasil por elas|banco de dados.*mulheres",
     "records": r"igualdade salarial|autonomia economica das mulheres|mulheres empreendedoras",
     "series": ["mulheres_renda", "mulheres_desocupacao"], "studies": [],
     "caveats": ["Igualdade salarial vale em regra para empregadas CLT de empresas obrigadas."],
     "check": "Veja se a sua empresa publica relatório de transparência salarial."},
    {"id": "saude_sus", "title": "Saúde pública (SUS)", "applies": {"always": True},
     "why": "Fila, medicamento e atendimento especializado dependem do SUS, que estados e municípios executam em grande parte.",
     "plan": r"\bsus\b|farmacia popular|agora tem especialistas|atencao basica|telemedicina|saude da mulher|"
             r"saude para elas|prontuario|medicamentos? gratuit",
     "records": r"medicament|farmacia|especialistas|saude publica|sistema unico de saude",
     "series": ["plano_saude"], "studies": [],
     "caveats": ["Prazos e filas dependem de estados e municípios, que executam boa parte do SUS."],
     "check": "Veja o que a sua UBS e a regulação municipal oferecem hoje."},
    {"id": "animais", "title": "Animais de estimação", "applies": {"any": [["pet", True]]},
     "why": "Castração, identificação e proteção contra maus-tratos dependem de política pública.",
     "plan": r"\banimais\b|propatinhas|sinpatinhas|\bgatos?\b|\bcaes\b|direitos animais",
     "records": r"\banimais\b|\banimal\b|maus[- ]tratos",
     "series": [], "studies": [],
     "caveats": ["Leis de proteção animal podem ter autoria parlamentar e não aparecer no registro do Executivo."],
     "check": "Veja se o seu município tem programa de castração e identificação."},
]

STAGE_ORDER = {"lei": 0, "aprovada": 1, "tramitando": 2, "encerrada": 3, "perdeu_eficacia": 4}


def is_toc(body: str) -> bool:
    """Linhas de sumário e índice (pontilhado) não são conteúdo do plano."""
    return "...." in body or body.count(". . .") > 2


def plan_hits(rows: list[dict], pattern: str, limit: int = 3) -> tuple[list[list[int]], int]:
    rx = re.compile(pattern)
    scored = []
    for r in rows:
        if is_toc(r["body"]):
            continue
        n = sum(1 for _ in rx.finditer(norm(r["body"])))
        if n:
            scored.append((-(min(n, 5) + 2 * len(r["markers"]) + (r["kind"] == "compromisso")), r["page"], r["id"], r))
    scored.sort(key=lambda s: s[:3])
    picks, pages = [], set()
    for _s, page, _id, r in scored:
        if page in pages:
            continue
        picks.append([r["id"], anchor_regex(r["body"], pattern)])
        pages.add(page)
        if len(picks) == limit:
            break
    return picks, len(scored)


def record_hits(records: list[dict], pattern: str, limit: int = 4) -> dict:
    rx = re.compile(pattern)
    rows = []
    for r in records:
        n = sum(1 for _ in rx.finditer(norm(r["ementa"]))) if r["nature"] != "credito" else 0
        if n:
            rows.append((min(n, 3), r))
    # aderência ao eixo > estágio > data (mais recente primeiro); sort estável em passes
    rows.sort(key=lambda t: t[1]["presented_on"], reverse=True)
    rows.sort(key=lambda t: STAGE_ORDER[t[1]["stage"]])
    rows.sort(key=lambda t: -t[0])
    rows = [r for _n, r in rows]
    by_stage = {s: sum(r["stage"] == s for r in rows) for s in STAGE_ORDER}
    items = [{"id": r["identifier"], "e": r["ementa"][:300], "d": r["presented_on"], "st": r["stage"],
              "a": r["authorship"], "b": r["body"], "u": r["source_url"]} for r in rows[:limit]]
    return {"count": len(rows), "by_stage": by_stage, "items": items}


def build_personal(excerpts: list[dict], records: list[dict], year: int = 2026) -> dict:
    plans: dict[str, list[dict]] = {}
    for r in excerpts:
        if r.get("doc_type") == "plano_eleitoral" and r.get("sq") and r.get("election_year") == year:
            plans.setdefault(r["sq"], []).append(r)
    by_person: dict[str, list[dict]] = {}
    for r in records:
        by_person.setdefault(r["person_sq"], []).append(r)
    axes = []
    for ax in AXES:
        cands = {}
        for sq, rows in plans.items():
            picks, total = plan_hits(rows, ax["plan"])
            entry = {"plan": picks, "plan_total": total}
            if sq in by_person:
                entry["records"] = record_hits(by_person[sq], ax["records"])
            cands[sq] = entry
        axes.append({"id": ax["id"], "title": ax["title"], "why": ax["why"], "applies": ax["applies"],
                     "check": ax["check"], "caveats": ax["caveats"], "studies": ax["studies"],
                     "series": [SERIES[k] for k in ax["series"]], "cands": cands})
    return {"profile": PROFILE, "axes": axes}
