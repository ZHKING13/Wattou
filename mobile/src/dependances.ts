import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { type Api, creerApi } from './api/client';
import { type Cache, cacheLocal } from './donnees/cache';
import { creerPush, type Push } from './notifications/push';
import { type StockageJeton, stockageSecurise } from './session/stockage';

/** Tout ce qui touche l'extérieur (réseau, stockage, horloge) : remplacé par des faux dans les tests. */
export type Dependances = {
  creerApi: (jeton: () => Promise<string | null>) => Api;
  stockage: StockageJeton;
  cache: Cache;
  push: Push;
  maintenant: () => Date;
};

const apiUrl = (Constants.expoConfig?.extra?.apiUrl as string | undefined) || 'http://10.0.2.2:8000';

export const dependancesReelles: Dependances = {
  creerApi: (jeton) => creerApi({ baseUrl: apiUrl, jeton }),
  stockage: stockageSecurise,
  cache: cacheLocal,
  push: creerPush({
    notifications: Notifications,
    estAppareil: Device.isDevice,
    projectId: (Constants.expoConfig?.extra?.eas?.projectId as string | undefined) ?? '',
    plateforme: Platform.OS,
    importanceHaute: Notifications.AndroidImportance.HIGH,
  }),
  maintenant: () => new Date(),
};
