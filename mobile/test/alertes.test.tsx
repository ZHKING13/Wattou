import { fireEvent, renderRouter, screen, waitFor, within } from 'expo-router/testing-library';
import type { Alerte, Resume } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);

const ALERTES: Alerte[] = [
  { id: 3, ts: '2026-11-24T14:10:00Z', kind: 'absence_load', message: 'Consommation de 400 W détectée alors que vous êtes absent.', read: false },
  { id: 2, ts: '2026-11-24T09:00:00Z', kind: 'outage', message: 'Coupure de courant de 30 min (de 08:30 à 09:00).', read: false },
  { id: 1, ts: '2026-11-23T21:00:00Z', kind: 'credit_low', message: 'Il vous reste environ 1,5 jours de crédit.', read: true },
];
const resume = async () => ({ absence_mode: false }) as Resume;

async function ouvrir(extra: Parameters<typeof fauxApi>[0] = {}) {
  await renderRouter(routesApp(deps(fauxApi({ alertes: async () => ALERTES, resume, ...extra }))),
                     { initialUrl: '/alertes' });
  await screen.findByTestId('alerte-3');
}

test('liste, styles et badge des non lues', async () => {
  await ouvrir();
  expect(screen.getByTestId('alerte-3').props.accessibilityHint).toBe('danger');
  expect(screen.getByTestId('alerte-2').props.accessibilityHint).toBe('normal');
  expect(screen.getByTestId('alerte-1').props.accessibilityHint).toBe('alerte');
  within(screen.getByTestId('alerte-3')).getByText('il y a 50 min');
  expect(screen.getByLabelText('2 alertes non lues')).toBeTruthy();
});

test('toucher une alerte non lue la marque lue', async () => {
  const lireAlerte = jest.fn(async () => {});
  await ouvrir({ lireAlerte });
  await fireEvent.press(screen.getByTestId('alerte-3'));
  await waitFor(() => expect(lireAlerte).toHaveBeenCalledWith(3));
  await screen.findByLabelText('1 alerte non lue');
});

test('activer « Je m\'absente »', async () => {
  const absence = jest.fn(async () => {});
  await ouvrir({ absence });
  await fireEvent(screen.getByRole('switch', { name: 'Je m’absente' }), 'valueChange', true);
  await waitFor(() => expect(absence).toHaveBeenCalledWith(true));
  screen.getByText('Wattou vous prévient si quelque chose consomme pendant votre absence.');
});

test('aucune alerte', async () => {
  await renderRouter(routesApp(deps(fauxApi({ alertes: async () => [], resume }))), { initialUrl: '/alertes' });
  await screen.findByText('Aucune alerte. Tout va bien.');
});

test('alertes impossibles à charger : message et Réessayer, jamais « Tout est lu »', async () => {
  const { HorsLigne } = require('../src/api/erreurs');
  await renderRouter(routesApp(deps(fauxApi({ alertes: async () => { throw new HorsLigne(); }, resume }))),
                     { initialUrl: '/alertes' });
  await screen.findByText('Pas de connexion internet.');
  screen.getByRole('button', { name: 'Réessayer' });
  expect(screen.queryByText('Tout est lu')).toBeNull();
  expect(screen.queryByText('Aucune alerte. Tout va bien.')).toBeNull();
});
