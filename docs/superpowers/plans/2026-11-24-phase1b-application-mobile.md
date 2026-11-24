# Wattou Phase 1b — Application mobile : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'application mobile Wattou (Android d'abord) qui montre au ménage où part son crédit
CIE, le prévient d'un branchement suspect et lui permet de piloter clim et prises, en consommant
l'API de la phase 1a.

**Architecture:** Application Expo Router dans `mobile/`. Une couche `api/` (client HTTP typé +
types du contrat) est la seule à parler au serveur ; un hook `useRessource` gère chargement,
rafraîchissement et cache hors ligne ; les écrans ne contiennent que de l'affichage et des appels
à ces deux couches. La logique pure (formatage, validation, échelles de graphique) est testée
en Node ; les écrans avec React Native Testing Library et un faux client.

**Tech Stack:** Expo SDK 58, expo-router, TypeScript, react-native-svg (graphiques),
expo-secure-store (jeton), expo-sqlite/kv-store (cache), expo-notifications, Jest (jest-expo) +
@testing-library/react-native. Mêmes versions que `apps/mobile` de Bustro.

**Spec:** `docs/superpowers/specs/2026-11-23-wattou-poc-design.md` (§5.5, §2 anti-objectifs) ;
API : `server/src/wattou/api/` (phase 1a, branche `develop`).

## Global Constraints

- Interface **en français**, tutoiement exclu (vouvoiement), vocabulaire du ménage : « crédit »,
  « compteur », « clim », « prise » — jamais « kWh » seul sans équivalent FCFA à côté sur l'Accueil.
- Montants en **FCFA sans décimales**, espace fine comme séparateur de milliers : `12 500 F`.
  Énergie : 1 décimale, virgule : `3,4 kWh`. Jours de crédit : 1 décimale : `4,8 jours`.
- Toute consommation par appareil est affichée avec la mention **« Estimation »** (anti-objectif
  spec : pas de chiffres faussement précis).
- Le frigo/congélateur (appareils `essential`) n'offre **aucun** bouton de coupure dans l'app.
- Android d'abord ; écrans utilisables à 360 dp de large ; zones tactiles ≥ 48 dp.
- Data chère : l'Accueil se rafraîchit toutes les **60 s seulement quand il est affiché** ;
  les autres écrans au focus et au tirer-pour-rafraîchir. Pas d'appel en arrière-plan.
- URL de l'API : `EXPO_PUBLIC_API_URL` (comme Bustro) ; build hors dev sans URL = erreur.
- Jeton JWT dans expo-secure-store uniquement ; jamais dans les logs ni le cache.
- Commits : Conventional Commits en français, sans ligne Co-Authored-By ni mention d'IA.

## Contrat API consommé (préfixe `/api/v1`, JSON, `Authorization: Bearer <jeton>`)

| Appel | Corps / paramètres | Réponse |
|---|---|---|
| `POST /auth/register` | `{phone, password (≥6), foyer_name}` | 201 `{token, foyer_id}` ; 409 numéro déjà inscrit |
| `POST /auth/login` | `{phone, password}` | `{token, foyer_id}` ; 401 |
| `GET /foyer/summary` | — | `{power_w, today_kwh, today_fcfa, price_fcfa_kwh, credit_kwh\|null, credit_fcfa\|null, days_left\|null, depletion_at\|null, month_forecast_fcfa, absence_mode, low_credit_days, data_until\|null}` |
| `GET /foyer/appliances` | `period=day\|week\|month` | `[{id, label\|null, power_w\|null, kwh, fcfa, share, estimated, essential, device_id\|null}]` (inclut `fond`, `autres`) |
| `PATCH /appliances/{id}` | `{label?, essential?}` | 200 ; 404 |
| `GET /foyer/history` | `from, to` (ISO), `step=hour\|day` | `[{ts, kwh}]` |
| `POST /foyer/credit` | `{kind:"reading"\|"recharge", kwh>0, amount_fcfa?}` | 201 ; 422 `{detail}` (message lisible) |
| `PUT /foyer/absence` | `{enabled}` | 200 |
| `PUT /foyer/rules` | `{low_credit_days: 0,5–10}` | 200 ; 422 |
| `GET /alerts` | `unread=true?` | `[{id, ts, kind, message, read}]` |
| `POST /alerts/{id}/read` | — | 200 ; 404 |
| `GET /devices` | — | `[{id, kind:"meter"\|"plug"\|"ir_ac", name, essential, last_state, schedule}]` |
| `POST /devices/{id}/command` | plug `{on}` ; ir_ac `{mode?, setpoint_c? (16–30)}` | 202 ; 404 ; 422 ; **503 pilotage indisponible** |
| `PUT /devices/{id}/schedule` | `{slots:[{at:"HH:MM", days:[0-6], action}]}` | 200 |
| `POST /push-tokens` | `{token}` | 201 |

Erreurs : `{detail: string}` (FastAPI). Kinds d'alerte : `absence_load`, `meter_gap`,
`night_unknown`, `credit_low`, `low_credit_rule`, `peak`, `stuck`, `outage`, `voltage`.

## Review Focus

1. **Pas de réseau / serveur injoignable** : l'écran affiche les dernières données en cache avec
   « Données de 14 h 32 — hors connexion », jamais un écran vide ou une erreur brute → test Task 4.
2. **Jeton expiré (401)** sur n'importe quel appel : retour à la connexion, sans boucle ni plantage
   → test Task 3.
3. **Foyer sans relevé de crédit** (`credit_kwh: null`) : l'Accueil invite « Saisissez le crédit
   affiché par votre compteur » au lieu d'afficher 0 → test Task 5.
4. **Kit déconnecté** (`data_until` vieux de > 5 min, ou null) : bandeau « Le capteur n'envoie plus
   de mesures depuis … » ; la puissance instantanée n'est pas affichée comme actuelle → test Task 5.
5. **Commande refusée (503 pilotage indisponible, 422)** : le bouton revient à son état précédent et
   le message du serveur est affiché → test Task 8.

---

## Structure des fichiers

```
mobile/
  package.json, app.config.ts, babel.config.js, tsconfig.json, jest.config.js, eas.json
  app/                         routes expo-router
    _layout.tsx                polices, fournisseurs, garde d'authentification
    (auth)/connexion.tsx, (auth)/inscription.tsx
    (onglets)/_layout.tsx      barre d'onglets : Accueil, Appareils, Historique, Contrôle, Alertes
    (onglets)/index.tsx, appareils.tsx, historique.tsx, controle.tsx, alertes.tsx
    credit.tsx                 modale de saisie du crédit
    programmation/[id].tsx     éditeur de programmation d'un appareil
  src/
    api/types.ts, api/client.ts, api/erreurs.ts
    session/stockage.ts, session/SessionContext.tsx
    donnees/useRessource.ts, donnees/cache.ts
    format.ts                  FCFA, kWh, jours, heures relatives
    graphique/echelle.ts, graphique/Barres.tsx
    programmation/creneaux.ts  validation / tri des créneaux
    notifications/push.ts
    ecrans/…                   un composant par écran (les fichiers app/ ne font qu'importer)
    ui/…                       Carte, Bouton, Bandeau, Pastille, ChampNombre, Interrupteur
    theme.ts
  test/…                       *.test.ts (Node) et *.test.tsx (écrans)
```

---

### Task 1: Socle de l'application, thème et formatage

**Files:**
- Create: `mobile/package.json`, `mobile/app.config.ts`, `mobile/babel.config.js`, `mobile/tsconfig.json`,
  `mobile/jest.config.js` (deux projets `logique` / `ecrans` comme Bustro), `mobile/eas.json`,
  `mobile/src/theme.ts`, `mobile/src/format.ts`, `mobile/test/format.test.ts`, `Makefile` (cible `mobile-test`)

**Interfaces:**
- Produces (`format.ts`) : `fcfa(n: number): string`, `kwh(n: number): string`, `jours(n: number): string`,
  `heure(iso: string): string` (« 14 h 32 »), `depuis(iso: string, maintenant: Date): string`
  (« il y a 12 min », « il y a 3 h », « hier à 21 h 05 »), `date(iso: string): string` (« mar. 24 nov. »).
- Produces (`theme.ts`) : `couleurs` (clair/sombre via `useColorScheme`), `espace`, `police` ;
  palette : fond, texte, accent (vert énergie), alerte (orange), danger (rouge), neutre.
- `app.config.ts` : nom « Wattou », slug `wattou`, scheme `wattou`, `android.package` `ci.wattou.app`,
  plugins `expo-router`, `expo-secure-store`, `expo-notifications`, `extra.apiUrl` comme Bustro
  (erreur si vide hors dev).

- [ ] **Step 1:** Tests `format.test.ts` :
  `fcfa(12500) === "12 500 F"` (U+202F), `fcfa(0) === "0 F"`, `fcfa(1234.6) === "1 235 F"` ;
  `kwh(3.44) === "3,4 kWh"` ; `jours(4.75) === "4,8 jours"`, `jours(1) === "1,0 jour"` ;
  `heure("2026-11-24T14:32:00Z") === "14 h 32"` (fuseau `Africa/Abidjan`) ;
  `depuis` : 12 min → « il y a 12 min », 3 h → « il y a 3 h », veille 21:05 → « hier à 21 h 05 ».
- [ ] **Step 2:** `cd mobile && npx jest test/format.test.ts` → FAIL (module absent).
- [ ] **Step 3:** Initialiser le projet (dépendances de la Tech Stack, versions de `apps/mobile` Bustro), implémenter `format.ts` avec `Intl` (`fr-FR`, `timeZone: "Africa/Abidjan"`).
- [ ] **Step 4:** Tests → PASS ; `npx tsc --noEmit` → aucune erreur.
- [ ] **Step 5:** Commit `chore(mobile): initialise l'application Expo et le formatage`.

---

### Task 2: Client API typé

**Files:**
- Create: `mobile/src/api/types.ts`, `mobile/src/api/erreurs.ts`, `mobile/src/api/client.ts`, `mobile/test/client.test.ts`

**Interfaces:**
- Produces (`types.ts`) : `Resume`, `Appareil`, `PointHistorique`, `Alerte`, `KindAlerte`, `Dispositif`,
  `CommandePrise {on}`, `CommandeClim {mode?, setpoint_c?}`, `Programmation {slots: Creneau[]}`,
  `Creneau {at, days, action}`, `Periode = "day"|"week"|"month"` — champs exactement ceux du contrat.
- Produces (`erreurs.ts`) : `HorsLigne`, `NonAutorise`, `Refuse(statut, message)` (4xx avec `detail`),
  `ErreurServeur(statut)` (5xx hors 503), `PilotageIndisponible` (503).
- Produces (`client.ts`) : `creerApi({baseUrl, jeton: () => Promise<string|null>, fetch?}): Api` avec une
  méthode par ligne du contrat : `inscrire`, `connecter`, `resume`, `appareils(periode)`, `renommer(id, label)`,
  `historique(from, to, step)`, `saisirCredit(corps)`, `absence(enabled)`, `regles(jours)`, `alertes()`,
  `lireAlerte(id)`, `dispositifs()`, `commander(id, cmd)`, `programmer(id, prog)`, `enregistrerPush(token)`.
  Délai 15 s (corps compris) → `HorsLigne` ; `TypeError` de fetch → `HorsLigne`.

- [ ] **Step 1:** Tests avec un faux `fetch` : `resume` envoie `Authorization: Bearer j` et renvoie le JSON ;
  401 → `NonAutorise` ; 422 `{"detail":"Ce relevé…"}` → `Refuse` avec ce message ; 503 → `PilotageIndisponible` ;
  500 → `ErreurServeur` ; fetch qui rejette `TypeError` → `HorsLigne` ; fetch qui ne répond pas (timers simulés 15 s) → `HorsLigne` ;
  `historique` encode `from`/`to` en query ; `connecter` n'envoie pas d'en-tête Authorization si jeton null.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): ajoute le client de l'API Wattou`.

---

### Task 3: Session et écrans d'authentification

**Files:**
- Create: `mobile/src/session/stockage.ts`, `mobile/src/session/SessionContext.tsx`, `mobile/src/dependances.ts`,
  `mobile/app/_layout.tsx`, `mobile/app/(auth)/connexion.tsx`, `mobile/app/(auth)/inscription.tsx`,
  `mobile/src/ecrans/Connexion.tsx`, `mobile/src/ecrans/Inscription.tsx`, `mobile/test/session.test.tsx`

**Interfaces:**
- Consumes: `creerApi`, `NonAutorise`.
- Produces: `Dependances {api: Api, stockage: StockageJeton, cache: Cache, maintenant: () => Date, push: Push}`
  injectées par `<Fournisseurs deps>` ; `useDeps()` ; `useSession(): {etat: "chargement"|"connecte"|"deconnecte", connecter(phone, pw), inscrire(phone, pw, nomFoyer), deconnecter()}`.
  Toute `NonAutorise` levée par un appel passe par `signalerNonAutorise()` du contexte → jeton effacé, état `deconnecte`.
- `_layout.tsx` redirige vers `(auth)/connexion` si déconnecté, vers `(onglets)` sinon.
- Écrans : numéro (format CI, 10 chiffres, préfixe `+225` ajouté), mot de passe (≥ 6), nom du foyer (inscription).
  Messages : 401 « Numéro ou mot de passe incorrect. » ; 409 « Ce numéro a déjà un compte. » ; HorsLigne « Pas de connexion internet. »

- [ ] **Step 1:** Tests (faux `Api`, faux stockage) : inscription réussie → jeton stocké, écran Accueil affiché ;
  connexion 401 → message affiché, reste sur l'écran ; mot de passe de 5 caractères → bouton désactivé ;
  **un appel qui renvoie `NonAutorise` depuis un écran connecté → retour à la connexion et jeton effacé** (Review Focus 2) ;
  relance de l'app avec jeton stocké → directement sur l'Accueil.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): ajoute la connexion et l'inscription`.

---

### Task 4: Données : chargement, rafraîchissement et cache hors ligne

**Files:**
- Create: `mobile/src/donnees/cache.ts`, `mobile/src/donnees/useRessource.ts`, `mobile/src/ui/BandeauEtat.tsx`, `mobile/test/useRessource.test.tsx`

**Interfaces:**
- Produces: `Cache {lire<T>(cle): Promise<{valeur: T, le: string}|null>, ecrire<T>(cle, valeur): Promise<void>}`
  (impl. `expo-sqlite/kv-store`, faux en mémoire pour les tests) ;
  `useRessource<T>(cle: string, charger: () => Promise<T>, options?: {intervalleMs?: number}): {donnees: T|null, etat: "chargement"|"pret"|"hors_ligne"|"erreur", le: string|null, rafraichir(): Promise<void>}` —
  au montage : affiche le cache immédiatement puis charge ; succès → écrit le cache ; `HorsLigne`/`ErreurServeur` → garde
  les données du cache avec `etat: "hors_ligne"` ; `intervalleMs` ne tourne que quand l'écran a le focus (`useIsFocused`).
  Le cache est vidé à la déconnexion (clé préfixée par `foyer_id`).
- Produces: `<BandeauEtat etat le />` : « Données de 14 h 32 — hors connexion » ; rien si `pret`.

- [ ] **Step 1:** Tests : cache présent + réseau coupé → données du cache affichées et bandeau « hors connexion » (Review Focus 1) ;
  pas de cache + réseau coupé → message « Pas de connexion internet. » avec bouton « Réessayer » ;
  succès → cache écrit ; intervalle 60 s → 2 appels après 60 s focus, 1 seul si écran sans focus (timers simulés).
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): charge les données avec cache hors ligne`.

---

### Task 5: Accueil et saisie du crédit

**Files:**
- Create: `mobile/app/(onglets)/_layout.tsx`, `mobile/app/(onglets)/index.tsx`, `mobile/app/credit.tsx`,
  `mobile/src/ecrans/Accueil.tsx`, `mobile/src/ecrans/Credit.tsx`, `mobile/test/accueil.test.tsx`, `mobile/test/credit.test.tsx`

**Interfaces:**
- Consumes: `api.resume`, `api.saisirCredit`, `useRessource` (`intervalleMs: 60_000`), `format`.
- Accueil, de haut en bas :
  1. Grand chiffre « **4,8 jours** de crédit » + « ≈ 3 120 F restants » + « épuisement prévu jeu. 26 nov. vers 18 h » ;
     sous le seuil `low_credit_days` → carte en couleur alerte.
  2. « Aujourd'hui : 1 850 F (12,3 kWh) » ; « Ce mois-ci : ≈ 38 000 F prévus ».
  3. « En ce moment : 1 150 W ».
  4. Bouton « Saisir le crédit du compteur » → modale `credit`.
- **Sans relevé** (`credit_kwh === null`) : la carte 1 devient « Saisissez le crédit affiché par votre compteur pour voir combien de jours il vous reste » + bouton (Review Focus 3).
- **Capteur muet** (`data_until` null ou plus vieux que 5 min selon `deps.maintenant()`) : bandeau
  « Le capteur n'envoie plus de mesures depuis {depuis(data_until)}. Vérifiez qu'il est branché. » et la ligne 3 devient
  « Dernière mesure : 1 150 W ({heure}) » (Review Focus 4).
- Modale Crédit : deux onglets « Relevé du compteur » (kWh affichés) et « Recharge » (montant FCFA + kWh obtenus) ;
  succès → ferme et rafraîchit l'Accueil ; 422 → affiche `detail` sous le champ.

- [ ] **Step 1:** Tests : résumé complet → textes « 4,8 jours », « 3 120 F », « 1 850 F » ; `credit_kwh: null` → invitation à saisir, aucun « 0 jour » ;
  `data_until` vieux de 10 min → bandeau capteur ; `days_left < low_credit_days` → carte en style alerte (testID) ;
  modale : relevé 60 → `saisirCredit({kind:"reading", kwh:60})` ; recharge sans montant → bouton désactivé ; 422 → message serveur affiché.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): affiche le crédit restant et permet de le saisir`.

---

### Task 6: Appareils

**Files:**
- Create: `mobile/app/(onglets)/appareils.tsx`, `mobile/src/ecrans/Appareils.tsx`, `mobile/src/ecrans/NommerAppareil.tsx`, `mobile/test/appareils.test.tsx`

**Interfaces:**
- Consumes: `api.appareils(periode)`, `api.renommer`.
- Sélecteur « Aujourd'hui / 7 jours / 30 jours » (`day/week/month`). Liste triée par FCFA décroissant : nom, barre de part (%),
  « 2 340 F · 35 % », pastille **« Estimation »** sur chaque ligne d'appareil (pas sur `fond`/`autres`).
- `label === null` → « Appareil inconnu (≈ 1 100 W) » + bouton « Nommer » → feuille avec suggestions
  (Clim, Frigo, Congélateur, Ventilateur, Télévision, Fer à repasser, Chauffe-eau, Autre…) + champ libre ≤ 60 caractères → `renommer`.
- `fond` → « Consommation de fond (veilles, box) » ; `autres` → « Autres petits appareils ».
- Liste vide (pas encore de données) → « Wattou apprend à reconnaître vos appareils. Revenez demain. »

- [ ] **Step 1:** Tests : ordre par FCFA ; « Estimation » présent sur les appareils et absent sur fond/autres ; inconnu → « Appareil inconnu (≈ 1 100 W) » ;
  nommer « Clim » → `renommer(id, "Clim")` puis liste rechargée ; changement de période → `appareils("week")` ; liste vide → message d'apprentissage.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): montre la consommation par appareil`.

---

### Task 7: Historique

**Files:**
- Create: `mobile/src/graphique/echelle.ts`, `mobile/src/graphique/Barres.tsx`, `mobile/app/(onglets)/historique.tsx`,
  `mobile/src/ecrans/Historique.tsx`, `mobile/test/echelle.test.ts`, `mobile/test/historique.test.tsx`

**Interfaces:**
- Produces (`echelle.ts`) : `type Fenetre = {from: string, to: string, step: "hour"|"day"}` ; `fenetre(vue: "jour"|"semaine"|"mois", maintenant: Date): Fenetre`
  (jour = aujourd'hui minuit → maintenant, pas horaire ; semaine = 7 j, pas jour ; mois = 30 j, pas jour) ;
  `completer(points: PointHistorique[], f: Fenetre): PointHistorique[]` (seaux manquants à 0 — un trou de mesure reste visible comme 0) ;
  `graduations(max: number): number[]` (3–5 valeurs « rondes » en kWh, max ≥ plus haute barre).
- Produces (`Barres.tsx`) : diagramme en barres react-native-svg, axe Y gradué en kWh, axe X (heures ou jours), barre touchée → info-bulle « 21 h : 1,4 kWh · 210 F ».
- Écran : sélecteur Jour/Semaine/Mois, total de la période en FCFA et kWh au-dessus du graphique (prix = `price_fcfa_kwh` du résumé en cache).

- [ ] **Step 1:** Tests `echelle` : `fenetre("jour", 24/11 15:20)` → from 24/11 00:00Z, step hour ; `completer` avec 3 points sur 15 heures → 16 seaux dont 13 à 0 ;
  `graduations(3.7)` → `[0, 1, 2, 3, 4]` ; `graduations(0)` → `[0, 1]`.
  Test écran : vue Semaine → `historique(from, to, "day")` et total « 84,2 kWh · 10 525 F ».
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): affiche l'historique de consommation`.

---

### Task 8: Contrôle — clim, prises, programmations, règle crédit bas

**Files:**
- Create: `mobile/src/programmation/creneaux.ts`, `mobile/app/(onglets)/controle.tsx`, `mobile/app/programmation/[id].tsx`,
  `mobile/src/ecrans/Controle.tsx`, `mobile/src/ecrans/Programmation.tsx`, `mobile/test/creneaux.test.ts`, `mobile/test/controle.test.tsx`

**Interfaces:**
- Consumes: `api.dispositifs`, `api.commander`, `api.programmer`, `api.regles`, `api.resume` (seuil actuel).
- Produces (`creneaux.ts`) : `trier(c: Creneau[]): Creneau[]` (par heure), `valider(c: Creneau[]): string|null`
  (doublon même heure et même jour → « Deux actions sont programmées le lundi à 06:00. » ; aucun jour coché → « Choisissez au moins un jour. »),
  `resumer(c: Creneau): string` (« Lun–Ven 06:00 : éteindre » ; « Tous les jours 19:00 : allumer à 26 °C »).
- Écran Contrôle :
  - **Clim** (`ir_ac`) : interrupteur Marche/Arrêt (`{mode:"cool"|"off"}`), consigne − / + entre 16 et 30 °C (`{setpoint_c}`), conseil fixe
    « Chaque degré en plus réduit la consommation de la clim d'environ 6 % » ; lien « Programmer ».
  - **Prises** (`plug`) : nom, puissance actuelle, interrupteur ; prise `essential` → pas d'interrupteur, mention
    « Toujours allumée (appareil essentiel) ».
  - **Règle crédit bas** : « Quand il reste moins de [2] jours de crédit, couper les prises non essentielles et régler la clim sur 27 °C »,
    sélecteur 1 / 2 / 3 / 5 jours → `regles(jours)`.
- Mise à jour optimiste : l'interrupteur bascule tout de suite ; si `commander` échoue (`PilotageIndisponible` → « Le pilotage est
  momentanément indisponible. Réessayez dans un instant. » ; `Refuse` → son message), il **revient à l'état précédent** et le message s'affiche (Review Focus 5).
- Éditeur de programmation : liste des créneaux (`resumer`), ajout (heure, jours, action selon le type), suppression, enregistrement → `programmer` ; `valider` bloque l'enregistrement.

- [ ] **Step 1:** Tests `creneaux` : tri, doublon détecté, aucun jour → erreur, `resumer` des deux exemples ci-dessus.
  Tests écran : prise frigo essentielle → pas d'interrupteur ; bascule prise fer → `commander("prise-fer", {on:false})` ;
  503 → interrupteur revenu à « allumé » + message pilotage indisponible ; consigne 26 → + → `{setpoint_c:27}`, bornée à 30 ;
  règle 3 jours → `regles(3)`.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): pilote la clim et les prises`.

---

### Task 9: Alertes et sécurité (mode absence)

**Files:**
- Create: `mobile/app/(onglets)/alertes.tsx`, `mobile/src/ecrans/Alertes.tsx`, `mobile/test/alertes.test.tsx`

**Interfaces:**
- Consumes: `api.alertes`, `api.lireAlerte`, `api.absence`, `api.resume` (`absence_mode`).
- En tête : grand interrupteur **« Je m'absente »** — activé : « Wattou vous prévient si quelque chose consomme pendant votre absence. »
- Liste des alertes, récentes d'abord : icône et couleur par kind (fraude `absence_load`/`meter_gap`/`night_unknown` = danger ;
  `credit_low`/`low_credit_rule`/`peak`/`stuck`/`voltage` = alerte ; `outage` = neutre), message du serveur tel quel, `depuis(ts)` ;
  non lue en gras ; toucher → `lireAlerte(id)`. Badge du nombre de non lues sur l'onglet.
- Liste vide → « Aucune alerte. Tout va bien. »

- [ ] **Step 1:** Tests : activer « Je m'absente » → `absence(true)` ; alerte `absence_load` affichée en style danger ; toucher une alerte non lue → `lireAlerte(id)` et plus en gras ;
  badge onglet = nombre de non lues ; liste vide → message.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): affiche les alertes et le mode absence`.

---

### Task 10: Notifications push

**Files:**
- Create: `mobile/src/notifications/push.ts`, `mobile/test/push.test.ts` ; Modify: `mobile/src/session/SessionContext.tsx`, `mobile/app/_layout.tsx`

**Interfaces:**
- Produces: `Push {demanderEtEnregistrer(api: Api): Promise<"ok"|"refuse"|"indisponible">}` — après connexion : permission
  (Android 13+), canal Android « Alertes Wattou » (importance haute), `getExpoPushTokenAsync({projectId})` puis `api.enregistrerPush(token)` ;
  sans `projectId` EAS (dev) ou sur simulateur → `"indisponible"` sans erreur. Réessayé à chaque démarrage (idempotent côté serveur).
- Toucher une notification → onglet Alertes.

- [ ] **Step 1:** Tests (expo-notifications simulé) : permission accordée → `enregistrerPush("ExponentPushToken[x]")` ; refusée → `"refuse"`, aucun appel ;
  pas de projectId → `"indisponible"` ; réponse à une notification → navigation vers `/alertes`.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(mobile): reçoit les alertes en notification`.

---

### Task 11: Vérification contre le vrai serveur

**Files:**
- Create: `mobile/test/integration/api.test.ts`, `mobile/README.md` ; Modify: `Makefile` (cible `mobile-integration`), `README.md`

**Interfaces:**
- Consumes: `creerApi` (Task 2) contre l'API de la phase 1a lancée localement (`make up`, API sur `WATTOU_API_URL`) et le simulateur.
- Test ignoré si `WATTOU_API_URL` absent. Scénario : inscription → simulateur 1 jour en rattrapage (`--backfill-days 1`) → attendre `data_until` →
  `resume` (champs du contrat présents, `credit_kwh` null) → `saisirCredit` relevé 50 puis relevé 60 → `Refuse` 422 avec message → `appareils("day")` non vide avec `estimated` →
  `dispositifs` contient `clim` et `prise-fer` → `commander("prise-fer", {on:false})` 202 → `absence(true)` → `alertes()` est un tableau.
- `mobile/README.md` : lancer l'app sur Android (Expo Go / build de développement) contre l'API locale, variables `EXPO_PUBLIC_API_URL`.

- [ ] **Step 1:** Écrire le test d'intégration.
- [ ] **Step 2:** `make mobile-integration` sans serveur → test ignoré ; avec serveur + simulateur → PASS (le contrat du client correspond à l'API réelle).
- [ ] **Step 3:** `cd mobile && npx jest && npx tsc --noEmit` → tout passe.
- [ ] **Step 4:** Commit `test(mobile): vérifie le client contre l'API réelle`.

---

## Hors de ce plan

- Build EAS / publication Play Store, icône et écran de démarrage définitifs (identité visuelle à décider).
- Assistant d'installation du kit (photos de pose de la pince) — avec le kit réel, phase 2.
- iOS, multi-langue (dioula, baoulé…), paiement / recharge CIE depuis l'app (non-objectifs de la spec).
