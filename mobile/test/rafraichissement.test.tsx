import { act, fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import { HorsLigne } from '../src/api/erreurs';
import type { Appareil, Resume } from '../src/api/types';
import { cacheMemoire, deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);

const RESUME: Resume = {
  foyer_name: 'Chez Awa', power_w: 500, today_kwh: 5, today_fcfa: 600, price_fcfa_kwh: 120, credit_kwh: 40, credit_fcfa: 4800,
  days_left: 3, depletion_at: null, month_forecast_fcfa: 20000, absence_mode: false, low_credit_days: 2,
  data_until: '2026-11-24T14:59:59Z',
};
const jour: Appareil = { id: 'a1', label: 'Clim', power_w: 1100, kwh: 2, fcfa: 250, share: 1, estimated: true, essential: false, device_id: null };

test('hors ligne : changer de période ne montre pas les chiffres de la période précédente', async () => {
  const cache = cacheMemoire();
  await cache.ecrire('f1:appareils:day', [jour], '2026-11-24T14:00:00Z');
  const api = fauxApi({ appareils: async () => { throw new HorsLigne(); } });
  await renderRouter(routesApp(deps(api, undefined, { cache })), { initialUrl: '/appareils' });
  await screen.findByTestId('appareil-a1');
  await fireEvent.press(screen.getByRole('tab', { name: '30 jours' }));
  await screen.findByText('Pas de connexion internet.');
  expect(screen.queryByTestId('appareil-a1')).toBeNull();
});

test('réponse tardive de l\'ancienne période ignorée', async () => {
  let finirJour: (v: Appareil[]) => void = () => {};
  const appareils = jest.fn((p: string) => (p === 'day'
    ? new Promise<Appareil[]>((ok) => { finirJour = ok; })
    : Promise.resolve([{ ...jour, id: 'w1', label: 'Semaine' }])));
  await renderRouter(routesApp(deps(fauxApi({ appareils }))), { initialUrl: '/appareils' });
  await fireEvent.press(await screen.findByRole('tab', { name: '7 jours' }));
  await screen.findByTestId('appareil-w1');
  await act(async () => { finirJour([jour]); });
  expect(screen.queryByTestId('appareil-a1')).toBeNull();
  screen.getByTestId('appareil-w1');
});

test('revenir sur un onglet recharge ses données', async () => {
  const resume = jest.fn(async () => RESUME);
  await renderRouter(routesApp(deps(fauxApi({ resume, appareils: async () => [] }))), { initialUrl: '/' });
  await screen.findByText('3,0 jours');
  await fireEvent.press(screen.getByLabelText(/^Appareils, tab/));
  await screen.findByTestId('ecran-appareils');
  const avant = resume.mock.calls.length;
  await fireEvent.press(screen.getByLabelText(/^Accueil, tab/));
  await waitFor(() => expect(resume.mock.calls.length).toBeGreaterThan(avant));
});

test('tirer pour rafraîchir', async () => {
  const resume = jest.fn(async () => RESUME);
  await renderRouter(routesApp(deps(fauxApi({ resume }))), { initialUrl: '/' });
  await screen.findByText('3,0 jours');
  const avant = resume.mock.calls.length;
  const defil = screen.getByTestId('defilement-ecran-accueil');
  await act(async () => { await defil.props.refreshControl.props.onRefresh(); });
  expect(resume.mock.calls.length).toBe(avant + 1);
});
