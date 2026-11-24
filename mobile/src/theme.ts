// Identité visuelle Wattou — piste B « Malin » (docs/identite-visuelle.md).
// Corail chaleureux pour l'action, bleu nuit sérieux pour les chiffres, fond crème.
// Les écrans n'utilisent que ces jetons.
import { useColorScheme } from 'react-native';

export type Couleurs = {
  fond: string; surface: string; texte: string; texteDoux: string; bordure: string;
  /** Corail des surfaces qui portent du texte blanc (boutons, conseil, onglets actifs). */
  accent: string;
  /** Texte posé sur `accent` : blanc. */
  surAccent: string;
  /** Corail vif de la marque, sans texte dessus : barres, graphiques, ampoule. */
  accentVif: string;
  /** Accent utilisé comme couleur de texte (liens, boutons secondaires) : lisible sur fond et surface. */
  accentTexte: string;
  alerte: string; danger: string; succes: string;
  /** Carte « nuit » (maquette B) : fond bleu nuit, texte crème, chiffre corail. */
  fort: string; surFort: string; surFortDoux: string; accentSurFort: string;
  /** Pastilles : fond clair + texte foncé. */
  succesFond: string; surSuccesFond: string; alerteFond: string; surAlerteFond: string;
};

const clair: Couleurs = {
  fond: '#FFF8F0', surface: '#FFFFFF', texte: '#1B2A41', texteDoux: '#5B6577', bordure: '#F0DCC8',
  accent: '#CC4A1F', surAccent: '#FFFFFF', accentVif: '#FF6B35', accentTexte: '#C2410C',
  alerte: '#B45309', danger: '#C0262D', succes: '#1E7F52',
  fort: '#1B2A41', surFort: '#FFF8F0', surFortDoux: '#C9D1DC', accentSurFort: '#FF8A5C',
  succesFond: '#E3F6EC', surSuccesFond: '#17663F', alerteFond: '#FDECDF', surAlerteFond: '#9A3412',
};

const sombre: Couleurs = {
  fond: '#1B2A41', surface: '#24364F', texte: '#FFF8F0', texteDoux: '#B8C2D1', bordure: '#34496A',
  accent: '#CC4A1F', surAccent: '#FFFFFF', accentVif: '#FF8A5C', accentTexte: '#FF9E78',
  alerte: '#F5B041', danger: '#FF8A8E', succes: '#4CC985',
  fort: '#0F1A2B', surFort: '#FFF8F0', surFortDoux: '#C9D1DC', accentSurFort: '#FF8A5C',
  succesFond: '#123B2A', surSuccesFond: '#7FE0AE', alerteFond: '#3E2414', surAlerteFond: '#FFB98A',
};

/** Noms des polices chargées dans app/_layout.tsx (@expo-google-fonts). */
export const polices = {
  titre: 'Baloo2_800ExtraBold',
  titreMoyen: 'Baloo2_700Bold',
  texte: 'NunitoSans_400Regular',
  texteGras: 'NunitoSans_700Bold',
} as const;

export const espace = { xs: 4, s: 8, m: 12, l: 16, xl: 24, xxl: 32 } as const;
export const rayon = { s: 12, m: 20, l: 28 } as const;
export const police = { titre: 30, grand: 52, moyen: 24, normal: 16, petit: 13 } as const;
export const TOUCHE_MIN = 48;

export function couleursPour(schema: 'light' | 'dark' | null | undefined): Couleurs {
  return schema === 'dark' ? sombre : clair;
}

export function useCouleurs(): Couleurs {
  return couleursPour(useColorScheme());
}
