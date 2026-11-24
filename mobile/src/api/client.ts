import { ErreurServeur, HorsLigne, NonAutorise, PilotageIndisponible, Refuse } from './erreurs';
import type {
  Alerte, Appareil, CommandeClim, CommandePrise, Dispositif, Jeton, Periode, PointHistorique,
  Programmation, Resume, SaisieCredit,
} from './types';

export interface Api {
  inscrire(phone: string, password: string, foyerName: string): Promise<Jeton>;
  connecter(phone: string, password: string): Promise<Jeton>;
  resume(): Promise<Resume>;
  appareils(periode: Periode): Promise<Appareil[]>;
  renommer(id: string, label: string): Promise<void>;
  historique(from: string, to: string, step: 'hour' | 'day'): Promise<PointHistorique[]>;
  saisirCredit(corps: SaisieCredit): Promise<void>;
  absence(enabled: boolean): Promise<void>;
  regles(jours: number): Promise<void>;
  alertes(): Promise<Alerte[]>;
  lireAlerte(id: number): Promise<void>;
  dispositifs(): Promise<Dispositif[]>;
  commander(id: string, cmd: CommandePrise | CommandeClim): Promise<void>;
  programmer(id: string, prog: Programmation): Promise<Programmation>;
  enregistrerPush(token: string): Promise<void>;
}

export interface OptionsApi {
  baseUrl: string;
  jeton: () => Promise<string | null>;
  fetch?: typeof fetch;
}

const DELAI_MS = 15_000;
type Methode = 'GET' | 'POST' | 'PUT' | 'PATCH';

export function creerApi(options: OptionsApi): Api {
  const base = `${options.baseUrl.replace(/\/+$/, '')}/api/v1`;
  const appelFetch = options.fetch ?? ((...a: Parameters<typeof fetch>) => fetch(...a));

  async function appeler<T>(methode: Methode, chemin: string, corps?: unknown,
                            query?: Record<string, string>): Promise<T> {
    const jeton = await options.jeton();
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (jeton) headers.Authorization = `Bearer ${jeton}`;
    if (corps !== undefined) headers['Content-Type'] = 'application/json';
    const qs = query ? `?${new URLSearchParams(query).toString()}` : '';
    // Le délai couvre l'appel ET la lecture du corps.
    let minuteur: ReturnType<typeof setTimeout> | undefined;
    const delai = new Promise<never>((_, rejeter) => {
      minuteur = setTimeout(() => rejeter(new HorsLigne()), DELAI_MS);
    });
    const requete = (async () => {
      let r: Response;
      try {
        r = await appelFetch(`${base}${chemin}${qs}`, {
          method: methode, headers, body: corps === undefined ? undefined : JSON.stringify(corps),
        });
      } catch {
        throw new HorsLigne();
      }
      if (r.status === 401) throw new NonAutorise();
      if (r.status === 503) throw new PilotageIndisponible();
      if (r.status >= 500) throw new ErreurServeur(r.status);
      const texte = await r.text();
      let donnees: unknown = null;
      try {
        donnees = texte ? JSON.parse(texte) : null;
      } catch {
        if (r.ok) throw new HorsLigne(); // portail captif d'un Wi-Fi
      }
      if (!r.ok) {
        const detail = (donnees as { detail?: unknown } | null)?.detail;
        throw new Refuse(r.status, typeof detail === 'string' ? detail : 'Valeur refusée par le serveur.');
      }
      return donnees as T;
    })();
    try {
      return await Promise.race([requete, delai]);
    } finally {
      clearTimeout(minuteur);
    }
  }

  const rien = async (p: Promise<unknown>) => {
    await p;
  };

  return {
    inscrire: (phone, password, foyerName) =>
      appeler('POST', '/auth/register', { phone, password, foyer_name: foyerName }),
    connecter: (phone, password) => appeler('POST', '/auth/login', { phone, password }),
    resume: () => appeler('GET', '/foyer/summary'),
    appareils: (periode) => appeler('GET', '/foyer/appliances', undefined, { period: periode }),
    renommer: (id, label) => rien(appeler('PATCH', `/appliances/${encodeURIComponent(id)}`, { label })),
    historique: (from, to, step) => appeler('GET', '/foyer/history', undefined, { from, to, step }),
    saisirCredit: (corps) => rien(appeler('POST', '/foyer/credit', corps)),
    absence: (enabled) => rien(appeler('PUT', '/foyer/absence', { enabled })),
    regles: (jours) => rien(appeler('PUT', '/foyer/rules', { low_credit_days: jours })),
    alertes: () => appeler('GET', '/alerts'),
    lireAlerte: (id) => rien(appeler('POST', `/alerts/${id}/read`)),
    dispositifs: () => appeler('GET', '/devices'),
    commander: (id, cmd) => rien(appeler('POST', `/devices/${encodeURIComponent(id)}/command`, cmd)),
    programmer: (id, prog) => appeler('PUT', `/devices/${encodeURIComponent(id)}/schedule`, prog),
    enregistrerPush: (token) => rien(appeler('POST', '/push-tokens', { token })),
  };
}
