import Svg, { Circle, Path, Rect } from 'react-native-svg';

export type NomIcone = 'accueil' | 'appareils' | 'historique' | 'controle' | 'alertes';

/** Icônes de la barre d'onglets, en trait (couleur = celle de l'onglet). */
export function Icone({ nom, couleur, taille = 24 }: { nom: NomIcone; couleur: string; taille?: number }) {
  const trait = { stroke: couleur, strokeWidth: 2, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  return (
    <Svg width={taille} height={taille} viewBox="0 0 24 24" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {nom === 'accueil' ? (
        <>
          <Path d="M3 11 L12 4 L21 11" {...trait} />
          <Path d="M5 10 V20 H19 V10" {...trait} />
          <Path d="M13 12 L10 16 H14 L11 20" {...trait} />
        </>
      ) : null}
      {nom === 'appareils' ? (
        <>
          <Circle cx={12} cy={12} r={8} {...trait} />
          <Path d="M12 4 V12 L18 16" {...trait} />
        </>
      ) : null}
      {nom === 'historique' ? (
        <>
          <Rect x={4} y={12} width={3.5} height={8} rx={1} {...trait} />
          <Rect x={10.25} y={7} width={3.5} height={13} rx={1} {...trait} />
          <Rect x={16.5} y={4} width={3.5} height={16} rx={1} {...trait} />
        </>
      ) : null}
      {nom === 'controle' ? (
        <>
          <Path d="M9 3 V8 M15 3 V8" {...trait} />
          <Path d="M6 8 H18 V12 A6 6 0 0 1 6 12 Z" {...trait} />
          <Path d="M12 18 V21" {...trait} />
        </>
      ) : null}
      {nom === 'alertes' ? (
        <>
          <Path d="M6 16 V11 A6 6 0 0 1 18 11 V16 L20 18 H4 Z" {...trait} />
          <Path d="M10 21 H14" {...trait} />
        </>
      ) : null}
    </Svg>
  );
}
