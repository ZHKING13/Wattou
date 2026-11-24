import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import { Refuse } from '../src/api/erreurs';
import type { Resume } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);
const NNBSP = ' ';

const RESUME: Resume = {
  foyer_name: 'Chez Awa',
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
  screen.getByText(`1${NNBSP}850 F`);
  screen.getByText(`12,3 kWh · ce mois-ci ≈ 38${NNBSP}000 F prévus`);
  screen.getByText('En ce moment : 1150 W');
  expect(screen.getByTestId('carte-credit').props.accessibilityHint).toBe('fort');
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

test('crédit sous le seuil : pastille crédit bas', async () => {
  await ouvrir({ days_left: 1.5 });
  await screen.findByText('1,5 jour');
  screen.getByText('Crédit bas : pensez à recharger');
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

test('hors connexion avec un résumé en cache : pas de fausse alerte capteur', async () => {
  const { HorsLigne } = require('../src/api/erreurs');
  const { cacheMemoire } = require('./fakes');
  const cache = cacheMemoire();
  await cache.ecrire('f1:resume', { ...RESUME, data_until: '2026-11-24T13:59:50Z' }, '2026-11-24T14:00:00Z');
  await renderRouter(routesApp(deps(fauxApi({ resume: async () => { throw new HorsLigne(); } }), undefined, { cache })),
                     { initialUrl: '/' });
  await screen.findByText('Données de 14 h 00 — hors connexion');
  expect(screen.queryByText(/Le capteur n’envoie plus/)).toBeNull();
});

test('crédit saisi mais jours pas encore calculés : pas de nouvelle demande de saisie', async () => {
  await ouvrir({ days_left: null, depletion_at: null });
  await screen.findByText(`≈ 3${NNBSP}120 F restants`);
  screen.getByText('Wattou calcule combien de jours il vous reste : il lui faut encore quelques heures de mesures.');
  expect(screen.queryByText(/Saisissez le crédit/)).toBeNull();
});


test('maquette B : salutation, carte nuit, conseil, comparaison et appareils', async () => {
  const appareils = async () => [
    { id: 'c', label: 'Clim', power_w: 1100, kwh: 56, fcfa: 7000, share: 0.6, estimated: true, essential: false, device_id: null },
    { id: 'g', label: 'Congélateur', power_w: 150, kwh: 12, fcfa: 1500, share: 0.12, estimated: true, essential: false, device_id: null },
    { id: 'fond', label: 'Consommation de fond', power_w: null, kwh: 8, fcfa: 900, share: 0.08, estimated: true, essential: false, device_id: null },
  ];
  const historique = async () => [
    { ts: '2026-11-23T10:00:00Z', kwh: 5 }, { ts: '2026-11-24T10:00:00Z', kwh: 4.6 },
  ];
  await ouvrir({}, { appareils, historique });
  await screen.findByText('Chez Awa');
  screen.getByText('Bonjour');
  expect(screen.getByTestId('carte-credit').props.accessibilityHint).toBe('fort');
  await screen.findByText(`Réglez la clim 2 °C plus haut : vous gardez ≈ 3${NNBSP}600 F ce mois-ci.`);
  await screen.findByText('−8 % vs hier');
  screen.getByText('Qui mange votre crédit ?');
  screen.getByText('Clim');
  screen.getByText('60 %');
});
