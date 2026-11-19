CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    titre VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    statut VARCHAR(20) NOT NULL DEFAULT 'ouvert'
        CHECK (statut IN ('ouvert', 'en_cours', 'resolu')),
    priorite VARCHAR(20) NOT NULL DEFAULT 'normale'
        CHECK (priorite IN ('basse', 'normale', 'haute')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
