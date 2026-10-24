"""Build public, source-linked, sanitized factual snapshot for installable Cívica PWA."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from app.db import connect

_ALLOWED_DOMAINS = (
    "tse.jus.br", "camara.leg.br", "senado.leg.br", "bcb.gov.br",
    "ibge.gov.br", "gov.br", "cnj.jus.br",
)
def official_url(url: str) -> bool:
    parts = urlparse(url or "")
    hostname = (parts.hostname or "").lower()
    return parts.scheme == "https" and any(
        hostname == suffix or hostname.endswith("." + suffix) for suffix in _ALLOWED_DOMAINS
    )

def build_snapshot() -> dict:
    conn = connect()
    try:
        docs = [dict(row) for row in conn.execute("""
            SELECT id,title,person,doc_type,election_year,issuer,source_url,sha256,page_count
            FROM documents ORDER BY election_year, id
        """).fetchall() if official_url(row["source_url"])]
        ids = {d["id"] for d in docs}
        excerpts = [dict(row) for row in conn.execute("""
            SELECT c.id, c.document_id, c.page, c.theme, c.body,
                   d.title, d.person, d.doc_type, d.source_url
            FROM chunks c JOIN documents d ON d.id=c.document_id
            ORDER BY d.id,c.page,c.chunk_index LIMIT 12000
        """).fetchall() if row["document_id"] in ids]
        for ex in excerpts:
            ex["body"] = ex["body"][:1600]
        indicators = [dict(row) for row in conn.execute("""
            SELECT indicator_code,indicator_name,unit,period,territory,
                   population,value,source_url,source_issuer,methodology
            FROM outcome_series ORDER BY period DESC LIMIT 10000
        """).fetchall() if official_url(row["source_url"])]
    finally:
        conn.close()
    archived_source = None
    if not indicators:
        archive_file = Path("data/sources/bcb_sgs433_official.json")
        if archive_file.exists():
            from app.bcb_source import parse_bcb_ipca
            archive = json.loads(archive_file.read_text(encoding="utf-8"))
            if (archive.get("source_name") == "Banco Central SGS 433, IPCA do IBGE"
                    and archive.get("source_url","").startswith("https://api.bcb.gov.br/")):
                indicators = parse_bcb_ipca(archive["records"],archive["source_url"])
                archived_source = {
                    "status": "archive_official_not_live",
                    "source": archive["source_url"],
                    "last_successful_access": archive["accessed_at"],
                    "message": "Cópia de medições oficiais recuperadas anteriormente. Não é nova consulta ao vivo."
                }
    return {
        "schema_version": "app-snapshot-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"documents":len(docs),"excerpts":len(excerpts),"indicators":len(indicators)},
        "documents":docs, "excerpts":excerpts, "indicators":indicators,
        "archived_indicator_source": archived_source,
        "methodology": (
            "Fontes públicas. Planos são compromissos, proposições são registros "
            "legislativos, indicadores são observações agregadas. Coincidência "
            "temática não comprova execução, causalidade ou benefício individual. "
            "O acervo é parcial e não recomenda candidaturas."
        )
    }

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("app/static/data/evidence.json"))
    args=p.parse_args()
    data=build_snapshot()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"output":str(args.output),"counts":data["counts"]},ensure_ascii=False))

if __name__ == "__main__":main()
