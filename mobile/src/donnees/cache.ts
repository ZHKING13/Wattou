import Storage from 'expo-sqlite/kv-store';

/** Dernières données connues, pour afficher quelque chose sans réseau. */
export interface Cache {
  lire<T>(cle: string): Promise<{ valeur: T; le: string } | null>;
  ecrire(cle: string, valeur: unknown, le?: string): Promise<void>;
  vider(): Promise<void>;
}

const PREFIXE = 'wattou.cache.';

export const cacheLocal: Cache = {
  async lire<T>(cle: string) {
    const v = await Storage.getItem(PREFIXE + cle);
    if (!v) return null;
    try {
      return JSON.parse(v) as { valeur: T; le: string };
    } catch {
      return null;
    }
  },
  async ecrire(cle, valeur, le = new Date().toISOString()) {
    await Storage.setItem(PREFIXE + cle, JSON.stringify({ valeur, le }));
  },
  async vider() {
    const cles = await Storage.getAllKeys();
    await Promise.all(cles.filter((c) => c.startsWith(PREFIXE)).map((c) => Storage.removeItem(c)));
  },
};
