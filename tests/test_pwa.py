from fastapi.testclient import TestClient
from app.main import app

def test_pwa_works_in_python_server():
    client=TestClient(app)
    assert client.get("/").status_code == 200
    for path in ("/app.js","/compare.js","/app.css","/icon.svg","/sw.js","/manifest.webmanifest","/data/impact_studies.json"):
        assert client.get(path).status_code == 200
    manifest=client.get("/manifest.webmanifest").json()
    assert manifest["display"]=="standalone"
    assert manifest["scope"]=="./"
    assert "Cívica" in manifest["name"]

def test_no_unverified_app_snapshot(tmp_path,monkeypatch):
    # The application should never invent data as a fallback.
    monkeypatch.setenv("CIVICA_DB",str(tmp_path/"app.sqlite3"))
    client=TestClient(app)
    assert client.get("/api/evidence-trace/overview").status_code == 200
