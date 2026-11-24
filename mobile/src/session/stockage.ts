import * as SecureStore from 'expo-secure-store';
import type { Jeton } from '../api/types';

export interface StockageJeton {
  lire(): Promise<Jeton | null>;
  ecrire(j: Jeton): Promise<void>;
  effacer(): Promise<void>;
}

const CLE = 'wattou.session';

export const stockageSecurise: StockageJeton = {
  async lire() {
    const v = await SecureStore.getItemAsync(CLE);
    if (!v) return null;
    try {
      return JSON.parse(v) as Jeton;
    } catch {
      return null;
    }
  },
  ecrire: (j) => SecureStore.setItemAsync(CLE, JSON.stringify(j)),
  effacer: () => SecureStore.deleteItemAsync(CLE),
};
