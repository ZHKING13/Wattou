import { conseilDuJour, comparerAHier } from '../src/conseils';
import type { Appareil } from '../src/api/types';

const NNBSP = ' ';
const a = (id: string, label: string | null, fcfa: number, share: number): Appareil =>
  ({ id, label, power_w: 100, kwh: 1, fcfa, share, estimated: true, essential: false, device_id: null });

test('clim nommée : conseil chiffré sur la consigne', () => {
  // 7 000 F/semaine de clim -> ≈ 30 000 F/mois ; 2 °C de plus ≈ 12 % -> ≈ 3 600 F
  expect(conseilDuJour([a('fond', 'Consommation de fond', 900, 0.1), a('c', 'Clim', 7000, 0.6)]))
    .toBe(`Réglez la clim 2 °C plus haut : vous gardez ≈ 3${NNBSP}600 F ce mois-ci.`);
});

test('sans clim, consommation de fond importante', () => {
  expect(conseilDuJour([a('fond', 'Consommation de fond', 2100, 0.3), a('f', 'Frigo', 900, 0.2)]))
    .toBe(`Les appareils en veille coûtent ≈ 9${NNBSP}000 F par mois : éteignez la box et la télé la nuit.`);
});

test('sinon : le plus gros appareil', () => {
  expect(conseilDuJour([a('f', 'Congélateur', 1500, 0.4), a('fond', 'Consommation de fond', 200, 0.05)]))
    .toBe('Le congélateur représente 40 % de vos dépenses cette semaine. Évitez de l’ouvrir trop souvent.');
});

test('pas assez de données : pas de conseil', () => {
  expect(conseilDuJour([])).toBeNull();
});

test('comparaison avec hier à la même heure', () => {
  const pts = [
    { ts: '2026-11-23T08:00:00Z', kwh: 2 }, { ts: '2026-11-23T09:00:00Z', kwh: 3 }, { ts: '2026-11-23T20:00:00Z', kwh: 9 },
    { ts: '2026-11-24T08:00:00Z', kwh: 2.2 }, { ts: '2026-11-24T09:00:00Z', kwh: 2.4 },
  ];
  // hier jusqu'à 10 h : 5 kWh ; aujourd'hui : 4,6 kWh -> −8 %
  expect(comparerAHier(pts, new Date('2026-11-24T10:00:00Z'))).toEqual({ ecart: -8, texte: '−8 % vs hier' });
  expect(comparerAHier([{ ts: '2026-11-24T08:00:00Z', kwh: 2 }], new Date('2026-11-24T10:00:00Z'))).toBeNull();
});
