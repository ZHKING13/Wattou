import type { Api } from '../src/api/client';
import { HorsLigne } from '../src/api/erreurs';
import type { Dependances } from '../src/dependances';
import type { StockageJeton } from '../src/session/stockage';

/** Faux Api : chaque méthode non fournie échoue « hors ligne ». */
export function fauxApi(methodes: Partial<Api> = {}): Api {
  return new Proxy(methodes as Api, {
    get: (cible, nom: string) =>
      (cible as unknown as Record<string, unknown>)[nom] ?? (async () => { throw new HorsLigne(); }),
  });
}

export function stockageMemoire(initial: { token: string; foyer_id: string } | null = null): StockageJeton & {
  valeur: { token: string; foyer_id: string } | null;
} {
  const s = {
    valeur: initial,
    lire: async () => s.valeur,
    ecrire: async (j: { token: string; foyer_id: string }) => { s.valeur = j; },
    effacer: async () => { s.valeur = null; },
  };
  return s;
}

export const MAINTENANT = new Date('2026-11-24T15:00:00Z');

export function deps(api: Api, stockage = stockageMemoire({ token: 'j', foyer_id: 'f1' }),
                     extra: Partial<Dependances> = {}): Dependances {
  return { creerApi: () => api, stockage, cache: cacheMemoire(), maintenant: () => MAINTENANT, ...extra } as Dependances;
}

export function cacheMemoire() {
  const m = new Map<string, { valeur: unknown; le: string }>();
  return {
    m,
    lire: async <T,>(cle: string) => (m.get(cle) as { valeur: T; le: string } | undefined) ?? null,
    ecrire: async (cle: string, valeur: unknown, le = MAINTENANT.toISOString()) => { m.set(cle, { valeur, le }); },
    vider: async () => { m.clear(); },
  };
}
