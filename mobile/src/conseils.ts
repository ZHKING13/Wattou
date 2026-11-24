import type { Appareil, PointHistorique } from './api/types';
import { fcfa } from './format';

const SEMAINES_PAR_MOIS = 30 / 7;
/** Chaque degré de plus sur la clim ≈ 6 % de sa consommation ; on conseille 2 °C. */
const GAIN_CLIM_2_DEGRES = 0.12;

function arrondiCent(n: number): number {
  return Math.round(n / 100) * 100;
}

/** Conseil chiffré à partir de la répartition de la semaine (appareils nommés). */
export function conseilDuJour(semaine: Appareil[]): string | null {
  const clim = semaine.find((a) => a.label && /clim/i.test(a.label) && a.fcfa > 0);
  if (clim) {
    const gain = arrondiCent(clim.fcfa * SEMAINES_PAR_MOIS * GAIN_CLIM_2_DEGRES);
    return `Réglez la clim 2 °C plus haut : vous gardez ≈ ${fcfa(gain)} ce mois-ci.`;
  }
  const fond = semaine.find((a) => a.id === 'fond');
  if (fond && fond.share >= 0.2) {
    return `Les appareils en veille coûtent ≈ ${fcfa(arrondiCent(fond.fcfa * SEMAINES_PAR_MOIS))} par mois : éteignez la box et la télé la nuit.`;
  }
  const plusGros = semaine.filter((a) => a.label && a.id !== 'fond' && a.id !== 'autres')
    .sort((x, y) => y.fcfa - x.fcfa)[0];
  if (plusGros?.label) {
    return `Le ${plusGros.label.toLowerCase()} représente ${Math.round(plusGros.share * 100)} % de vos dépenses cette semaine. Évitez de l’ouvrir trop souvent.`;
  }
  return null;
}

/** Aujourd'hui comparé à hier jusqu'à la même heure (points horaires couvrant hier et aujourd'hui). */
export function comparerAHier(points: PointHistorique[], maintenant: Date): { ecart: number; texte: string } | null {
  const minuit = Date.UTC(maintenant.getUTCFullYear(), maintenant.getUTCMonth(), maintenant.getUTCDate());
  const depuisMinuit = maintenant.getTime() - minuit;
  let hier = 0;
  let aujourdhui = 0;
  for (const p of points) {
    const t = new Date(p.ts).getTime();
    if (t >= minuit) aujourdhui += p.kwh;
    else if (t >= minuit - 86_400_000 && t < minuit - 86_400_000 + depuisMinuit) hier += p.kwh;
  }
  if (hier <= 0) return null;
  const ecart = Math.round(((aujourdhui - hier) / hier) * 100);
  const signe = ecart > 0 ? '+' : ecart < 0 ? '−' : '';
  return { ecart, texte: `${signe}${Math.abs(ecart)} % vs hier` };
}
