// Formatage des chiffres et des dates pour un ménage ivoirien (fr, Africa/Abidjan = UTC).
const TZ = 'Africa/Abidjan';
const NNBSP = ' ';

function groupe(n: number): string {
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, NNBSP);
}

function virgule(n: number, decimales = 1): string {
  return n.toFixed(decimales).replace('.', ',');
}

export function fcfa(n: number): string {
  return `${groupe(n)} F`;
}

export function kwh(n: number): string {
  return `${virgule(n)} kWh`;
}

export function jours(n: number): string {
  return `${virgule(n)} ${n >= 1.95 ? 'jours' : 'jour'}`;
}

function parties(iso: string) {
  const d = new Date(iso);
  const p = new Intl.DateTimeFormat('fr-FR', {
    timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(d);
  const v = (t: string) => p.find((x) => x.type === t)?.value ?? '';
  return { jour: `${v('year')}-${v('month')}-${v('day')}`, h: v('hour'), m: v('minute') };
}

export function heure(iso: string): string {
  const { h, m } = parties(iso);
  return `${h} h ${m}`;
}

export function depuis(iso: string, maintenant: Date): string {
  const secondes = (maintenant.getTime() - new Date(iso).getTime()) / 1000;
  if (secondes < 60) return "à l'instant";
  if (secondes < 3600) return `il y a ${Math.floor(secondes / 60)} min`;
  const veille = parties(new Date(maintenant.getTime() - 86_400_000).toISOString()).jour;
  if (secondes < 6 * 3600 || parties(iso).jour !== veille) {
    if (secondes < 86_400) return `il y a ${Math.floor(secondes / 3600)} h`;
    return `le ${date(iso)} à ${heure(iso)}`;
  }
  return `hier à ${heure(iso)}`;
}

export function date(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    timeZone: TZ, weekday: 'short', day: 'numeric', month: 'short',
  }).format(new Date(iso));
}

/** « 80,5 » -> 80.5 ; « 10 000 » -> 10000 ; null si vide ou invalide. */
export function nombre(saisie: string): number | null {
  const propre = saisie.replace(/[\s  ]/g, '').replace(',', '.');
  if (!/^\d+(\.\d+)?$/.test(propre)) return null;
  return Number(propre);
}
