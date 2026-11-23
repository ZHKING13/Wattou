# Wattou Phase 1a — Serveur + simulateur : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un serveur Wattou qui ingère les mesures MQTT d'un foyer, reconnaît les gros appareils,
calcule coûts, crédit restant et prévision, détecte la fraude, émet des alertes, pilote prises et
clim, et expose tout via une API REST — démontré de bout en bout avec un simulateur de logement.

**Architecture:** Le simulateur publie les mêmes messages MQTT que le futur kit ESPHome. Un worker
d'ingestion les écrit dans PostgreSQL/TimescaleDB ; un worker d'analyse exécute toutes les 60 s
des fonctions pures (paliers, appareils, crédit, prévision, fraude, alertes, règles) ; une API
FastAPI sert l'app mobile (plan 1b, séparé). Toute la logique d'analyse est en fonctions pures
testées sans base ; seule la couche `repo` touche la base.

**Tech Stack:** Python ≥ 3.12, uv, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, aiomqtt,
Mosquitto 2, TimescaleDB (PostgreSQL 16), pytest + pytest-asyncio, httpx, ruff, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-11-23-wattou-poc-design.md`

## Global Constraints

- Fuseau : Côte d'Ivoire = `Africa/Abidjan` = UTC+0 toute l'année. Tous les horodatages sont UTC
  ISO-8601 ; « heure locale » = heure UTC.
- **Horloge des données** : le « maintenant » d'un foyer est l'horodatage de sa dernière mesure
  (jamais `datetime.now()` dans l'analyse), pour que le simulateur accéléré fonctionne.
- Installation monophasée 230 V / 50 Hz ; mesure du capteur ≈ 1 message/seconde.
- Le crédit CIE est saisi **en kWh** (ce qu'affiche le compteur) ; recharges = montant FCFA + kWh.
- Prix du kWh = moyenne pondérée des 3 dernières recharges ; repli : `TARIF_FCFA_KWH_DEFAUT`
  (variable d'environnement, valeur par défaut `110`, à vérifier — question ouverte de la spec).
- Seuil « crédit bas » par défaut : **2 jours**, réglable par foyer.
- Appareils `essential=true` (frigo, congélateur) : **jamais** coupés par une règle automatique.
- Clim en règle crédit bas : consigne remontée à **27 °C** (jamais abaissée).
- Toute consommation par appareil exposée par l'API porte `estimated: true`.
- Fraude : charge inexpliquée **≥ 300 W** en mode absence → alerte en **< 15 min** (données).
  Écart compteur/capteur **> 10 %** sur 2 intervalles consécutifs (décompte ≥ 2 kWh) → alerte.
- Données de consommation : API authentifiée (JWT) ; MQTT avec identifiants (TLS en phase 2).
- Commits : Conventional Commits, en français, **sans** ligne Co-Authored-By ni mention d'IA
  (CLAUDE.md du dépôt).

## Contrat MQTT (partagé simulateur ↔ serveur, recopié tel quel des deux côtés)

Préfixe `wattou/{foyer_id}/{device_id}/…` ; `foyer_id` = UUID texte ; `device_id` = slug `[a-z0-9-]+`.

| Topic | Sens | Retenu | Payload JSON |
|---|---|---|---|
| `…/meta` | appareil → serveur | oui | `{"kind": "meter"\|"plug"\|"ir_ac", "name": str, "essential": bool}` |
| `…/state` (meter) | appareil → serveur | non | `{"ts": str, "p_w": float, "v": float, "i_a": float, "pf": float, "e_kwh": float}` |
| `…/state` (plug) | appareil → serveur | non | `{"ts": str, "p_w": float, "on": bool}` |
| `…/state` (ir_ac) | appareil → serveur | non | `{"ts": str, "mode": "off"\|"cool"\|"fan", "setpoint_c": int}` |
| `…/cmd` | serveur → appareil | non | plug `{"on": bool}` ; ir_ac `{"mode": str, "setpoint_c": int}` (champs optionnels) |
| `…/schedule` | serveur → appareil | oui | `{"slots": [{"at": "HH:MM", "days": [0-6], "action": <cmd>}]}` (0 = lundi) |

`ts` = horodatage de mesure (horloge simulée en phase 1). Les plugs/ir_ac publient `state` toutes
les 10 s et à chaque changement.

## Review Focus

1. **Trous de données** (délestage, coupure internet) : un trou de > 120 s ne doit ni créer de faux
   paliers, ni compter d'énergie, ni faire planter l'analyse → test dans Task 6 et Task 10.
2. **Messages MQTT invalides ou d'un foyer inconnu** : ignorés et journalisés, l'ingestion continue
   → test dans Task 5.
3. **Foyer sans aucune recharge ni lecture de crédit** : le résumé renvoie `credit_kwh: null`,
   `days_left: null` au lieu d'une erreur → tests dans Task 8 et Task 13.
4. **Lecture de crédit incohérente** (kWh lu supérieur au précédent sans recharge entre les deux,
   faute de frappe) : refusée en 422 avec message clair → test dans Task 13.
5. **Pince posée à l'envers** (puissances négatives) : valeur absolue à l'ingestion → test dans Task 5.

---

## Structure des fichiers

```
infra/docker-compose.yml          mosquitto + timescaledb (+ api, ingest, analysis, sim)
infra/mosquitto/mosquitto.conf, passwd
server/pyproject.toml             paquet `wattou`
server/alembic.ini, server/migrations/
server/src/wattou/
  config.py        Settings (pydantic-settings)
  contract.py      modèles pydantic du contrat MQTT + parse_topic()
  db.py            moteur/session async
  models.py        tables SQLAlchemy
  repo.py          requêtes (seul module qui parle à la base)
  ingest.py        worker MQTT → base
  analysis/
    types.py       dataclasses partagées (Sample, Step, Activation, …)
    steps.py       détection et appariement de paliers
    appliances.py  regroupement en appareils + attribution d'énergie
    credit.py      prix kWh, crédit restant, prévision
    fraud.py       détection de branchement sauvage
    alerts.py      autres alertes
    rules.py       règle crédit bas
  control.py       publication cmd/schedule
  notify.py        Notifier (Expo push + log)
  worker.py        boucle d'analyse 60 s
  api/  app.py, auth.py, routes_*.py, schemas.py
server/tests/…     (miroir de src)
simulator/pyproject.toml          paquet `wattou_sim`
simulator/src/wattou_sim/
  contract.py      copie du contrat (mêmes modèles)
  appliances.py    modèles d'appareils
  household.py     profil ménage abidjanais + scénarios
  runner.py        horloge accélérée, publication MQTT, commandes, vérité terrain
  __main__.py      CLI
simulator/tests/…
tests_e2e/test_acceptance.py
Makefile
```

---

### Task 1: Socle du dépôt et infrastructure

**Files:**
- Create: `infra/docker-compose.yml`, `infra/mosquitto/mosquitto.conf`, `infra/mosquitto/passwd`,
  `server/pyproject.toml`, `server/src/wattou/__init__.py`, `server/src/wattou/config.py`,
  `server/tests/test_config.py`, `simulator/pyproject.toml`, `simulator/src/wattou_sim/__init__.py`,
  `Makefile`, `.gitignore`, `README.md`

**Interfaces:**
- Produces: `wattou.config.Settings` avec `database_url: str`, `mqtt_host: str`, `mqtt_port: int = 1883`,
  `mqtt_user: str`, `mqtt_password: str`, `jwt_secret: str`, `tarif_fcfa_kwh_defaut: float = 110.0`,
  `expo_push_enabled: bool = False` ; `get_settings() -> Settings` (cache). Préfixe env `WATTOU_`
  sauf `TARIF_FCFA_KWH_DEFAUT`.
- Produces: `make up` (compose : `db` timescale/timescaledb:latest-pg16 port 5432, `mqtt`
  eclipse-mosquitto:2 port 1883, auth par fichier passwd, utilisateurs `server` et `device`),
  `make test` (pytest serveur + simulateur), `make lint` (ruff).

- [ ] **Step 1:** Test `test_settings_from_env` : avec `WATTOU_DATABASE_URL`, `WATTOU_MQTT_HOST`,
  `WATTOU_JWT_SECRET` posés via `monkeypatch`, `Settings()` les lit et `tarif_fcfa_kwh_defaut == 110.0`.
- [ ] **Step 2:** `cd server && uv run pytest tests/test_config.py -v` → FAIL (module absent).
- [ ] **Step 3:** Écrire pyprojects (src layout, deps de la stack), `config.py`, compose, Makefile.
- [ ] **Step 4:** `uv run pytest tests/test_config.py -v` → PASS ; `make up && docker compose -f infra/docker-compose.yml ps` → `db` et `mqtt` healthy.
- [ ] **Step 5:** Commit `chore: initialise le serveur, le simulateur et l'infrastructure`.

---

### Task 2: Contrat MQTT et modèles d'appareils du simulateur

**Files:**
- Create: `simulator/src/wattou_sim/contract.py`, `simulator/src/wattou_sim/appliances.py`,
  `simulator/src/wattou_sim/household.py`, `simulator/tests/test_appliances.py`,
  `simulator/tests/test_household.py`

**Interfaces:**
- Produces (`contract.py`) : modèles pydantic `Meta`, `MeterState`, `PlugState`, `AcState`,
  `PlugCmd`, `AcCmd`, `Schedule`, `ScheduleSlot` exactement selon le contrat ; `topic(foyer_id, device_id, leaf) -> str`.
- Produces (`appliances.py`) : classe abstraite `Appliance(name: str, essential: bool)` avec
  `power_w(t: datetime) -> float` et `pf: float` ; implémentations :
  - `Cyclic(name, on_w, on_s, off_s, pf)` — frigo 120 W 15 min/25 min pf 0,8 ; congélateur 150 W 20/20 pf 0,8
  - `Scheduled(name, on_w, windows: list[tuple[time, time]], pf, jitter_min=15, seed)` — clim, TV, ventilateur, éclairage
  - `Bursty(name, on_w, bursts_per_day, burst_s, active_hours, pf, seed)` — fer à repasser 1 000 W
  - `Constant(name, w, pf)` — fond (box, veilles) 25 W
  Le hasard est déterministe par `seed` et par jour (`random.Random(hash((seed, date)))`).
- Produces (`household.py`) : `abidjan_household(seed: int = 1) -> Household` ; `Household.appliances: list[Appliance]` ;
  `Household.total(t) -> tuple[float, float]` (W, pf pondéré) ; `Household.breakdown(t) -> dict[str, float]` ;
  scénarios `Household.add_scenario(s)` où `s` ∈ `NeighborTap(start, end, w=400)`,
  `FridgeStuck(start)` (frigo toujours ON), `Outage(start, end)` (rien publié), `NetCut(start, end)` (messages bufferisés puis rejoués).
  Composition du ménage : clim 1 100 W (19:00–23:30 et 01:00–05:30), frigo, congélateur, 2 ventilateurs
  60 W (12:00–16:00, 21:00–06:00), TV 80 W (18:30–23:00), fer 1 000 W (2 épisodes × 8 min/jour, 06:00–08:00 et 18:00–20:00),
  éclairage 40 W (18:30–23:30), fond 25 W.

- [ ] **Step 1:** Tests :
  - `test_cyclic_duty_cycle` : sur 24 h échantillonnées à 1 s, frigo ON ≈ 15/40 du temps (±2 %) à 120 W.
  - `test_scheduled_off_outside_windows` : clim à 10:00 → 0 W ; à 21:00 → 1 100 W.
  - `test_bursty_energy` : fer sur une journée ≈ 2×8 min×1 000 W = 0,267 kWh (±10 %).
  - `test_household_breakdown_sums_to_total` : pour 100 instants, `sum(breakdown) == total[0]`.
  - `test_neighbor_tap_adds_power` : avec `NeighborTap` actif, total augmente de 400 W et `breakdown["voisin"] == 400`.
  - `test_deterministic` : deux ménages même seed → mêmes valeurs.
- [ ] **Step 2:** `cd simulator && uv run pytest -v` → FAIL.
- [ ] **Step 3:** Implémenter les trois modules.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat(simulator): modélise les appareils d'un ménage abidjanais`.

---

### Task 3: Runner du simulateur (MQTT, horloge accélérée, commandes, vérité terrain)

**Files:**
- Create: `simulator/src/wattou_sim/runner.py`, `simulator/src/wattou_sim/__main__.py`,
  `simulator/tests/test_runner.py`

**Interfaces:**
- Consumes: Task 2.
- Produces: `SimClock(start: datetime, speed: float)` avec `now() -> datetime` ;
  `Runner(household, foyer_id, publisher, clock)` avec `async step(t) -> list[tuple[str, str]]`
  (topic, payload JSON) pour l'instant `t`, `handle_command(device_id, payload)` ;
  `Publisher` protocole `async publish(topic, payload, retain=False)` (impl. `MqttPublisher` aiomqtt
  et `ListPublisher` pour les tests) ; vérité terrain écrite dans `truth.csv`
  (`ts,appareil,p_w`, une ligne par minute et par appareil, énergie moyenne de la minute).
- CLI : `python -m wattou_sim --foyer <uuid> [--speed 60] [--start 2026-11-01T00:00:00Z]
  [--backfill-days 14] [--scenario neighbor_tap@<iso>/<iso>] [--scenario fridge_stuck@<iso>]
  [--scenario outage@<iso>/<iso>] [--scenario netcut@<iso>/<iso>] [--truth truth.csv]`.
  `--backfill-days N` publie N jours aussi vite que possible (pas de sleep) puis continue au rythme `--speed`.
- Appareils publiés : `meter` (meter), `prise-tv` (plug, TV), `prise-fer` (plug, fer, non essentiel),
  `prise-frigo` (plug, frigo, essential=true), `clim` (ir_ac). Au démarrage, `meta` retenus.
- Compteur : `e_kwh` cumulatif ; `v` = 228 ± 4 V bruité ; `i_a = p_w / (v*pf)`.
- Commandes : `prise-*/cmd {"on": false}` coupe l'appareil dans le ménage simulé (sa puissance tombe à 0
  jusqu'à `{"on": true}`) ; `clim/cmd` change mode/consigne ; consigne ≥ 27 °C réduit la puissance clim de 30 % ;
  `…/schedule` stocké et exécuté par le simulateur à l'heure simulée (comme le ferait ESPHome).

- [ ] **Step 1:** Tests (avec `ListPublisher`, sans broker) :
  - `test_meter_message_each_second` : 10 pas d'1 s → 10 messages `meter/state` valides (`MeterState`).
  - `test_energy_accumulates` : 1 h à 1 000 W constant → `e_kwh` final ≈ 1,0 (±0,5 %).
  - `test_plug_cmd_off_cuts_power` : après `handle_command("prise-fer", {"on": false})` pendant un épisode, la puissance totale baisse de 1 000 W.
  - `test_schedule_executes_at_sim_time` : schedule `{"at": "06:00", "action": {"mode": "off"}}` sur la clim → à 06:00 simulé, état clim `off`.
  - `test_outage_publishes_nothing` et `test_netcut_replays_buffer` (messages rejoués avec leurs `ts` d'origine).
  - `test_truth_csv_matches_breakdown` : la somme des lignes d'une minute = moyenne du total.
- [ ] **Step 2:** `uv run pytest tests/test_runner.py -v` → FAIL.
- [ ] **Step 3:** Implémenter `runner.py` et la CLI.
- [ ] **Step 4:** Tests → PASS ; `make up` puis `uv run python -m wattou_sim --foyer 00000000-0000-0000-0000-000000000001 --speed 60` et `mosquitto_sub -t 'wattou/#' -C 5` → 5 messages reçus.
- [ ] **Step 5:** Commit `feat(simulator): publie les mesures MQTT avec horloge accélérée et scénarios`.

---

### Task 4: Schéma de base de données et dépôt (`repo`)

**Files:**
- Create: `server/src/wattou/db.py`, `server/src/wattou/models.py`, `server/src/wattou/repo.py`,
  `server/src/wattou/contract.py` (copie conforme de celui du simulateur, + `parse_topic(topic) -> tuple[UUID, str, str]`),
  `server/alembic.ini`, `server/migrations/versions/0001_initial.py`, `server/tests/conftest.py`, `server/tests/test_repo.py`

**Interfaces:**
- Tables (toutes avec `foyer_id` sauf `users`) :
  - `foyers(id uuid pk, name, absence_mode bool=false, low_credit_days float=2, created_at)`
  - `users(id uuid pk, phone unique, password_hash, foyer_id fk)`
  - `devices(id text, foyer_id, kind, name, essential bool, last_state jsonb, pk(foyer_id,id))`
  - `meter_readings(foyer_id, ts timestamptz, p_w, v, i_a, pf, e_kwh)` — hypertable sur `ts`, pk `(foyer_id, ts)`, `ON CONFLICT DO NOTHING`
  - `plug_readings(foyer_id, device_id, ts, p_w, on bool)` — hypertable
  - `appliances(id uuid pk, foyer_id, label text null, delta_w float, pf float, n_obs int, device_id text null, essential bool=false)`
  - `activations(id bigserial, foyer_id, appliance_id, start_ts, end_ts null, delta_w)`
  - `credit_entries(id bigserial, foyer_id, ts, kind 'reading'|'recharge', kwh float, amount_fcfa int null)`
  - `alerts(id bigserial, foyer_id, ts, kind text, message text, read bool=false, dedup_key text, unique(foyer_id, dedup_key))`
  - `push_tokens(foyer_id, token, pk(foyer_id, token))`
  - `analysis_state(foyer_id pk, last_ts timestamptz)`
- Produces (`repo.py`, fonctions async prenant `session: AsyncSession`) :
  `create_foyer(name) -> UUID`, `upsert_device(foyer_id, device_id, meta)`, `insert_meter(foyer_id, MeterState)`,
  `insert_plug(foyer_id, device_id, PlugState)`, `meter_samples(foyer_id, start, end) -> list[Sample]`,
  `latest_ts(foyer_id) -> datetime | None`, `foyer_exists(foyer_id) -> bool`,
  `credit_entries(foyer_id) -> list[CreditEntry]`, `add_credit_entry(...)`, `add_alert(foyer_id, ts, kind, message, dedup_key) -> bool` (False si doublon),
  `list_appliances`, `save_appliances`, `add_activations`, `energy_by_bucket(foyer_id, start, end, step: 'minute'|'hour'|'day') -> list[tuple[datetime, float]]` (via `time_bucket`).
- `conftest.py` : fixture `session` sur `WATTOU_TEST_DATABASE_URL` (base de compose), migrations appliquées une fois, transaction annulée après chaque test.
- `analysis/types.py` créé ici : `Sample(ts, p_w, pf)`, `CreditEntry(ts, kind, kwh, amount_fcfa)`.

- [ ] **Step 1:** Tests : `test_insert_meter_idempotent` (même ts deux fois → une ligne), `test_meter_samples_ordered`,
  `test_energy_by_bucket_hour` (3 600 échantillons à 1 000 W → 1 seau ≈ 1,0 kWh), `test_add_alert_dedup` (2ᵉ appel même clé → False).
- [ ] **Step 2:** `make up && cd server && uv run pytest tests/test_repo.py -v` → FAIL.
- [ ] **Step 3:** Implémenter modèles, migration (`CREATE EXTENSION IF NOT EXISTS timescaledb`, `create_hypertable`), repo.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5:** Commit `feat(server): ajoute le schéma de données et le dépôt`.

---

### Task 5: Worker d'ingestion MQTT

**Files:**
- Create: `server/src/wattou/ingest.py`, `server/tests/test_ingest.py`

**Interfaces:**
- Consumes: `contract.parse_topic`, `repo.upsert_device/insert_meter/insert_plug/foyer_exists`.
- Produces: `async handle_message(session, topic: str, payload: bytes) -> None` (pure vis-à-vis de MQTT, testable) ;
  `async run_ingest(settings)` (abonnement `wattou/+/+/#`, écriture par lots de 1 s). `python -m wattou.ingest`.
- Règles : foyer inconnu ou JSON invalide → `logger.warning` et retour sans exception ; `p_w` négatif → `abs()`
  (et `pf` → `abs()`) ; `ir_ac/state` et `plug/state` mettent à jour `devices.last_state`.

- [ ] **Step 1:** Tests : `test_meter_state_stored`, `test_meta_creates_device`, `test_unknown_foyer_ignored`,
  `test_invalid_json_ignored` (aucune exception, rien écrit), `test_negative_power_made_absolute` (−850 W → 850 W).
- [ ] **Step 2:** → FAIL. **Step 3:** Implémenter. **Step 4:** → PASS ; avec compose + simulateur, `SELECT count(*) FROM meter_readings` croît.
- [ ] **Step 5:** Commit `feat(server): ingère les mesures MQTT`.

---

### Task 6: Détection et appariement des paliers

**Files:**
- Create: `server/src/wattou/analysis/steps.py`, `server/tests/analysis/test_steps.py`

**Interfaces:**
- Consumes: `Sample`.
- Produces: `Step(ts: datetime, delta_w: float, pf: float)` ; `Activation(start: datetime, end: datetime | None, delta_w: float, pf: float)` ;
  `detect_steps(samples: list[Sample], min_delta_w: float = 80, settle_s: int = 3, max_gap_s: int = 120) -> list[Step]` ;
  `pair_steps(steps: list[Step], open_: list[Activation], tol: float = 0.15) -> tuple[list[Activation], list[Activation]]`
  (activations fermées, activations encore ouvertes).
- Algorithme `detect_steps` : pour chaque i, `avant = médiane(p[i-settle:i])`, `après = médiane(p[i:i+settle])` ;
  palier si `|après-avant| ≥ min_delta_w` ; fusionner les candidats contigus en gardant le plus grand |delta| ;
  `pf` = médiane des pf après. Ne jamais comparer à travers un trou > `max_gap_s` (segmenter d'abord).
- Algorithme `pair_steps` : palier positif → nouvelle activation ouverte ; palier négatif → ferme l'activation
  ouverte la plus récente dont `|delta + step.delta| ≤ tol × delta` ; sinon ignoré.

- [ ] **Step 1:** Tests : `test_single_on_off` (0→1 100→0 W donne +1 100 et −1 100), `test_noise_below_threshold_ignored`
  (bruit ±30 W → aucun palier), `test_overlapping_appliances_paired` (frigo 120 W s'allume pendant la clim, s'éteint avant elle → 2 activations correctes),
  `test_gap_creates_no_step` (trou de 10 min entre 0 W et 1 000 W → aucun palier).
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(analysis): détecte et apparie les paliers de puissance`.

---

### Task 7: Reconnaissance d'appareils et attribution d'énergie

**Files:**
- Create: `server/src/wattou/analysis/appliances.py`, `server/tests/analysis/test_appliances.py`

**Interfaces:**
- Consumes: `Activation`, `Sample`.
- Produces: `ApplianceSig(id: UUID, label: str | None, delta_w: float, pf: float, n_obs: int, device_id: str | None, essential: bool)` ;
  `assign(activations, sigs, tol: float = 0.15) -> tuple[list[tuple[Activation, UUID]], list[ApplianceSig]]`
  (affectation au signal le plus proche en `delta_w` si écart relatif ≤ tol et |Δpf| ≤ 0,15, sinon nouveau signal `label=None` ;
  `delta_w` du signal mis à jour en moyenne glissante) ;
  `promote_after: int = 3` — un signal n'est exposé (« appareil inconnu à nommer ») qu'après 3 observations ;
  `attribute(samples, assigned, plug_energy: dict[str, float]) -> dict[str, float]` (kWh par clé : id d'appareil,
  `"fond"` = 5ᵉ percentile de la puissance de 00:00–05:00 × durée, `"autres"` = reste, jamais négatif).
  Les appareils sur prise (`device_id` non nul) prennent l'énergie mesurée par la prise et leurs activations NILM
  à ±15 % de leur puissance sont exclues pour éviter le double comptage.

- [ ] **Step 1:** Tests : `test_same_appliance_grouped` (5 activations ≈1 100 W → 1 signal, n_obs=5),
  `test_distinct_appliances` (120 W et 1 100 W → 2 signaux), `test_promoted_after_three`,
  `test_attribution_sums_to_total` (somme des clés = énergie totale ±0,1 %), `test_plug_energy_not_double_counted`.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(analysis): reconnaît les appareils et répartit l'énergie`.

---

### Task 8: Prix du kWh, crédit restant et prévision

**Files:**
- Create: `server/src/wattou/analysis/credit.py`, `server/tests/analysis/test_credit.py`

**Interfaces:**
- Consumes: `CreditEntry`.
- Produces:
  - `price_per_kwh(entries, default: float) -> float` — Σ FCFA / Σ kWh des 3 dernières recharges ; `default` si aucune.
  - `remaining_kwh(entries, measured_kwh_since: Callable[[datetime], float]) -> float | None` — dernière lecture,
    plus les recharges postérieures, moins l'énergie mesurée depuis la lecture ; `None` si aucune lecture ; plancher 0.
  - `validate_reading(entries, new_kwh, measured_since_last: float) -> str | None` — message d'erreur si
    `new_kwh > dernière_lecture + recharges_depuis + 0,5` (sinon None).
  - `forecast_daily_kwh(daily: list[tuple[date, float]], target: date) -> float` — moyenne des 7 derniers jours complets ;
    si ≥ 2 mêmes jours de semaine dans les 28 derniers jours, 50/50 avec leur moyenne.
  - `depletion(remaining, now, daily_history, hourly_profile: list[float]) -> tuple[float, datetime] | None` —
    consomme jour par jour (reste du jour courant au prorata de `hourly_profile`) jusqu'à épuisement ; renvoie (jours décimaux, date/heure).

- [ ] **Step 1:** Tests : `test_price_weighted` (recharges 5 000 F/40 kWh et 10 000 F/80 kWh → 125 F/kWh), `test_price_default`,
  `test_remaining_after_consumption` (lecture 50 kWh, 12 kWh mesurés → 38), `test_remaining_with_recharge` (+ recharge 40 → 78),
  `test_remaining_none_without_reading`, `test_validate_reading_rejects_increase`, `test_forecast_constant` (7 jours à 8 kWh → 8),
  `test_depletion_days` (38 kWh, 8 kWh/j, à minuit → 4,75 j).
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(analysis): calcule le crédit restant et prévoit son épuisement`.

---

### Task 9: Détection des branchements sauvages

**Files:**
- Create: `server/src/wattou/analysis/fraud.py`, `server/tests/analysis/test_fraud.py`

**Interfaces:**
- Consumes: `Sample`, `ApplianceSig`, activations ouvertes, `CreditEntry`, énergie mesurée.
- Produces: dans `analysis/types.py`, `Alert(kind: str, ts: datetime, message: str, dedup_key: str)` (utilisé aussi par la Task 10) ;
  kinds de fraude : `"absence_load"`, `"meter_gap"`, `"night_unknown"` ;
  - `check_absence(samples, open_activations, sigs, baseline_w, absence: bool) -> Alert | None` — en mode absence,
    `inexpliqué = p - baseline - Σ(delta des activations ouvertes d'appareils essentiels)` ; alerte si ≥ 300 W en continu sur 10 min.
    Message : « Consommation de {w} W détectée alors que vous êtes absent. Un appareil ou un branchement inconnu consomme sur votre compteur. »
  - `check_meter_gap(entries, measured_between: Callable[[datetime, datetime], float]) -> Alert | None` — sur les deux derniers
    intervalles entre lectures : `décompte = lecture_prec + recharges - lecture` ; alerte si `décompte ≥ 2` et `(décompte - mesuré)/décompte > 0,10` pour les deux.
    Message : « Votre compteur a décompté {d} kWh mais Wattou n'en a mesuré que {m}. Quelque chose consomme entre le compteur et le capteur. »
  - `check_night_unknown(activations_by_sig: dict[UUID, list[Activation]], sigs) -> list[Alert]` — signal non étiqueté actif entre 23:00 et 05:00 sur ≥ 3 nuits distinctes des 7 derniers jours.

- [ ] **Step 1:** Tests : `test_absence_tap_detected_within_15_min` (400 W apparaît à t0 → alerte à t0+10 min),
  `test_absence_fridge_not_flagged`, `test_no_alert_when_present`, `test_meter_gap_two_intervals`, `test_meter_gap_single_interval_ignored`,
  `test_night_unknown_three_nights`.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(analysis): détecte les branchements sauvages`.

---

### Task 10: Autres alertes et notifications

**Files:**
- Create: `server/src/wattou/analysis/alerts.py`, `server/src/wattou/notify.py`,
  `server/tests/analysis/test_alerts.py`, `server/tests/test_notify.py`

**Interfaces:**
- Consumes: `Alert` (Task 9, `analysis/types.py`).
- Produces (`alerts.py`) :
  - `check_credit(days_left, threshold) -> Alert | None` — « Il vous reste environ {n} jours de crédit (épuisement prévu le {date}). » ; dédup par jour.
  - `check_peak(hourly_today: list[float], hourly_7d_avg: list[float]) -> Alert | None` — heure écoulée > 150 % de la moyenne et > 0,5 kWh.
  - `check_stuck(open_activations, sigs, now) -> list[Alert]` — appareil étiqueté frigo/congélateur ouvert depuis > 3 h : « Votre {label} ne s'arrête plus depuis 3 h : il est peut-être en panne. »
  - `check_outage(samples, max_gap_s=120) -> list[Alert]` — « Coupure de courant de {d} min (de {h1} à {h2}). »
  - `check_voltage(samples) -> Alert | None` — v < 180 ou > 250 V pendant ≥ 10 s.
- Produces (`notify.py`) : protocole `Notifier.send(tokens: list[str], title: str, body: str)` ; `ExpoNotifier` (POST https://exp.host/--/api/v2/push/send, httpx) ; `LogNotifier`.

- [ ] **Step 1:** Tests pour chaque `check_*` (cas positif + négatif) ; `test_expo_payload` (httpx mocké, corps conforme à l'API Expo).
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(analysis): ajoute les alertes et l'envoi de notifications`.

---

### Task 11: Pilotage — commandes, programmations, règle crédit bas

**Files:**
- Create: `server/src/wattou/control.py`, `server/src/wattou/analysis/rules.py`,
  `server/tests/test_control.py`, `server/tests/analysis/test_rules.py`

**Interfaces:**
- Produces (`control.py`) : `async send_command(publisher, foyer_id, device_id, cmd: PlugCmd | AcCmd)` ;
  `async set_schedule(publisher, foyer_id, device_id, schedule: Schedule)` (retenu) ; publisher = protocole `Publisher` (même forme que Task 3).
- Produces (`rules.py`) : `low_credit_actions(days_left: float | None, threshold: float, devices: list[DeviceView]) -> list[tuple[str, PlugCmd | AcCmd]]` —
  si `days_left < threshold` : `{"on": false}` pour chaque plug non essentiel allumé ; pour la clim en `cool` avec consigne < 27 → `{"setpoint_c": 27}`.
  `DeviceView(id, kind, essential, last_state: dict)`.

- [ ] **Step 1:** Tests : `test_low_credit_cuts_non_essential`, `test_low_credit_never_cuts_essential`, `test_ac_setpoint_raised_to_27`,
  `test_ac_setpoint_never_lowered` (consigne 29 → aucune action), `test_no_action_above_threshold`, `test_schedule_published_retained`.
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(server): pilote les appareils et applique la règle crédit bas`.

---

### Task 12: Worker d'analyse

**Files:**
- Create: `server/src/wattou/worker.py`, `server/tests/test_worker.py`

**Interfaces:**
- Consumes: Tasks 4–11.
- Produces: `async analyze_foyer(session, publisher, notifier, foyer_id) -> None` ; `async run_worker(settings, interval_s=60)` ; `python -m wattou.worker`.
- Déroulé pour un foyer : lire `analysis_state.last_ts` → échantillons `(last_ts - 10 s, latest_ts]` → paliers → appariement
  (activations ouvertes persistées) → affectation aux signaux → sauvegarde → fraude/alertes (insertion dédupliquée ; push seulement si insertion nouvelle)
  → règle crédit bas → commandes → `last_ts = latest_ts`. Traiter au plus 6 h de données par passage (rattrapage du backfill par tranches).

- [ ] **Step 1:** Test d'intégration (base de test + `ListPublisher` + `LogNotifier`) : insérer 2 h d'échantillons avec une clim 1 100 W
  allumée 3 fois → après `analyze_foyer`, 1 appareil, 3 activations ; deuxième appel sans nouvelles données → rien de nouveau ;
  `test_low_credit_triggers_command` (crédit 1 kWh, conso 8 kWh/j → commande `{"on": false}` publiée sur `prise-fer/cmd`).
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(server): orchestre l'analyse périodique des foyers`.

---

### Task 13: API REST

**Files:**
- Create: `server/src/wattou/api/app.py`, `auth.py`, `schemas.py`, `routes_auth.py`, `routes_foyer.py`,
  `routes_devices.py`, `routes_alerts.py`, `server/tests/api/test_*.py`

**Interfaces (toutes sous `/api/v1`, JSON, JWT Bearer sauf auth) :**
- `POST /auth/register {phone, password, foyer_name}` → `{token, foyer_id}` ; `POST /auth/login {phone, password}` → `{token, foyer_id}`.
  Mot de passe ≥ 6 caractères, hachage argon2.
- `GET /foyer/summary` → `{power_w, today_kwh, today_fcfa, price_fcfa_kwh, credit_kwh|null, credit_fcfa|null, days_left|null, depletion_at|null, month_forecast_fcfa, absence_mode, low_credit_days}`
  (`month_forecast_fcfa` = énergie du mois écoulé + `forecast_daily_kwh` × jours restants du mois, × prix)
- `GET /foyer/appliances?period=day|week|month` → `[{id, label|null, kwh, fcfa, share, estimated: true, essential, device_id|null}]` + entrées `fond` et `autres`
- `PATCH /appliances/{id} {label?, essential?}`
- `GET /foyer/history?from&to&step=minute|hour|day` → `[{ts, kwh}]`
- `POST /foyer/credit {kind: "reading"|"recharge", kwh, amount_fcfa?}` → 201 ; 422 avec le message de `validate_reading`
  (« Ce relevé est plus élevé que le précédent sans recharge entre les deux. Vérifiez le chiffre affiché par le compteur. »)
- `PUT /foyer/absence {enabled}` ; `PUT /foyer/rules {low_credit_days}` (0,5–10)
- `GET /alerts?unread=true` ; `POST /alerts/{id}/read`
- `GET /devices` ; `POST /devices/{id}/command <PlugCmd|AcCmd>` ; `GET|PUT /devices/{id}/schedule <Schedule>`
- `POST /push-tokens {token}`
- `python -m wattou.api` (uvicorn, port 8000). Le temps « aujourd'hui » vient de l'horloge des données.

- [ ] **Step 1:** Tests httpx `AsyncClient` : `test_register_login`, `test_requires_auth` (401), `test_summary_without_credit_returns_nulls`,
  `test_credit_reading_increase_rejected_422`, `test_appliances_marked_estimated`, `test_command_published` (publisher factice injecté),
  `test_foyer_isolation` (un utilisateur ne voit pas les alertes d'un autre foyer → 404).
- [ ] **Step 2–4:** FAIL → implémenter → PASS.
- [ ] **Step 5:** Commit `feat(api): expose le résumé, les appareils, le crédit et le pilotage`.

---

### Task 14: Test d'acceptation de bout en bout

**Files:**
- Create: `tests_e2e/test_acceptance.py`, `tests_e2e/conftest.py` ; Modify: `infra/docker-compose.yml` (services `api`, `ingest`, `worker`), `Makefile` (`make e2e`), `README.md` (démarrage rapide)

**Interfaces:**
- Consumes: tout ce qui précède, la CLI du simulateur, `truth.csv`.
- Scénario : `make up` (tous services) → inscription via API → simulateur `--backfill-days 14 --speed 600` avec une lecture de crédit
  (saisie via API au jour 7 à 60 kWh, recharge au jour 10 : 10 000 F / 80 kWh, lecture au jour 14) et `neighbor_tap` la nuit du jour 13 avec mode absence activé
  → attendre que le worker ait rattrapé (`analysis_state.last_ts` = dernière mesure).

- [ ] **Step 1:** Assertions (critères de réussite de la spec, mesurés sur le simulateur) :
  - `test_daily_cost_within_10pct` : pour chacun des jours 8–14, `history(step=day)` à ±10 % de la vérité terrain.
  - `test_four_appliances_recognized` : après étiquetage via `PATCH` des signaux proches de 1 100/1 000/150/120 W, ≥ 4 appareils dont l'énergie attribuée est à ±25 % de la vérité.
  - `test_depletion_within_one_day` : prévision faite au jour 14 vs épuisement réel obtenu en prolongeant la simulation (± 1 jour).
  - `test_tap_alert_within_15_min` : alerte `absence_load` horodatée < 15 min après le début de `neighbor_tap`.
  - `test_low_credit_rule_cuts_iron` : quand `days_left < 2`, `prise-fer` reçoit `{"on": false}` et jamais `prise-frigo`.
- [ ] **Step 2:** `make e2e` → FAIL au premier lancement si un seuil n'est pas atteint ; ajuster les paramètres (tolérances, seuils) des Tasks 6–9, pas les assertions.
- [ ] **Step 3:** `make e2e` → PASS.
- [ ] **Step 4:** Commit `test: vérifie les critères de réussite du POC sur le simulateur`.

---

## Hors de ce plan

- **Plan 1b — application mobile Expo** (écrans de la spec §5.5, notifications push) : plan séparé, consomme l'API de la Task 13.
- Phase 2 : firmware ESPHome, TLS MQTT, hébergement cloud, installation chez le fondateur.
