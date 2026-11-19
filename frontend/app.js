const API = (window.API_URL || "http://localhost:8000").replace(/\/$/, "");

const LIBELLES = { ouvert: "Ouvert", en_cours: "En cours", resolu: "Résolu" };

const liste = document.getElementById("liste");
const formulaire = document.getElementById("formulaire");
const message = document.getElementById("message");
const filtre = document.getElementById("filtre");
const recherche = document.getElementById("recherche");
const etatApi = document.getElementById("etat-api");

async function appel(chemin, options = {}) {
  const reponse = await fetch(API + chemin, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!reponse.ok) {
    throw new Error("Erreur " + reponse.status);
  }
  return reponse.status === 204 ? null : reponse.json();
}

async function verifierApi() {
  try {
    await appel("/health");
    etatApi.textContent = "API : en ligne";
    etatApi.className = "etat ok";
  } catch {
    etatApi.textContent = "API : injoignable";
    etatApi.className = "etat ko";
  }
}

function afficher(tickets) {
  liste.innerHTML = "";
  if (tickets.length === 0) {
    liste.innerHTML = '<li class="vide">Aucun ticket.</li>';
    return;
  }
  for (const t of tickets) {
    const li = document.createElement("li");
    li.className = "ticket statut-" + t.statut;

    const titre = document.createElement("h3");
    titre.textContent = t.titre;

    const desc = document.createElement("p");
    desc.textContent = t.description;

    const infos = document.createElement("p");
    infos.className = "infos";
    const date = new Date(t.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
    infos.textContent = `#${t.id} · priorité ${t.priorite} · créé le ${date}`;

    const actions = document.createElement("div");
    actions.className = "actions";

    const choix = document.createElement("select");
    choix.setAttribute("aria-label", "Statut du ticket " + t.id);
    for (const [valeur, libelle] of Object.entries(LIBELLES)) {
      const opt = document.createElement("option");
      opt.value = valeur;
      opt.textContent = libelle;
      opt.selected = valeur === t.statut;
      choix.appendChild(opt);
    }
    choix.addEventListener("change", () => changerStatut(t.id, choix.value));

    const supprimer = document.createElement("button");
    supprimer.className = "secondaire";
    supprimer.textContent = "Supprimer";
    supprimer.addEventListener("click", () => supprimerTicket(t.id));

    actions.append(choix, supprimer);
    li.append(titre, desc, infos, actions);
    liste.appendChild(li);
  }
}

async function charger() {
  const params = new URLSearchParams();
  if (filtre.value) params.set("statut", filtre.value);
  if (recherche.value.trim()) params.set("q", recherche.value.trim());
  try {
    const tickets = await appel("/api/tickets" + (params.toString() ? "?" + params : ""));
    afficher(tickets);
  } catch (e) {
    liste.innerHTML = '<li class="vide">Impossible de charger les tickets (' + e.message + ").</li>";
  }
}

async function changerStatut(id, statut) {
  try {
    await appel("/api/tickets/" + id, { method: "PATCH", body: JSON.stringify({ statut }) });
  } catch (e) {
    alert("Le statut n'a pas pu être modifié : " + e.message);
  }
  charger();
}

async function supprimerTicket(id) {
  if (!confirm("Supprimer le ticket #" + id + " ?")) return;
  try {
    await appel("/api/tickets/" + id, { method: "DELETE" });
  } catch (e) {
    alert("Suppression impossible : " + e.message);
  }
  charger();
}

formulaire.addEventListener("submit", async (event) => {
  event.preventDefault();
  const donnees = {
    titre: formulaire.titre.value.trim(),
    description: formulaire.description.value.trim(),
    priorite: formulaire.priorite.value,
  };
  try {
    await appel("/api/tickets", { method: "POST", body: JSON.stringify(donnees) });
    formulaire.reset();
    message.textContent = "Ticket créé.";
    message.className = "message ok";
    charger();
  } catch (e) {
    message.textContent = "Création impossible : " + e.message;
    message.className = "message ko";
  }
});

let minuteur;
recherche.addEventListener("input", () => {
  clearTimeout(minuteur);
  minuteur = setTimeout(charger, 300);
});
filtre.addEventListener("change", charger);

verifierApi();
charger();
