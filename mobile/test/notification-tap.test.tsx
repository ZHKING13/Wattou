import { act, renderRouter, screen } from 'expo-router/testing-library';
import type { Resume } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);

test('connecté : jeton push enregistré ; toucher une notification ouvre les alertes', async () => {
  let ouvrir: (() => void) | null = null;
  const push = {
    demanderEtEnregistrer: jest.fn(async () => 'ok' as const),
    ecouterOuvertures: (f: () => void) => { ouvrir = f; return () => {}; },
  };
  const api = fauxApi({ alertes: async () => [], resume: async () => ({ absence_mode: false }) as Resume });
  await renderRouter(routesApp(deps(api, undefined, { push })), { initialUrl: '/historique' });
  await screen.findByTestId('ecran-historique');
  expect(push.demanderEtEnregistrer).toHaveBeenCalledTimes(1);
  await act(async () => { ouvrir?.(); });
  await screen.findByTestId('ecran-alertes');
});
