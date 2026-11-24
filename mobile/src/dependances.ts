import Constants from 'expo-constants';
import { type Api, creerApi } from './api/client';
import { type StockageJeton, stockageSecurise } from './session/stockage';

/** Tout ce qui touche l'extérieur (réseau, stockage, horloge) : remplacé par des faux dans les tests. */
export type Dependances = {
  creerApi: (jeton: () => Promise<string | null>) => Api;
  stockage: StockageJeton;
  maintenant: () => Date;
};

const apiUrl = (Constants.expoConfig?.extra?.apiUrl as string | undefined) || 'http://10.0.2.2:8000';

export const dependancesReelles: Dependances = {
  creerApi: (jeton) => creerApi({ baseUrl: apiUrl, jeton }),
  stockage: stockageSecurise,
  maintenant: () => new Date(),
};
