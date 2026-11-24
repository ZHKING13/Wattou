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
  icon: './assets/icon.png',
  android: {
    package: 'ci.wattou.app',
    adaptiveIcon: { foregroundImage: './assets/adaptive-icon.png', backgroundColor: '#FF6B35' },
  },
  plugins: [
    'expo-router', 'expo-secure-store', 'expo-sqlite', 'expo-font',
    ['expo-notifications', { color: '#FF6B35' }],
    ['expo-splash-screen', {
      image: './assets/splash-icon.png', imageWidth: 160, backgroundColor: '#FFF8F0',
      dark: { image: './assets/splash-icon.png', backgroundColor: '#1B2A41' },
    }],
  ],
  // projectId EAS : à renseigner après `eas init` (nécessaire aux notifications push).
  extra: { apiUrl, eas: { projectId: env.EAS_PROJECT_ID ?? '' } },
};

export default config;
