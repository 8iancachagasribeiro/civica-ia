"""SQLite + FTS5; busca local e auditável, sem embeddings proprietários."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    person TEXT NOT NULL DEFAULT '',
    election_year INTEGER,
    doc_type TEXT NOT NULL,
    issuer TEXT NOT NULL,
    source_url TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    collected_at TEXT NOT NULL DEFAULT (datetime('now')),
    page_count INTEGER NOT NULL DEFAULT 0,
    source_notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    body TEXT NOT NULL,
    theme TEXT NOT NULL DEFAULT 'geral',
    UNIQUE(document_id, page, chunk_index)
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_search USING fts5(
    body, content='chunks', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
 INSERT INTO chunk_search(rowid,body) VALUES(new.id,new.body);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
 INSERT INTO chunk_search(chunk_search,rowid,body) VALUES('delete',old.id,old.body);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
 INSERT INTO chunk_search(chunk_search,rowid,body) VALUES('delete',old.id,old.body);
 INSERT INTO chunk_search(rowid,body) VALUES(new.id,new.body);
END;
-- Relações de compromisso/execução/efeitos exigem revisão humana, não são inferidas.
CREATE TABLE IF NOT EXISTS commitments (
 id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id),
 page INTEGER NOT NULL, exact_excerpt TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'pendente',
 reviewed_at TEXT, notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS outcome_series (
 id INTEGER PRIMARY KEY, indicator_code TEXT NOT NULL, indicator_name TEXT NOT NULL,
 unit TEXT NOT NULL, period TEXT NOT NULL, territory TEXT NOT NULL,
 population TEXT NOT NULL, value REAL NOT NULL,
 source_url TEXT NOT NULL, source_issuer TEXT NOT NULL,
 retrieved_at TEXT NOT NULL DEFAULT (datetime('now')),
 methodology TEXT NOT NULL DEFAULT '',
 UNIQUE(indicator_code,period,territory,population,source_url)
);
CREATE TABLE IF NOT EXISTS evidence_links (
 id INTEGER PRIMARY KEY, commitment_id INTEGER NOT NULL REFERENCES commitments(id),
 outcome_series_id INTEGER REFERENCES outcome_series(id),
 kind TEXT NOT NULL CHECK(kind IN ('associacao','avaliacao_de_impacto','sem_evidencia')),
 evidence_url TEXT NOT NULL, analyst_notes TEXT NOT NULL,
 reviewed_at TEXT NOT NULL
);
"""

def connect() -> sqlite3.Connection:
    path = Path(os.environ.get("CIVICA_DB", "data/civica.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
