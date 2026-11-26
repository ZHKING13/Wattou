# Wattou — application mobile

Application Expo (Android d'abord) qui consomme l'API Wattou (`server/`).

## Lancer sur un téléphone Android

```bash
cd mobile
npm install
EXPO_PUBLIC_API_URL=http://<ip-du-serveur>:8000 npx expo start
```

Ouvrez le projet dans un build de développement (`eas build --profile development`) ou Expo Go.
Sur l'émulateur Android, le serveur local est joignable à `http://10.0.2.2:8000`.

Pour avoir des données : `make app` (ou API + ingestion + analyse lancées à la main), créez un compte
dans l'app, puis lancez le simulateur avec le `foyer_id` du compte (voir le README racine).

## Build Android (EAS)

Projet EAS : `@zetreyy/wattou`. Avant le premier build de test, remplacez dans `eas.json`
(profil `preview`) l'adresse provisoire `https://REMPLACER-PAR-URL-RAILWAY.invalid` par l'URL publique
de l'API sur Railway (voir `infra/railway/README.md`), puis :

```bash
eas build --platform android --profile preview
```

Le build produit un APK installable directement sur un téléphone Android.

## Notifications push

Elles demandent une clé FCM (Firebase) enregistrée dans le projet EAS (`eas credentials`),
et le serveur démarré avec `WATTOU_EXPO_PUSH_ENABLED=true`.

## Tests

```bash
npx jest && npx tsc --noEmit          # ou : make mobile-test
WATTOU_API_URL=http://localhost:8000 make mobile-integration   # contre l'API réelle
```

## Identité visuelle

Piste B « Malin » : voir [`docs/identite-visuelle.md`](../docs/identite-visuelle.md). Les couleurs,
polices et rayons sont dans `src/theme.ts` ; l'icône et l'écran de démarrage dans `assets/`.
