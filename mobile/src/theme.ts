// Thème PROVISOIRE : l'identité visuelle définitive remplacera uniquement ce fichier
// (jetons de couleur, polices, rayons). Les écrans n'utilisent que ces jetons.
import { useColorScheme } from 'react-native';

export type Couleurs = {
  fond: string; surface: string; texte: string; texteDoux: string; bordure: string;
  accent: string; surAccent: string; alerte: string; danger: string; succes: string;
};

const clair: Couleurs = {
  fond: '#f5f7f6', surface: '#ffffff', texte: '#15201c', texteDoux: '#5b6964', bordure: '#d5dfdb',
  accent: '#0f7b5f', surAccent: '#ffffff', alerte: '#b3541e', danger: '#c0262d', succes: '#1f8a4c',
};

const sombre: Couleurs = {
  fond: '#0f1513', surface: '#18211e', texte: '#e7eeeb', texteDoux: '#9aaaa4', bordure: '#2e3a36',
  accent: '#34c79c', surAccent: '#06261c', alerte: '#f08a4b', danger: '#f26b70', succes: '#4cc985',
};

export const espace = { xs: 4, s: 8, m: 12, l: 16, xl: 24, xxl: 32 } as const;
export const rayon = { s: 8, m: 12, l: 20 } as const;
export const police = { titre: 28, grand: 40, normal: 16, petit: 13 } as const;
export const TOUCHE_MIN = 48;

export function couleursPour(schema: 'light' | 'dark' | null | undefined): Couleurs {
  return schema === 'dark' ? sombre : clair;
}

export function useCouleurs(): Couleurs {
  return couleursPour(useColorScheme());
}
