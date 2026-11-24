import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import { Refuse } from '../src/api/erreurs';
import type { Resume } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);
const NNBSP = ' ';

const RESUME: Resume = {
  power_w: 1150, today_kwh: 12.3, today_fcfa: 1850, price_fcfa_kwh: 125, credit_kwh: 24.96,
  credit_fcfa: 3120, days_left: 4.75, depletion_at: '2026-11-29T18:10:00Z', month_forecast_fcfa: 38000,
  absence_mode: false, low_credit_days: 2, data_until: '2026-11-24T14:59:50Z',
};

const ouvrir = (r: Partial<Resume>, extra = {}) =>
  renderRouter(routesApp(deps(fauxApi({ resume: async () => ({ ...RESUME, ...r }), ...extra }))), { initialUrl: '/' });

test('résumé complet', async () => {
  await ouvrir({});
  await screen.findByText('4,8 jours');
  screen.getByText(`≈ 3${NNBSP}120 F restants`);
  screen.getByText(`Aujourd’hui : 1${NNBSP}850 F (12,3 kWh)`);
  screen.getByText(`Ce mois-ci : ≈ 38${NNBSP}000 F prévus`);
  screen.getByText('En ce moment : 1150 W');
  expect(screen.getByTestId('carte-credit').props.accessibilityHint).toBe('normal');
});

test('sans relevé : invitation à saisir, jamais « 0 jour »', async () => {
  await ouvrir({ credit_kwh: null, credit_fcfa: null, days_left: null, depletion_at: null });
  await screen.findByText('Saisissez le crédit affiché par votre compteur pour voir combien de jours il vous reste.');
  expect(screen.queryByText(/0,0 jour/)).toBeNull();
});

test('capteur muet depuis 10 min : bandeau et dernière mesure datée', async () => {
  await ouvrir({ data_until: '2026-11-24T14:50:00Z' });
  await screen.findByText('Le capteur n’envoie plus de mesures depuis il y a 10 min. Vérifiez qu’il est branché.');
  screen.getByText('Dernière mesure : 1150 W (14 h 50)');
});

test('crédit sous le seuil : carte en alerte', async () => {
  await ouvrir({ days_left: 1.5 });
  await screen.findByText('1,5 jour');
  expect(screen.getByTestId('carte-credit').props.accessibilityHint).toBe('alerte');
});

test('saisie d\'un relevé puis retour à l\'Accueil', async () => {
  const saisirCredit = jest.fn(async () => {});
  await ouvrir({}, { saisirCredit });
  await fireEvent.press(await screen.findByRole('button', { name: 'Saisir le crédit du compteur' }));
  await fireEvent.changeText(await screen.findByLabelText('kWh affichés par le compteur'), '60');
  await fireEvent.press(screen.getByRole('button', { name: 'Enregistrer' }));
  await waitFor(() => expect(saisirCredit).toHaveBeenCalledWith({ kind: 'reading', kwh: 60 }));
  await screen.findByText('4,8 jours');
});

test('recharge : montant obligatoire, virgule acceptée', async () => {
  const saisirCredit = jest.fn(async () => {});
  await ouvrir({}, { saisirCredit });
  await fireEvent.press(await screen.findByRole('button', { name: 'Saisir le crédit du compteur' }));
  await fireEvent.press(await screen.findByRole('tab', { name: 'Recharge' }));
  await fireEvent.changeText(screen.getByLabelText('kWh obtenus'), '80,5');
  expect(screen.getByRole('button', { name: 'Enregistrer' })).toBeDisabled();
  await fireEvent.changeText(screen.getByLabelText('Montant payé (FCFA)'), '10 000');
  await fireEvent.press(screen.getByRole('button', { name: 'Enregistrer' }));
  await waitFor(() => expect(saisirCredit).toHaveBeenCalledWith({ kind: 'recharge', kwh: 80.5, amount_fcfa: 10000 }));
});

test('relevé refusé (422) : message du serveur sous le champ', async () => {
  const saisirCredit = jest.fn(async () => { throw new Refuse(422, 'Ce relevé est plus élevé que le précédent sans recharge entre les deux.'); });
  await ouvrir({}, { saisirCredit });
  await fireEvent.press(await screen.findByRole('button', { name: 'Saisir le crédit du compteur' }));
  await fireEvent.changeText(await screen.findByLabelText('kWh affichés par le compteur'), '90');
  await fireEvent.press(screen.getByRole('button', { name: 'Enregistrer' }));
  await screen.findByText('Ce relevé est plus élevé que le précédent sans recharge entre les deux.');
});
