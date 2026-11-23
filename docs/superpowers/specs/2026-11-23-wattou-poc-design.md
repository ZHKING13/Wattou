# Wattou — POC de suivi et pilotage de l'électricité des ménages (Côte d'Ivoire)

Date : 2026-11-23 · Statut : brouillon à valider

## 1. Intention

Wattou est destiné à devenir un **produit vendu aux ménages ivoiriens**. Le POC doit prouver, d'abord
sur données simulées puis dans un vrai logement (celui du fondateur), que l'on sait résoudre trois
douleurs exprimées par le fondateur :

1. **Le crédit prépayé CIE fond sans qu'on comprenne pourquoi.** → Montrer où part l'argent, en FCFA,
   par appareil, et prévoir quand le crédit sera épuisé.
2. **Des personnes se branchent sur le compteur** (branchements sauvages d'un voisin qui consomme
   aux frais du ménage). → Détecter et alerter.
3. **Impossible de programmer la consommation de certains appareils.** → Programmer et piloter la clim
   et des prises, y compris automatiquement quand le crédit devient bas.

## 2. Objectifs, non-objectifs, anti-objectifs

### Objectifs du POC
- Mesurer la consommation totale du logement en continu (≈ 1 mesure/seconde).
- Reconnaître automatiquement les **gros appareils** (clim, frigo, congélateur, fer à repasser,
  chauffe-eau, ventilateur, TV) et leur attribuer une consommation et un coût.
- Convertir en **FCFA** selon le tarif CIE et estimer le **nombre de jours de crédit restant**.
- Détecter une consommation suspecte (branchement sauvage).
- Programmer la clim (infrarouge) et des prises connectées ; les programmations continuent de
  fonctionner **sans internet**.
- Règle « anti-fin de crédit » : quand le crédit estimé passe sous un seuil, réduire automatiquement
  certains appareils.
- Restituer tout cela dans une **application mobile** avec notifications.

### Critères de réussite (mesurés chez le fondateur, 2 à 4 semaines)
- Coût journalier estimé à **±10 %** de ce que le compteur CIE a réellement décompté.
- Date de fin de crédit prévue à **±1 jour** quand il reste moins de 7 jours.
- Au moins **4 gros appareils** reconnus et correctement étiquetés après confirmation par l'utilisateur.
- Branchement sauvage simulé (une charge de ≥ 300 W non déclarée allumée en mode absence) détecté et
  notifié en **moins de 15 minutes**.
- Une programmation de clim s'exécute correctement avec la box internet débranchée.

### Non-objectifs (hors V1 / hors POC)
- L'eau (SODECI), la répartition de facture en cour commune, la recharge du crédit CIE depuis l'app.
- Notre propre matériel (on utilise du matériel du commerce reprogrammé).
- Reconnaître les petits appareils (chargeurs, ampoules LED) : regroupés dans « autres ».
- iOS (Android d'abord), multi-langue, paiement / abonnement.

### Anti-objectifs (ce qui serait un échec même si « ça marche »)
- **Couper automatiquement un frigo ou un congélateur** (risque alimentaire) : interdit par défaut.
- Afficher des chiffres faussement précis : chaque attribution par appareil est une estimation, et
  l'app doit le dire.
- Un kit qui exige un ingénieur pour chaque installation (acceptable pour le POC, mais tout choix qui
  rendrait cela inévitable en produit est à éviter).
- Fuite de données : la courbe de consommation révèle quand le foyer est absent ; elle doit être
  protégée (authentification, chiffrement en transit).

## 3. Contexte et contraintes

- **Compteurs CIE prépayés** : le ménage achète du crédit (Orange Money, Wave, MTN…). Le compteur
  n'expose aucune donnée exploitable → on pose notre propre capteur.
- **Réseau instable** : délestages, baisses/surtensions, coupures internet → les appareils doivent
  fonctionner localement et le système doit tolérer les trous de données.
- **Téléphones Android d'entrée de gamme et data chère** → app légère, peu de données échangées.
- **Contrainte physique anti-fraude** : la pince doit être clipsée **juste à la sortie du compteur**,
  avant toute dérivation, sinon un branchement sauvage lui échappe.
- **Installation par le ménage lui-même** : aucune intervention sur les fils (pas de dénudage, pas
  d'ouverture du tableau). Il faut que le câble de sortie du compteur soit accessible et qu'une
  prise se trouve à portée du câble de la pince.
- **Installation monophasée 220–230 V / 50 Hz** supposée (cas courant des ménages) ; le triphasé est
  hors POC.
- **Limite de la désagrégation à ~1 Hz** : seuls les appareils à forts paliers marche/arrêt sont
  reconnaissables de façon fiable.

## 4. Approches considérées

### Pour le pilotage (décision du fondateur : A)
- **A. Matériel du commerce reprogrammé (ESPHome)** — retenu. Rapide, peu cher, fonctionne hors ligne,
  la clim se pilote par infrarouge.
- B. Matériel propriétaire — plus tard, une fois le marché validé (6–12 mois, certification).
- C. Pas de pilotage en V1 — rejeté, laisse la douleur n°3 sans réponse.

### Pour le POC (décision du fondateur : C)
- A. Simulé seulement — ne prouve rien sur un vrai foyer.
- B. Réel seulement — bloque le développement en attendant le matériel.
- **C. Simulateur puis kit réel chez le fondateur, même logiciel** — retenu.

### Pour l'architecture logicielle (décision du fondateur : B)
- A. Home Assistant sur Raspberry Pi — rapide mais lourd à installer et ~50 000 FCFA de plus par
  client ; inadapté à un produit grand public.
- **B. Plateforme propre : appareils ESPHome → MQTT → serveur Wattou** — retenu. C'est déjà
  l'architecture du produit, sans boîtier supplémentaire.
- C. Cloud Tuya — rejeté : pas de fonctionnement hors ligne, données pauvres, dépendance fournisseur.

### Pour le capteur de consommation (décision du fondateur : 1)
- Boîtier branché seul sur une prise — rejeté : il voit la tension mais pas le courant des autres
  appareils, donc ni les watts, ni le crédit, ni un branchement sauvage.
- **1. Pince + boîtier branché sur une prise** — retenu. La pince se clipse autour du câble de sortie
  du compteur sans rien couper ; le boîtier, branché sur une prise voisine, en tire son alimentation
  et la référence de tension → vraie puissance à ~1 mesure/seconde. Installable par le ménage.
- 2. Lecteur optique sur la LED « imp/kWh » du compteur — option future : mesure exactement ce que
  la CIE décompte (excellent pour la fraude) mais trop lent pour bien reconnaître les appareils, et
  dépend de l'accès au compteur.
- Module câblé sur l'arrivée par un électricien — rejeté : installation non reproductible à
  l'échelle d'un produit grand public.

### Pour l'interface (décision du fondateur : application mobile)
WhatsApp a été envisagé puis écarté au profit d'une **application mobile** avec notifications push.

## 5. Conception

### 5.1 Vue d'ensemble

```
 Logement                                   Serveur Wattou (cloud)
┌───────────────────────────┐            ┌─────────────────────────────────────┐
│ Pince sortie compteur +   │──MQTT/TLS─▶│ Broker MQTT (Mosquitto)              │
│ boîtier sur prise (ESP32) │            │   │                                  │
│ Prises connectées ESPHome │◀─commandes─│   ▼                                  │
│ Émetteur IR clim ESPHome  │            │ Ingestion ─▶ TimescaleDB (Postgres)   │
└───────────────────────────┘            │ Analyse : événements, appareils,     │
        ▲                                │   coûts, prévision, fraude, règles   │
        │ (remplacé en phase 1 par)      │ API REST (FastAPI) + push (Expo)     │
 Simulateur de logement (Python) ──MQTT─▶│                                      │
                                         └──────────────┬──────────────────────┘
                                                        │ HTTPS
                                                 App mobile (Expo)
```

Le simulateur publie **exactement les mêmes messages MQTT** que les vrais appareils et réagit aux
mêmes commandes. Passer au kit réel = arrêter le simulateur et brancher les appareils.

### 5.2 Kit matériel (proposition — prix indicatifs à vérifier sur le marché local)

| Élément | Choix proposé | Rôle | Prix indicatif |
|---|---|---|---|
| Capteur principal | **Pince ouvrante** 100 A (type SCT-013-000, prise jack) + **boîtier ESP32 avec puce de mesure** (type ATM90E26/ATM90E32, supportée par ESPHome) + **transformateur 230 V → 9 V AC enfichable** dans une prise | La pince donne le courant, le transformateur donne la tension et alimente le boîtier → puissance, tension, courant, facteur de puissance, énergie ≈ 1/s | 25 000 – 35 000 FCFA |
| Prises (×2–3) | Prises **pré-flashées ESPHome avec mesure** (type Athom V2, 16 A, norme FR/Schuko) | Pilotage + mesure de référence par appareil | 8 000 – 12 000 FCFA pièce |
| Émetteur IR clim | ESP32/ESP8266 + module émetteur IR (ESPHome `climate_ir`) | Programmer la clim comme sa télécommande | 5 000 – 8 000 FCFA |

Total ≈ 50 000 – 70 000 FCFA. **Installation par le ménage** : clipser la pince autour du câble de
phase en sortie du compteur, brancher le transformateur sur une prise proche, relier pince et
transformateur au boîtier. Aucun fil secteur n'entre dans le boîtier (seulement du 9 V AC et le
signal de la pince), ce qui le rend sûr à manipuler. La pince ne doit entourer **qu'un seul
conducteur** (la phase) ; le guide d'installation de l'app doit le montrer en photos.

Points d'attention :
- **Distance pince ↔ prise** : prévoir une rallonge de câble de pince de 3 à 5 m ; au-delà, vérifier
  la précision.
- **Étalonnage** : une fois à l'installation, en comparant avec une charge connue (ex. une prise
  connectée du kit qui alimente un appareil) ; le facteur d'étalonnage est stocké par foyer.
- **Sens de la pince** : une pince à l'envers donne une puissance négative ; le boîtier la corrige
  automatiquement (valeur absolue ou inversion détectée à l'installation).

Les prises servent aussi de **vérité terrain** : la consommation qu'elles mesurent permet de valider
la reconnaissance d'appareils.

### 5.3 Firmware (ESPHome)
- Chaque appareil publie en MQTT (TLS, identifiants par appareil) sous
  `wattou/<foyer_id>/<appareil_id>/...`.
- Capteur : puissance active (W), tension, courant, facteur de puissance, énergie cumulée (kWh),
  publiés chaque seconde ; tampon local court si le réseau tombe.
- **Programmations stockées dans l'appareil** (créneaux réglables via MQTT, persistés en mémoire,
  heure via NTP + horloge interne) → exécutées même sans internet.
- Émetteur IR : expose la clim comme un thermostat (marche/arrêt, mode, consigne). Les marques
  courantes (Midea/Coolix, Gree, LG, Samsung…) sont à couvrir selon la clim du fondateur.

### 5.4 Serveur (Python)
- **Stack** : Python 3.12, FastAPI, Mosquitto, PostgreSQL + TimescaleDB, Docker Compose.
- **Ingestion** : abonnement MQTT → table de séries temporelles ; agrégats par minute/heure/jour.
- **Détection d'événements** : repérer les paliers de puissance (ex. +1 150 W, −1 150 W) dans le
  signal 1 Hz, les apparier (allumage/extinction) et les regrouper par signature (puissance,
  facteur de puissance, durée, cycle).
- **Reconnaissance d'appareils** : chaque nouveau groupe stable devient un « appareil inconnu » ;
  l'app demande à l'utilisateur de le nommer (« Nouvel appareil ≈ 1 150 W, souvent vers 20 h.
  Qu'est-ce que c'est ? »). Les appareils sur prise connectée sont connus d'office. Consommation
  non attribuée = « autres / fond ».
- **Coûts** : conversion kWh → FCFA avec une **grille tarifaire CIE configurable** (tranches, tarif
  social / domestique). Les valeurs exactes sont à renseigner et vérifier.
- **Crédit** : l'utilisateur saisit dans l'app le crédit affiché par le compteur (et chaque recharge),
  **en kWh ou en FCFA** selon ce qu'affiche son compteur. On en déduit le crédit restant en temps
  réel à partir de la mesure.
- **Modèle de données multi-foyers** dès le POC (un foyer = un compte + ses appareils), même si un
  seul foyer est utilisé.
- **Prévision** : consommation journalière prévue à partir des jours récents et du profil par jour
  de semaine → « crédit épuisé dans ≈ N jours (date) » et coût prévu du mois.
- **Détection de fraude (branchement sauvage)** :
  1. consommation inexpliquée (hors appareils connus et au-dessus du fond habituel) pendant le
     **mode absence** déclaré dans l'app ;
  2. apparition d'une charge inconnue récurrente aux heures inhabituelles ;
  3. **écart compteur / capteur** : à chaque saisie du crédit, comparer le décompte du compteur CIE
     avec l'énergie mesurée ; un écart durable > 10 % signale une dérivation entre compteur et capteur
     (ou un capteur mal posé).
- **Alertes** : crédit bas, fin de crédit prévue, pic anormal, frigo qui ne s'arrête plus,
  branchement suspect, coupure / retour du courant, tension hors plage dangereuse.
- **Règles et pilotage** : programmations (envoyées aux appareils), et règle « crédit bas » : sous un
  seuil (par défaut 2 jours), couper les prises marquées « non essentielles » et remonter la consigne
  de la clim. Les appareils marqués « essentiels » (frigo, congélateur) ne sont **jamais** coupés.
- **API REST** pour l'app, authentification par compte, notifications via Expo Push.

### 5.5 Application mobile (Expo / React Native, Android d'abord)
Écrans :
- **Accueil** : crédit restant estimé (FCFA + jours), dépense d'aujourd'hui, puissance instantanée.
- **Appareils** : répartition par appareil (jour / semaine / mois, en FCFA et %), appareils inconnus
  à nommer, mention « estimation ».
- **Historique** : courbes de consommation.
- **Contrôle** : clim (marche/arrêt, consigne, programmations), prises, règle « crédit bas ».
- **Sécurité** : mode absence, alertes de branchement suspect.
- **Crédit** : saisie du crédit affiché et des recharges.
- Notifications push pour toutes les alertes.

### 5.6 Simulateur de logement
- Profil type d'un ménage abidjanais : clim ~1 100 W le soir/la nuit, frigo en cycles ~120 W,
  congélateur, ventilateurs ~60 W, TV ~80 W, fer ~1 000 W par épisodes courts, éclairage LED,
  chargeurs, consommation de fond.
- Scénarios injectables : branchement sauvage (charge inconnue de 300–500 W), délestage, coupure
  internet, frigo en panne (ne s'arrête plus), recharge de crédit.
- Accélération du temps (ex. 1 jour en quelques minutes) pour démontrer les prévisions.
- Réagit aux commandes (prises, clim) pour démontrer le pilotage.

### 5.7 Organisation du code (dépôt `Wattou`)
```
firmware/     configurations ESPHome (capteur, prise, IR)
server/       API, ingestion, analyse (Python)
simulator/    simulateur de logement (Python)
mobile/       application Expo
infra/        docker-compose, Mosquitto, base de données
docs/         specs et plans
```

## 6. Phases

1. **Phase 1 — Simulé** : serveur + simulateur + app ; tous les critères démontrables sur le
   simulateur.
2. **Phase 2 — Kit réel** : achat et installation du kit chez le fondateur, firmware ESPHome,
   bascule du simulateur vers les vrais appareils, mesure des critères de réussite sur 2 à 4 semaines.

## 7. Décisions du fondateur vs choix proposés

**Décidé par le fondateur** : cible ménages en Côte d'Ivoire ; les trois douleurs ; pilotage par
matériel du commerce reprogrammé ; capteur « pince + boîtier branché sur une prise »,
installable par le ménage ; POC simulé puis réel chez lui ; plateforme propre ; application
mobile plutôt que WhatsApp ; dépôt `Wattou`.

**Choix proposés (à corriger si besoin)** : nom de travail « Wattou » ; Python/FastAPI/TimescaleDB ;
Expo pour l'app (comme Bustro) ; Android d'abord ; composition du kit ; saisie manuelle du crédit
(lecture photo/OCR plus tard) ; seuil « crédit bas » à 2 jours ; frigo/congélateur jamais coupés ;
critères de réussite chiffrés ; hébergement local en Docker pour le POC.

## 8. Laissé au constructeur
- Algorithme précis de détection de paliers et de regroupement (seuils, fenêtres).
- Modèle de prévision (tant qu'il respecte les critères de réussite).
- Schéma de base de données, format exact des messages MQTT.
- Référence exacte de la puce de mesure et de la carte (assemblée par nous ou carte du commerce),
  selon disponibilité locale, à condition de garder le principe « pince + boîtier sur prise » et
  ≥ 1 mesure/seconde en MQTT.
- Hébergement cloud pour la phase 2.

## 9. Questions ouvertes
- Grille tarifaire CIE exacte applicable au compteur du fondateur (tarif social ou domestique ?).
- Le compteur du fondateur affiche-t-il le crédit restant en kWh ou en FCFA ?
- Marque et modèle de la clim du fondateur (pour le protocole infrarouge).
