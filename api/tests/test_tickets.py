import pytest
from fastapi.testclient import TestClient

from main import app, connexion


@pytest.fixture
def client():
    with TestClient(app) as c:
        with connexion() as conn:
            conn.execute("DELETE FROM tickets")
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_creer_puis_lister(client):
    r = client.post("/api/tickets", json={"titre": "Imprimante", "description": "Bourrage papier"})
    assert r.status_code == 201
    ticket = r.json()
    assert ticket["statut"] == "ouvert"
    assert ticket["priorite"] == "normale"

    r = client.get("/api/tickets")
    assert r.status_code == 200
    assert [t["titre"] for t in r.json()] == ["Imprimante"]


def test_creation_refuse_titre_vide(client):
    r = client.post("/api/tickets", json={"titre": "   ", "description": "x"})
    assert r.status_code == 422


def test_changer_statut(client):
    tid = client.post("/api/tickets", json={"titre": "VPN", "description": "Ne se connecte pas"}).json()["id"]
    r = client.patch(f"/api/tickets/{tid}", json={"statut": "en_cours"})
    assert r.status_code == 200
    assert r.json()["statut"] == "en_cours"
    r = client.patch(f"/api/tickets/{tid}", json={"statut": "resolu"})
    assert r.json()["statut"] == "resolu"


def test_statut_invalide(client):
    tid = client.post("/api/tickets", json={"titre": "Mail", "description": "Boite pleine"}).json()["id"]
    r = client.patch(f"/api/tickets/{tid}", json={"statut": "ferme"})
    assert r.status_code == 422


def test_ticket_inconnu(client):
    assert client.patch("/api/tickets/999999", json={"statut": "resolu"}).status_code == 404
    assert client.delete("/api/tickets/999999").status_code == 404


def test_filtre_et_recherche(client):
    a = client.post("/api/tickets", json={"titre": "Ecran noir", "description": "Poste 12"}).json()["id"]
    client.post("/api/tickets", json={"titre": "Clavier", "description": "Touche cassee"})
    client.patch(f"/api/tickets/{a}", json={"statut": "resolu"})
    assert [t["titre"] for t in client.get("/api/tickets?statut=resolu").json()] == ["Ecran noir"]
    assert [t["titre"] for t in client.get("/api/tickets?q=touche").json()] == ["Clavier"]


def test_supprimer(client):
    tid = client.post("/api/tickets", json={"titre": "Test", "description": "a supprimer"}).json()["id"]
    assert client.delete(f"/api/tickets/{tid}").status_code == 204
    assert client.get("/api/tickets").json() == []
