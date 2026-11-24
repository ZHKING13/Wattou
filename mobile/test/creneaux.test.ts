import { resumer, trier, valider } from '../src/programmation/creneaux';

test('trier par heure', () => {
  const t = trier([
    { at: '19:00', days: [0], action: { on: true } },
    { at: '06:00', days: [0], action: { on: false } },
  ]);
  expect(t.map((c) => c.at)).toEqual(['06:00', '19:00']);
});

test('doublon même jour et même heure', () => {
  expect(valider([
    { at: '06:00', days: [0, 1], action: { mode: 'off' } },
    { at: '06:00', days: [0], action: { mode: 'cool', setpoint_c: 26 } },
  ])).toBe('Deux actions sont programmées le lundi à 06:00.');
});

test('aucun jour', () => {
  expect(valider([{ at: '06:00', days: [], action: { on: false } }])).toBe('Choisissez au moins un jour.');
  expect(valider([{ at: '06:00', days: [2], action: { on: false } }])).toBeNull();
});

test('résumés lisibles', () => {
  expect(resumer({ at: '06:00', days: [0, 1, 2, 3, 4], action: { mode: 'off' } })).toBe('Lun–Ven 06:00 : éteindre');
  expect(resumer({ at: '19:00', days: [0, 1, 2, 3, 4, 5, 6], action: { mode: 'cool', setpoint_c: 26 } }))
    .toBe('Tous les jours 19:00 : allumer à 26 °C');
  expect(resumer({ at: '07:30', days: [5, 6], action: { on: true } })).toBe('Sam, Dim 07:30 : allumer');
});
