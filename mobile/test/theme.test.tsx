import { couleursPour, polices } from '../src/theme';

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const contraste = (a: string, b: string) => {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};

test.each(['light', 'dark'] as const)('piste B lisible en mode %s (≥ 4,5:1)', (mode) => {
  const c = couleursPour(mode);
  expect(contraste(c.texte, c.fond)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.texte, c.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.texteDoux, c.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.surAccent, c.accent)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.accentTexte, c.fond)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.accentTexte, c.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.alerte, c.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.danger, c.surface)).toBeGreaterThanOrEqual(4.5);
  // carte « nuit » de la maquette B : texte crème et chiffre corail sur bleu nuit
  expect(contraste(c.surFort, c.fort)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.surFortDoux, c.fort)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.accentSurFort, c.fort)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.dangerSurFort, c.fort)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.surSuccesFond, c.succesFond)).toBeGreaterThanOrEqual(4.5);
  expect(contraste(c.surAlerteFond, c.alerteFond)).toBeGreaterThanOrEqual(4.5);
});

test.each(['light', 'dark'] as const)('texte blanc sur le corail, lisible (%s)', (mode) => {
  const c = couleursPour(mode);
  expect(c.surAccent).toBe('#FFFFFF');
  expect(contraste(c.surAccent, c.accent)).toBeGreaterThanOrEqual(4.5);
  // pastille corail clair sur la carte nuit : texte bleu nuit
  expect(contraste(c.fort, c.accentSurFort)).toBeGreaterThanOrEqual(4.5);
});

test('couleurs de la piste B', () => {
  const c = couleursPour('light');
  expect([c.accentVif, c.texte, c.fond]).toEqual(['#FF6B35', '#1B2A41', '#FFF8F0']);
  expect(polices.titre).toBe('Baloo2_800ExtraBold');
  expect(polices.texte).toBe('NunitoSans_400Regular');
});
