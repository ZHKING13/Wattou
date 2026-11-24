import { fireEvent, renderRouter, screen, waitFor, within } from 'expo-router/testing-library';
import type { Appareil } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);
const NNBSP = ' ';

const LISTE: Appareil[] = [
  { id: 'fond', label: 'Consommation de fond', power_w: null, kwh: 0.6, fcfa: 75, share: 0.05, estimated: true, essential: false, device_id: null },
  { id: 'a1', label: 'Clim', power_w: 1100, kwh: 9.9, fcfa: 1238, share: 0.62, estimated: true, essential: false, device_id: null },
  { id: 'a2', label: null, power_w: 150, kwh: 1.8, fcfa: 225, share: 0.11, estimated: true, essential: false, device_id: null },
  { id: 'autres', label: 'Autres', power_w: null, kwh: 1.2, fcfa: 150, share: 0.08, estimated: true, essential: false, device_id: null },
  { id: 'p1', label: 'prise-frigo', power_w: 120, kwh: 1.1, fcfa: 138, share: 0.07, estimated: true, essential: true, device_id: 'prise-frigo' },
];

async function ouvrir(api: Parameters<typeof fauxApi>[0]) {
  await renderRouter(routesApp(deps(fauxApi(api))), { initialUrl: '/appareils' });
}

test('triés par FCFA, « Estimation » sauf fond et autres', async () => {
  await ouvrir({ appareils: async () => LISTE });
  const lignes = await screen.findAllByTestId(/^appareil-/);
  expect(lignes.map((l) => l.props.testID)).toEqual(['appareil-a1', 'appareil-a2', 'appareil-autres', 'appareil-p1', 'appareil-fond']);
  within(screen.getByTestId('appareil-a1')).getByText('Estimation');
  within(screen.getByTestId('appareil-a1')).getByText(`1${NNBSP}238 F · 62 %`);
  expect(within(screen.getByTestId('appareil-fond')).queryByText('Estimation')).toBeNull();
  expect(within(screen.getByTestId('appareil-autres')).queryByText('Estimation')).toBeNull();
  within(screen.getByTestId('appareil-fond')).getByText('Consommation de fond (veilles, box)');
  within(screen.getByTestId('appareil-autres')).getByText('Autres petits appareils');
  within(screen.getByTestId('appareil-p1')).getByText('Frigo (prise connectée)');
});

test('appareil inconnu : nommer avec une suggestion', async () => {
  const renommer = jest.fn(async () => {});
  let liste = LISTE;
  const appareils = jest.fn(async () => liste);
  await ouvrir({ appareils, renommer });
  const ligne = await screen.findByTestId('appareil-a2');
  within(ligne).getByText('Appareil inconnu (≈ 150 W)');
  await fireEvent.press(within(ligne).getByRole('button', { name: 'Nommer' }));
  liste = LISTE.map((a) => (a.id === 'a2' ? { ...a, label: 'Congélateur' } : a));
  await fireEvent.press(screen.getByRole('button', { name: 'Congélateur' }));
  await waitFor(() => expect(renommer).toHaveBeenCalledWith('a2', 'Congélateur'));
  await within(await screen.findByTestId('appareil-a2')).findByText('Congélateur');
});

test('nom libre', async () => {
  const renommer = jest.fn(async () => {});
  await ouvrir({ appareils: async () => LISTE, renommer });
  await fireEvent.press(within(await screen.findByTestId('appareil-a2')).getByRole('button', { name: 'Nommer' }));
  await fireEvent.changeText(screen.getByLabelText('Autre nom'), '  Pompe à eau ');
  await fireEvent.press(screen.getByRole('button', { name: 'Valider le nom' }));
  await waitFor(() => expect(renommer).toHaveBeenCalledWith('a2', 'Pompe à eau'));
});

test('changement de période', async () => {
  const appareils = jest.fn(async () => LISTE);
  await ouvrir({ appareils });
  await screen.findByTestId('appareil-a1');
  await fireEvent.press(screen.getByRole('tab', { name: '7 jours' }));
  await waitFor(() => expect(appareils).toHaveBeenLastCalledWith('week'));
});

test('liste vide : message d\'apprentissage', async () => {
  await ouvrir({ appareils: async () => [] });
  await screen.findByText('Wattou apprend à reconnaître vos appareils. Revenez demain.');
});
