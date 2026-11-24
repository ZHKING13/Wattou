import type { CommandeClim, CommandePrise, Creneau } from '../api/types';

export const JOURS_COURTS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const JOURS_LONGS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];

export function trier(c: Creneau[]): Creneau[] {
  return [...c].sort((a, b) => a.at.localeCompare(b.at));
}

export function valider(c: Creneau[]): string | null {
  const vus = new Set<string>();
  for (const s of trier(c)) {
    if (s.days.length === 0) return 'Choisissez au moins un jour.';
    for (const j of s.days) {
      const cle = `${j}-${s.at}`;
      if (vus.has(cle)) return `Deux actions sont programmées le ${JOURS_LONGS[j]} à ${s.at}.`;
      vus.add(cle);
    }
  }
  return null;
}

function jours(days: number[]): string {
  const d = [...days].sort((a, b) => a - b);
  if (d.length === 7) return 'Tous les jours';
  if (d.join() === '0,1,2,3,4') return 'Lun–Ven';
  return d.map((j) => JOURS_COURTS[j]).join(', ');
}

function action(a: CommandePrise | CommandeClim): string {
  if ('on' in a) return a.on ? 'allumer' : 'éteindre';
  if (a.mode === 'off') return 'éteindre';
  return a.setpoint_c ? `allumer à ${a.setpoint_c} °C` : 'allumer';
}

export function resumer(c: Creneau): string {
  return `${jours(c.days)} ${c.at} : ${action(c.action)}`;
}
