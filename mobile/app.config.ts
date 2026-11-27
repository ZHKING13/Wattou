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

// Projet EAS créé par `eas init` (compte zetreyy).
const ID_PROJET_EAS = '1a5a5762-3089-440a-a693-5aa14e441288';

const config: ExpoConfig = {
  name: 'Wattou',
  slug: 'wattou',
  owner: 'zetreyy',
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
  extra: { apiUrl, eas: { projectId: ID_PROJET_EAS } },
};

export default config;
