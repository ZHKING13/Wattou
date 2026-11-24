import { fireEvent, renderRouter, screen, waitFor, within } from 'expo-router/testing-library';
import { PilotageIndisponible } from '../src/api/erreurs';
import type { Dispositif, Resume } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);

const DISPOSITIFS: Dispositif[] = [
  { id: 'meter', kind: 'meter', name: 'Compteur', essential: false, last_state: {}, schedule: { slots: [] } },
  { id: 'clim', kind: 'ir_ac', name: 'Clim salon', essential: false, last_state: { mode: 'cool', setpoint_c: 26 }, schedule: { slots: [] } },
  { id: 'prise-fer', kind: 'plug', name: 'Prise fer à repasser', essential: false, last_state: { on: true, p_w: 1000 }, schedule: { slots: [] } },
  { id: 'prise-frigo', kind: 'plug', name: 'Prise frigo', essential: true, last_state: { on: true, p_w: 120 }, schedule: { slots: [] } },
];
const resume = async (): Promise<Resume> => ({
  foyer_name: 'Chez Awa', power_w: 500, today_kwh: 5, today_fcfa: 600, price_fcfa_kwh: 120, credit_kwh: 40, credit_fcfa: 4800,
  days_left: 3, depletion_at: null, month_forecast_fcfa: 20000, absence_mode: false, low_credit_days: 2,
  data_until: '2026-11-24T14:59:59Z',
});

async function ouvrir(extra: Parameters<typeof fauxApi>[0] = {}) {
  await renderRouter(routesApp(deps(fauxApi({ dispositifs: async () => DISPOSITIFS, resume, ...extra }))),
                     { initialUrl: '/controle' });
  await screen.findByText('Clim salon');
}

test('prise essentielle : pas d\'interrupteur', async () => {
  await ouvrir();
  const frigo = screen.getByTestId('dispositif-prise-frigo');
  within(frigo).getByText('Toujours allumée (appareil essentiel)');
  expect(within(frigo).queryByRole('switch')).toBeNull();
  expect(screen.queryByTestId('dispositif-meter')).toBeNull();
});

test('éteindre la prise du fer', async () => {
  const commander = jest.fn(async () => {});
  await ouvrir({ commander });
  await fireEvent(screen.getByRole('switch', { name: 'Prise fer à repasser' }), 'valueChange', false);
  await waitFor(() => expect(commander).toHaveBeenCalledWith('prise-fer', { on: false }));
  expect(screen.getByRole('switch', { name: 'Prise fer à repasser' }).props.value).toBe(false);
});

test('pilotage indisponible : l\'interrupteur revient et le message s\'affiche', async () => {
  const commander = jest.fn(async () => { throw new PilotageIndisponible(); });
  await ouvrir({ commander });
  await fireEvent(screen.getByRole('switch', { name: 'Prise fer à repasser' }), 'valueChange', false);
  await screen.findByText('Le pilotage est momentanément indisponible. Réessayez dans un instant.');
  expect(screen.getByRole('switch', { name: 'Prise fer à repasser' }).props.value).toBe(true);
});

test('consigne de la clim : +1 °C, bornée à 30', async () => {
  const commander = jest.fn(async () => {});
  await ouvrir({ commander });
  await fireEvent.press(screen.getByRole('button', { name: 'Monter la consigne' }));
  await waitFor(() => expect(commander).toHaveBeenCalledWith('clim', { setpoint_c: 27 }));
  screen.getByText('27 °C');
  for (let i = 0; i < 5; i += 1) await fireEvent.press(screen.getByRole('button', { name: 'Monter la consigne' }));
  screen.getByText('30 °C');
  expect(commander).toHaveBeenLastCalledWith('clim', { setpoint_c: 30 });
  expect(screen.getByRole('button', { name: 'Monter la consigne' })).toBeDisabled();
});

test('éteindre la clim', async () => {
  const commander = jest.fn(async () => {});
  await ouvrir({ commander });
  await fireEvent(screen.getByRole('switch', { name: 'Clim salon' }), 'valueChange', false);
  await waitFor(() => expect(commander).toHaveBeenCalledWith('clim', { mode: 'off' }));
});

test('règle crédit bas : 3 jours', async () => {
  const regles = jest.fn(async () => {});
  await ouvrir({ regles });
  await fireEvent.press(screen.getByRole('tab', { name: '3 jours' }));
  await waitFor(() => expect(regles).toHaveBeenCalledWith(3));
});

test('programmer la clim : éteindre à 6 h en semaine', async () => {
  const programmer = jest.fn(async (_id: string, p: unknown) => p as never);
  await ouvrir({ programmer });
  await fireEvent.press(screen.getByRole('button', { name: 'Programmer Clim salon' }));
  await fireEvent.changeText(await screen.findByLabelText('Heure (ex. 0630)'), '0600');
  screen.getByText('06:00');
  for (const j of ['Sam', 'Dim']) await fireEvent.press(screen.getByRole('checkbox', { name: j }));
  await fireEvent.press(screen.getByRole('tab', { name: 'Éteindre' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Ajouter' }));
  screen.getByText('Lun–Ven 06:00 : éteindre');
  await fireEvent.press(screen.getByRole('button', { name: 'Enregistrer' }));
  await waitFor(() => expect(programmer).toHaveBeenCalledWith('clim', {
    slots: [{ at: '06:00', days: [0, 1, 2, 3, 4], action: { mode: 'off' } }],
  }));
});

test('l\'état des prises suit le serveur après rafraîchissement (coupure par la règle)', async () => {
  let liste = DISPOSITIFS;
  const { act } = require('expo-router/testing-library');
  await renderRouter(routesApp(deps(fauxApi({ dispositifs: async () => liste, resume }))), { initialUrl: '/controle' });
  await screen.findByText('Clim salon');
  expect(screen.getByRole('switch', { name: 'Prise fer à repasser' }).props.value).toBe(true);
  liste = DISPOSITIFS.map((d) => (d.id === 'prise-fer' ? { ...d, last_state: { on: false, p_w: 0 } } : d));
  const defil = screen.getByTestId('defilement-ecran-controle');
  await act(async () => { await defil.props.refreshControl.props.onRefresh(); });
  await waitFor(() => expect(screen.getByRole('switch', { name: 'Prise fer à repasser' }).props.value).toBe(false));
});
