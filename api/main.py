import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, Field, field_validator

STATUTS = ("ouvert", "en_cours", "resolu")
Statut = Literal["ouvert", "en_cours", "resolu"]
Priorite = Literal["basse", "normale", "haute"]


def database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("SCALINGO_POSTGRESQL_URL")
    if not url:
        raise RuntimeError("DATABASE_URL est requis")
    # certains hebergeurs donnent postgres://, psycopg veut postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def connexion():
    return psycopg.connect(database_url(), row_factory=dict_row)


def creer_table():
    schema = (Path(__file__).parent / "schema.sql").read_text()
    with connexion() as conn:
        conn.execute(schema)


@asynccontextmanager
async def lifespan(app: FastAPI):
    creer_table()
    yield


app = FastAPI(title="API Tickets", lifespan=lifespan)

origines = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5500").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origines,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


class TicketCreation(BaseModel):
    titre: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    priorite: Priorite = "normale"

    @field_validator("titre", "description")
    @classmethod
    def pas_vide(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ne doit pas etre vide")
        return v


class ChangementStatut(BaseModel):
    statut: Statut


class Ticket(BaseModel):
    id: int
    titre: str
    description: str
    statut: Statut
    priorite: Priorite
    created_at: datetime


@app.get("/health")
def health():
    try:
        with connexion() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="base de donnees injoignable")
    return {"status": "ok"}


@app.get("/api/tickets", response_model=list[Ticket])
def lister(statut: Statut | None = None, q: str | None = Query(default=None, max_length=100)):
    sql = "SELECT * FROM tickets WHERE 1=1"
    params = []
    if statut:
        sql += " AND statut = %s"
        params.append(statut)
    if q:
        sql += " AND (titre ILIKE %s OR description ILIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY created_at DESC, id DESC"
    with connexion() as conn:
        return conn.execute(sql, params).fetchall()


@app.post("/api/tickets", response_model=Ticket, status_code=201)
def creer(ticket: TicketCreation):
    with connexion() as conn:
        return conn.execute(
            "INSERT INTO tickets (titre, description, priorite) VALUES (%s, %s, %s) RETURNING *",
            (ticket.titre, ticket.description, ticket.priorite),
        ).fetchone()


@app.patch("/api/tickets/{ticket_id}", response_model=Ticket)
def changer_statut(ticket_id: int, changement: ChangementStatut):
    with connexion() as conn:
        ligne = conn.execute(
            "UPDATE tickets SET statut = %s WHERE id = %s RETURNING *",
            (changement.statut, ticket_id),
        ).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="ticket introuvable")
    return ligne


@app.delete("/api/tickets/{ticket_id}", status_code=204)
def supprimer(ticket_id: int):
    with connexion() as conn:
        res = conn.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="ticket introuvable")
