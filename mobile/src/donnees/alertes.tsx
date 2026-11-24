import { createContext, type ReactNode, useContext, useMemo, useState } from 'react';
import type { Alerte } from '../api/types';
import { useApi } from '../session/SessionContext';
import { type Ressource, useRessource } from './useRessource';

type Ctx = { ressource: Ressource<Alerte[]>; alertes: Alerte[]; nonLues: number; marquerLue(id: number): Promise<void> };

const C = createContext<Ctx | null>(null);

/** Partage les alertes entre l'onglet (badge) et l'écran Alertes. */
export function FournisseurAlertes({ children }: { children: ReactNode }) {
  const api = useApi();
  const ressource = useRessource<Alerte[]>('alertes', () => api.alertes());
  const [lues, setLues] = useState<Set<number>>(new Set());
  const valeur = useMemo<Ctx>(() => {
    const alertes = (ressource.donnees ?? []).map((a) => (lues.has(a.id) ? { ...a, read: true } : a));
    return {
      ressource,
      alertes,
      nonLues: alertes.filter((a) => !a.read).length,
      async marquerLue(id) {
        setLues((s) => new Set(s).add(id));
        try {
          await api.lireAlerte(id);
        } catch {
          setLues((s) => {
            const n = new Set(s);
            n.delete(id);
            return n;
          });
        }
      },
    };
  }, [ressource, lues, api]);
  return <C.Provider value={valeur}>{children}</C.Provider>;
}

export function useAlertes(): Ctx {
  const c = useContext(C);
  if (!c) throw new Error('FournisseurAlertes manquant');
  return c;
}
