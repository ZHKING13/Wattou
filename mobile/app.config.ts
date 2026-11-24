import type { ExpoConfig } from 'expo/config';

// Lu dans Node au moment de `expo config` / du build (pas dans l'application).
const env = process.env;
const apiUrl = env.EXPO_PUBLIC_API_URL ?? '';
const horsDev = Boolean(env.EAS_BUILD_PROFILE) || env.NODE_ENV === 'production';
if (!apiUrl && horsDev) {
  throw new Error(
    'EXPO_PUBLIC_API_URL est vide : indiquez l’URL du serveur Wattou (eas.json, champ env du profil) avant ce build.',
  );
}

const config: ExpoConfig = {
  name: 'Wattou',
  slug: 'wattou',
  version: '0.1.0',
  scheme: 'wattou',
  orientation: 'portrait',
  userInterfaceStyle: 'automatic',
  android: { package: 'ci.wattou.app' },
  plugins: ['expo-router', 'expo-secure-store', 'expo-sqlite', 'expo-notifications'],
  // projectId EAS : à renseigner après `eas init` (nécessaire aux notifications push).
  extra: { apiUrl, eas: { projectId: env.EAS_PROJECT_ID ?? '' } },
};

export default config;
