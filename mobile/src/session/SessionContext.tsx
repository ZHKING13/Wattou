import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { Api } from '../api/client';
import { NonAutorise } from '../api/erreurs';
import type { Jeton } from '../api/types';
import type { Dependances } from '../dependances';

type Etat = 'chargement' | 'connecte' | 'deconnecte';

type Session = {
  etat: Etat;
  foyerId: string | null;
  connecter(phone: string, password: string): Promise<void>;
  inscrire(phone: string, password: string, nomFoyer: string): Promise<void>;
  deconnecter(): Promise<void>;
};

type Contexte = { deps: Dependances; api: Api; session: Session };

const Ctx = createContext<Contexte | null>(null);

function lire(): Contexte {
  const c = useContext(Ctx);
  if (!c) throw new Error('FournisseurApp manquant');
  return c;
}

export const useDeps = () => lire().deps;
export const useApi = () => lire().api;
export const useSession = () => lire().session;

/** Toute réponse 401 déconnecte : le jeton est effacé et l'app revient à la connexion. */
function envelopper(api: Api, surNonAutorise: () => void): Api {
  return new Proxy(api, {
    get(cible, nom) {
      const f = (cible as unknown as Record<string | symbol, unknown>)[nom];
      if (typeof f !== 'function') return f;
      return async (...args: unknown[]) => {
        try {
          return await (f as (...a: unknown[]) => Promise<unknown>).apply(cible, args);
        } catch (e) {
          if (e instanceof NonAutorise && nom !== 'connecter') surNonAutorise();
          throw e;
        }
      };
    },
  });
}

export function FournisseurApp({ deps, children }: { deps: Dependances; children: ReactNode }) {
  const [jeton, setJeton] = useState<Jeton | null>(null);
  const [etat, setEtat] = useState<Etat>('chargement');
  const jetonRef = useRef<string | null>(null);

  useEffect(() => {
    deps.stockage.lire().then((j) => {
      jetonRef.current = j?.token ?? null;
      setJeton(j);
      setEtat(j ? 'connecte' : 'deconnecte');
    });
  }, [deps]);

  const deconnecter = useCallback(async () => {
    jetonRef.current = null;
    setJeton(null);
    setEtat('deconnecte');
    await deps.stockage.effacer();
  }, [deps]);

  const api = useMemo(
    () => envelopper(deps.creerApi(async () => jetonRef.current), () => void deconnecter()),
    [deps, deconnecter],
  );

  const ouvrir = useCallback(async (j: Jeton) => {
    await deps.stockage.ecrire(j);
    jetonRef.current = j.token;
    setJeton(j);
    setEtat('connecte');
  }, [deps]);

  const session: Session = useMemo(() => ({
    etat,
    foyerId: jeton?.foyer_id ?? null,
    connecter: async (phone, password) => ouvrir(await api.connecter(phone, password)),
    inscrire: async (phone, password, nom) => ouvrir(await api.inscrire(phone, password, nom)),
    deconnecter,
  }), [etat, jeton, api, ouvrir, deconnecter]);

  return <Ctx.Provider value={{ deps, api, session }}>{children}</Ctx.Provider>;
}
