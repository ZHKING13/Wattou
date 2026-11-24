# Identité visuelle Wattou — piste B « Malin »

Choisie le 2026-11-24 parmi trois pistes (canevas de comparaison : https://claude.ai/artifact/E9WRJGs1HMrZ9RnQryfMrL).

## Positionnement

Wattou est un **conseiller malin qui fait économiser** : un voisin débrouillard plutôt qu'un comptable.
L'ampoule souriante est le personnage des conseils.

## Couleurs (`mobile/src/theme.ts`)

| Rôle | Clair | Sombre |
|---|---|---|
| Fond | Crème `#FFF8F0` | Nuit `#1B2A41` |
| Surface | `#FFFFFF` | `#24364F` |
| Texte | Nuit `#1B2A41` | Crème `#FFF8F0` |
| Corail vif (barres, graphiques, ampoule — sans texte dessus) | `#FF6B35` | `#FF8A5C` |
| Corail des surfaces avec texte (boutons, conseil, onglet actif) | `#CC4A1F` | `#CC4A1F` |
| Texte sur le corail | Blanc `#FFFFFF` | Blanc `#FFFFFF` |
| Carte nuit : fond / texte / chiffre | `#1B2A41` / `#FFF8F0` / `#FF8A5C` | `#0F1A2B` / `#FFF8F0` / `#FF8A5C` |
| Accent en texte (liens, boutons secondaires) | `#C2410C` | `#FF9E78` |
| Alerte / danger / succès | `#B45309` / `#C0262D` / `#1E7F52` | `#F5B041` / `#FF8A8E` / `#4CC985` |

Tout texte respecte un contraste d'au moins 4,5:1 (vérifié par `mobile/test/theme.test.tsx`).
Le texte sur le corail est blanc : le corail des surfaces qui portent du texte est donc plus foncé (`#CC4A1F`, 4,6:1) que le corail vif de la marque (blanc sur `#FF6B35` = 2,9:1, illisible).

## Typographie

- Titres et grands chiffres : **Baloo 2** (ExtraBold, Bold), ronde et chaleureuse.
- Texte : **Nunito Sans** (Regular, Bold).
- Polices embarquées dans l'app (`@expo-google-fonts`), utilisables hors connexion.

## Logo et icône

- Ampoule souriante crème sur cercle ou carré corail, yeux et culot bleu nuit (`mobile/assets/`).
- Pas d'emoji dans l'interface.

## Ton

- **Vouvoiement** (le tutoiement de la piste reste à valider avec des ménages).
- Conseils concrets et chiffrés en FCFA : « Réglez la clim sur 26 °C ce soir : vous gardez ≈ 2 100 F ce mois-ci. »
- Phrases courtes, vocabulaire du ménage : crédit, compteur, clim, prise.

## À vérifier

- Qu'aucune application concurrente en Côte d'Ivoire n'utilise déjà une ampoule souriante comme logo.
- Le nom « Wattou » (disponibilité de la marque et des noms de domaine).
