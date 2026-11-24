import { act, fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import { Text } from 'react-native';
import type { Resume } from '../src/api/types';
import { useApi } from '../src/session/SessionContext';
import { useRessource } from '../src/donnees/useRessource';
import { EtatRessource } from '../src/ui/Etat';
import { HorsLigne } from '../src/api/erreurs';
import { cacheMemoire, deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);

function Sonde() {
  const api = useApi();
  const r = useRessource<Resume>('resume', () => api.resume(), { intervalleMs: 60_000 });
  return (
    <EtatRessource ressource={r}>
      {(d) => <Text>{`Puissance ${d.power_w}`}</Text>}
    </EtatRessource>
  );
}

const routes = (d: ReturnType<typeof deps>) => ({ ...routesApp(d), '(onglets)/index': Sonde });

test('réseau coupé avec cache : données du cache et bandeau hors connexion', async () => {
  const cache = cacheMemoire();
  await cache.ecrire('f1:resume', { power_w: 450 }, '2026-11-24T14:32:00Z');
  const api = fauxApi({ resume: async () => { throw new HorsLigne(); } });
  await renderRouter(routes(deps(api, undefined, { cache })), { initialUrl: '/' });
  await screen.findByText('Puissance 450');
  await screen.findByText('Données de 14 h 32 — hors connexion');
});

test('réseau coupé sans cache : message et bouton Réessayer', async () => {
  let n = 0;
  const api = fauxApi({
    resume: async () => {
      n += 1;
      if (n === 1) throw new HorsLigne();
      return { power_w: 600 } as Resume;
    },
  });
  await renderRouter(routes(deps(api, undefined, { cache: cacheMemoire() })), { initialUrl: '/' });
  await screen.findByText('Pas de connexion internet.');
  await fireEvent.press(screen.getByRole('button', { name: 'Réessayer' }));
  await screen.findByText('Puissance 600');
});

test('succès : cache écrit pour le foyer', async () => {
  const cache = cacheMemoire();
  const api = fauxApi({ resume: async () => ({ power_w: 700 }) as Resume });
  await renderRouter(routes(deps(api, undefined, { cache })), { initialUrl: '/' });
  await screen.findByText('Puissance 700');
  expect((await cache.lire('f1:resume'))?.valeur).toEqual({ power_w: 700 });
  expect(screen.queryByText(/hors connexion/)).toBeNull();
});

test('rafraîchi toutes les 60 s quand l\'écran est affiché', async () => {
  const resume = jest.fn(async () => ({ power_w: 1 }) as Resume);
  await renderRouter(routes(deps(fauxApi({ resume }), undefined, { cache: cacheMemoire() })), { initialUrl: '/' });
  await screen.findByText('Puissance 1');
  expect(resume).toHaveBeenCalledTimes(1);
  await act(async () => { await jest.advanceTimersByTimeAsync(60_000); });
  expect(resume).toHaveBeenCalledTimes(2);
});
