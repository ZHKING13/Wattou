import { completer, fenetre, graduations } from '../src/graphique/echelle';

const MAINTENANT = new Date('2026-11-24T15:20:00Z');

test('fenêtre du jour : depuis minuit, par heure', () => {
  expect(fenetre('jour', MAINTENANT)).toEqual({
    from: '2026-11-24T00:00:00.000Z', to: '2026-11-24T15:20:00.000Z', step: 'hour',
  });
});

test('fenêtres semaine et mois : par jour, 7 et 30 jours calendaires', () => {
  expect(fenetre('semaine', MAINTENANT).from).toBe('2026-11-18T00:00:00.000Z');
  expect(fenetre('semaine', MAINTENANT).step).toBe('day');
  expect(fenetre('mois', MAINTENANT).from).toBe('2026-10-26T00:00:00.000Z');
});

test('compléter les heures sans mesure à 0', () => {
  const f = fenetre('jour', MAINTENANT);
  const pts = completer([
    { ts: '2026-11-24T02:00:00+00:00', kwh: 1 },
    { ts: '2026-11-24T08:00:00+00:00', kwh: 2 },
    { ts: '2026-11-24T15:00:00+00:00', kwh: 0.5 },
  ], f);
  expect(pts).toHaveLength(16);
  expect(pts.filter((p) => p.kwh === 0)).toHaveLength(13);
  expect(pts[8]).toEqual({ ts: '2026-11-24T08:00:00.000Z', kwh: 2 });
});

test('graduations rondes', () => {
  expect(graduations(3.7)).toEqual([0, 1, 2, 3, 4]);
  expect(graduations(0)).toEqual([0, 1]);
  expect(graduations(17)).toEqual([0, 5, 10, 15, 20]);
  expect(graduations(0.34)).toEqual([0, 0.1, 0.2, 0.3, 0.4]);
});
