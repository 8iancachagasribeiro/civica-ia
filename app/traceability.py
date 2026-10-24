"""Grafo público de evidências: compromissos, ações e resultados documentados.

Não estima causalidade nem atribui méritos ou pontuações a pessoas políticas.
Acesso HTTP estritamente de leitura. Alimentação demanda curadoria externa.
"""
from __future__ import annotations
from .db import connect

TRACE_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS office_terms (
    id INTEGER PRIMARY KEY,
    person_name TEXT NOT NULL,
    office TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    source_url TEXT NOT NULL,
    CHECK(length(source_url)>8)
);
CREATE TABLE IF NOT EXISTS documented_actions (
    id INTEGER PRIMARY KEY,
    term_id INTEGER REFERENCES office_terms(id),
    event_date TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK(action_type IN
      ('lei','decreto','votacao','projeto','orcamento','execucao','programa','outro')),
    description TEXT NOT NULL,
    government_body TEXT NOT NULL,
    source_url TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'pendente' CHECK(verification_status IN
      ('pendente','verificado','contestado')),
    reviewer TEXT,
    verified_at TEXT
);
CREATE TABLE IF NOT EXISTS commitment_action_links (
    commitment_id INTEGER NOT NULL REFERENCES commitments(id),
    action_id INTEGER NOT NULL REFERENCES documented_actions(id),
    relationship TEXT NOT NULL CHECK(relationship IN
      ('relacionada','implementacao_documentada','nao_implementada_documentada')),
    evidence_url TEXT NOT NULL,
    reviewed_by TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    PRIMARY KEY(commitment_id,action_id)
);
CREATE TABLE IF NOT EXISTS action_outcome_links (
    action_id INTEGER NOT NULL REFERENCES documented_actions(id),
    outcome_id INTEGER NOT NULL REFERENCES outcome_series(id),
    relationship TEXT NOT NULL CHECK(relationship IN
      ('coincidencia_temporal','associacao_estatistica','estudo_causal','evidencia_insuficiente')),
    methodology_url TEXT NOT NULL,
    limitations TEXT NOT NULL,
    reviewed_by TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    PRIMARY KEY(action_id,outcome_id)
);
CREATE INDEX IF NOT EXISTS idx_terms_person ON office_terms(person_name);
CREATE INDEX IF NOT EXISTS idx_actions_term ON documented_actions(term_id);
CREATE INDEX IF NOT EXISTS idx_commitment_links_action ON commitment_action_links(action_id);
"""


def install_trace_schema(conn):
    """Idempotent schema installation, no seeded/hypothetical real-world claims."""
    conn.executescript(TRACE_SCHEMA)


def get_trace(commitment_id: int) -> dict | None:
    """Read a reviewed evidence chain without inferring merit or individual benefit."""
    conn = connect()
    try:
        install_trace_schema(conn)
        commitment = conn.execute("""
            SELECT c.id,c.document_id,c.page,c.exact_excerpt,c.review_status,
                   d.title,d.person,d.election_year,d.source_url AS plan_url,d.sha256
            FROM commitments c JOIN documents d ON d.id=c.document_id
            WHERE c.id=?
        """, (commitment_id,)).fetchone()
        if commitment is None:
            return None
        links = conn.execute("""
            SELECT a.id AS action_id,a.event_date,a.action_type,a.description,
                   a.government_body,a.source_url,a.verification_status,
                   t.person_name AS officeholder,t.office,t.jurisdiction,
                   t.started_at,t.ended_at,cl.relationship AS commitment_relationship,
                   cl.evidence_url AS relationship_source
            FROM commitment_action_links cl
            JOIN documented_actions a ON a.id=cl.action_id
            LEFT JOIN office_terms t ON t.id=a.term_id
            WHERE cl.commitment_id=?
            ORDER BY a.event_date ASC,a.id ASC
        """, (commitment_id,)).fetchall()
        actions = []
        for link in links:
            action = dict(link)
            outcomes = conn.execute("""
                SELECT os.indicator_code,os.indicator_name,os.unit,os.period,
                       os.territory,os.population,os.value,os.source_url,
                       al.relationship,al.methodology_url,al.limitations
                FROM action_outcome_links al
                JOIN outcome_series os ON os.id=al.outcome_id
                WHERE al.action_id=?
                ORDER BY os.period,os.indicator_code
            """, (link['action_id'],)).fetchall()
            action['outcomes'] = [dict(o) for o in outcomes]
            actions.append(action)
        return {
            'commitment':dict(commitment),
            'actions':actions,
            'notices':[
              'Plano eleitoral não comprova execução.',
              'Ato documentado não comprova benefício individual.',
              'Associação temporal não comprova causalidade.',
              'Ausência de vínculo não significa que a medida não ocorreu.',
              'Não há recomendações eleitorais, pontuações ou ranqueamento.'
            ]
        }
    finally:
        conn.close()


def trace_overview() -> dict:
    conn = connect()
    try:
        install_trace_schema(conn)
        tables = ('commitments','office_terms','documented_actions',
                  'commitment_action_links','action_outcome_links')
        return {t:int(conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in tables}
    finally:
        conn.close()
