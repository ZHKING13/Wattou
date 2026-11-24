import { date, depuis, fcfa, heure, jours, kwh } from '../src/format';

const NNBSP = ' ';

test('fcfa sans décimales, espace fine', () => {
  expect(fcfa(12500)).toBe(`12${NNBSP}500 F`);
  expect(fcfa(0)).toBe('0 F');
  expect(fcfa(1234.6)).toBe(`1${NNBSP}235 F`);
});

test('kwh à une décimale avec virgule', () => {
  expect(kwh(3.44)).toBe('3,4 kWh');
});

test('jours de crédit', () => {
  expect(jours(4.75)).toBe('4,8 jours');
  expect(jours(1)).toBe('1,0 jour');
});

test('heure à Abidjan', () => {
  expect(heure('2026-11-24T14:32:00Z')).toBe('14 h 32');
});

test('depuis', () => {
  const maintenant = new Date('2026-11-24T15:00:00Z');
  expect(depuis('2026-11-24T14:48:00Z', maintenant)).toBe('il y a 12 min');
  expect(depuis('2026-11-24T12:00:00Z', maintenant)).toBe('il y a 3 h');
  expect(depuis('2026-11-23T21:05:00Z', maintenant)).toBe('hier à 21 h 05');
  expect(depuis('2026-11-24T14:59:40Z', maintenant)).toBe("à l'instant");
});

test('date courte', () => {
  expect(date('2026-11-24T10:00:00Z')).toBe('mar. 24 nov.');
});
