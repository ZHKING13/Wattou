import Svg, { Circle, G, Path, Rect } from 'react-native-svg';
import { useCouleurs } from '../theme';

/** Le personnage Wattou : l'ampoule souriante (logo et conseils). */
export function Ampoule({ taille = 40, fond, ampoule }: { taille?: number; fond?: string; ampoule?: string }) {
  const c = useCouleurs();
  const nuit = '#1B2A41';
  return (
    <Svg width={taille} height={taille} viewBox="0 0 72 72" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      <Circle cx={36} cy={36} r={36} fill={fond ?? c.accent} />
      <G transform="translate(36 37) scale(1.3) translate(-36 -37)">
        <Path d="M24 30 C24 20 48 20 48 30 C48 38 40 40 40 46 H32 C32 40 24 38 24 30 Z" fill={ampoule ?? '#FFF8F0'} />
        <Rect x={32} y={49} width={8} height={5} rx={2} fill={nuit} />
        <Circle cx={32} cy={30} r={2.5} fill={nuit} />
        <Circle cx={40} cy={30} r={2.5} fill={nuit} />
        <Path d="M31 35 Q36 39 41 35" stroke={nuit} strokeWidth={2.5} fill="none" strokeLinecap="round" />
      </G>
    </Svg>
  );
}
