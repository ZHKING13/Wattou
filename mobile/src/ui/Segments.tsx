import { Pressable, View } from 'react-native';
import { espace, rayon, TOUCHE_MIN, useCouleurs } from '../theme';
import { Texte } from './base';

export function Segments<T extends string>({ items, actif, onChange }: {
  items: [T, string][]; actif: T; onChange: (v: T) => void;
}) {
  const c = useCouleurs();
  return (
    <View accessibilityRole="tablist" style={{ flexDirection: 'row', gap: espace.s }}>
      {items.map(([id, nom]) => (
        <Pressable key={id} accessibilityRole="tab" accessibilityLabel={nom} accessibilityState={{ selected: actif === id }}
                   onPress={() => onChange(id)}
                   style={{ flex: 1, minHeight: TOUCHE_MIN, alignItems: 'center', justifyContent: 'center',
                            borderRadius: rayon.s, backgroundColor: actif === id ? c.accent : c.surface,
                            borderWidth: 1, borderColor: actif === id ? c.accent : c.bordure }}>
          <Texte couleur={actif === id ? c.surAccent : c.texte}>{nom}</Texte>
        </Pressable>
      ))}
    </View>
  );
}
