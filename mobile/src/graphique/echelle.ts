import type { PointHistorique } from '../api/types';

export type Vue = 'jour' | 'semaine' | 'mois';
export type Fenetre = { from: string; to: string; step: 'hour' | 'day' };

const H = 3_600_000;
const J = 24 * H;

function minuit(t: Date): number {
  // Abidjan = UTC : minuit local = minuit UTC
  return Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate());
}

export function fenetre(vue: Vue, maintenant: Date): Fenetre {
  const m = minuit(maintenant);
  const debut = vue === 'jour' ? m : m - (vue === 'semaine' ? 6 : 29) * J;
  return { from: new Date(debut).toISOString(), to: maintenant.toISOString(), step: vue === 'jour' ? 'hour' : 'day' };
}

/** Un point par heure (ou jour) de la fenêtre ; un trou de mesure reste visible à 0. */
export function completer(points: PointHistorique[], f: Fenetre): PointHistorique[] {
  const pas = f.step === 'hour' ? H : J;
  const parTs = new Map(points.map((p) => [new Date(p.ts).getTime(), p.kwh]));
  const out: PointHistorique[] = [];
  for (let t = new Date(f.from).getTime(); t <= new Date(f.to).getTime(); t += pas) {
    out.push({ ts: new Date(t).toISOString(), kwh: parTs.get(t) ?? 0 });
  }
  return out;
}

/** 3 à 5 graduations « rondes » de 0 jusqu'à au moins `max`. */
export function graduations(max: number): number[] {
  if (max <= 0) return [0, 1];
  const puissance = 10 ** Math.floor(Math.log10(max));
  const pas = [0.1, 0.2, 0.5, 1, 2, 5, 10].map((x) => x * puissance).find((p) => Math.ceil(max / p - 1e-9) <= 4)!;
  const n = Math.ceil(max / pas - 1e-9);
  return Array.from({ length: n + 1 }, (_, i) => Math.round(i * pas * 1e6) / 1e6);
}
