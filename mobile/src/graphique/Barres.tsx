import { useState } from 'react';
import { View } from 'react-native';
import Svg, { G, Line, Rect, Text as SvgText } from 'react-native-svg';
import type { PointHistorique } from '../api/types';
import { fcfa, kwh } from '../format';
import { espace, polices, useCouleurs } from '../theme';
import { Texte } from '../ui/base';
import { graduations } from './echelle';

const L = 340;
const HAUT = 200;
const MARGE_G = 32;
const MARGE_B = 22;

export function libelleBarre(p: PointHistorique, step: 'hour' | 'day'): string {
  const d = new Date(p.ts);
  const quand = step === 'hour' ? `${d.getUTCHours()} h` : `${d.getUTCDate()}/${d.getUTCMonth() + 1}`;
  return `${quand} : ${kwh(p.kwh)}`;
}

export function Barres({ points, step, prix }: { points: PointHistorique[]; step: 'hour' | 'day'; prix: number }) {
  const c = useCouleurs();
  const [choix, setChoix] = useState<number | null>(null);
  const ticks = graduations(Math.max(0, ...points.map((p) => p.kwh)));
  const max = ticks[ticks.length - 1];
  const zoneH = HAUT - MARGE_B;
  const larg = (L - MARGE_G) / Math.max(points.length, 1);
  const y = (v: number) => zoneH - (v / max) * (zoneH - 8);
  const sel = choix !== null ? points[choix] : null;
  return (
    <View style={{ gap: espace.s }}>
      <Svg width="100%" height={HAUT} viewBox={`0 0 ${L} ${HAUT}`}>
        {ticks.map((t) => (
          <G key={t}>
            <Line x1={MARGE_G} x2={L} y1={y(t)} y2={y(t)} stroke={c.bordure} strokeWidth={1} />
            <SvgText x={MARGE_G - 4} y={y(t) + 4} fontSize={10} fontFamily={polices.texte} fill={c.texteDoux} textAnchor="end">
              {String(t).replace('.', ',')}
            </SvgText>
          </G>
        ))}
        {points.map((p, i) => (
          <Rect key={p.ts} x={MARGE_G + i * larg + larg * 0.15} y={y(p.kwh)} width={larg * 0.7}
                height={Math.max(0, zoneH - y(p.kwh))} rx={2}
                fill={choix === i ? c.alerte : c.accent}
                accessibilityLabel={libelleBarre(p, step)} onPress={() => setChoix(i)} />
        ))}
        {points.map((p, i) => (i % Math.ceil(points.length / 6) === 0 ? (
          <SvgText key={`x${p.ts}`} x={MARGE_G + i * larg + larg / 2} y={HAUT - 6} fontSize={10}
                   fontFamily={polices.texte} fill={c.texteDoux} textAnchor="middle">
            {libelleBarre(p, step).split(' :')[0]}
          </SvgText>
        ) : null))}
      </Svg>
      {sel ? <Texte>{`${libelleBarre(sel, step)} · ${fcfa(sel.kwh * prix)}`}</Texte> : null}
    </View>
  );
}
