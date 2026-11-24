import { type ReactNode, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View, type ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { espace, police, rayon, TOUCHE_MIN, useCouleurs } from '../theme';

export function Ecran({ children, testID, defiler = true, onRefresh }: {
  children: ReactNode; testID?: string; defiler?: boolean; onRefresh?: () => Promise<void>;
}) {
  const c = useCouleurs();
  const [tire, setTire] = useState(false);
  const contenu = <View style={{ padding: espace.l, gap: espace.l }}>{children}</View>;
  const rafraichir = async () => {
    setTire(true);
    try {
      await onRefresh?.();
    } finally {
      setTire(false);
    }
  };
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.fond }} testID={testID}>
      {defiler ? (
        <ScrollView testID={testID ? `defilement-${testID}` : undefined} keyboardShouldPersistTaps="handled"
                    refreshControl={onRefresh
                      ? <RefreshControl refreshing={tire} onRefresh={rafraichir} colors={[c.accent]} tintColor={c.accent} />
                      : undefined}>
          {contenu}
        </ScrollView>
      ) : contenu}
    </SafeAreaView>
  );
}

export function Titre({ children }: { children: ReactNode }) {
  const c = useCouleurs();
  return <Text accessibilityRole="header" style={{ color: c.texte, fontSize: police.titre, fontWeight: '700' }}>{children}</Text>;
}

export function Texte({ children, doux, gras, taille, couleur, accessibilityLabel }: {
  children: ReactNode; doux?: boolean; gras?: boolean; taille?: number; couleur?: string; accessibilityLabel?: string;
}) {
  const c = useCouleurs();
  return (
    <Text accessibilityLabel={accessibilityLabel} style={{ color: couleur ?? (doux ? c.texteDoux : c.texte), fontSize: taille ?? police.normal,
                   fontWeight: gras ? '700' : '400' }}>
      {children}
    </Text>
  );
}

export function Carte({ children, ton, testID, style }: {
  children: ReactNode; ton?: 'alerte' | 'danger'; testID?: string; style?: ViewStyle;
}) {
  const c = useCouleurs();
  const bord = ton === 'alerte' ? c.alerte : ton === 'danger' ? c.danger : c.bordure;
  return (
    <View testID={testID} accessibilityHint={ton ?? 'normal'} style={[{ backgroundColor: c.surface, borderRadius: rayon.m, padding: espace.l,
                                    borderWidth: ton ? 2 : StyleSheet.hairlineWidth, borderColor: bord, gap: espace.s }, style]}>
      {children}
    </View>
  );
}

export function Bouton({ titre, onPress, desactive, secondaire, chargement }: {
  titre: string; onPress: () => void; desactive?: boolean; secondaire?: boolean; chargement?: boolean;
}) {
  const c = useCouleurs();
  const off = desactive || chargement;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={titre}
      accessibilityState={{ disabled: !!off }}
      disabled={off}
      onPress={onPress}
      style={{ minHeight: TOUCHE_MIN, borderRadius: rayon.m, alignItems: 'center', justifyContent: 'center',
               paddingHorizontal: espace.l, opacity: off ? 0.5 : 1,
               backgroundColor: secondaire ? 'transparent' : c.accent,
               borderWidth: secondaire ? 1 : 0, borderColor: c.accent }}>
      {chargement ? <ActivityIndicator color={secondaire ? c.accent : c.surAccent} /> : (
        <Text style={{ color: secondaire ? c.accent : c.surAccent, fontSize: police.normal, fontWeight: '700' }}>{titre}</Text>
      )}
    </Pressable>
  );
}

export function Champ({ libelle, valeur, onChange, secret, clavier, erreur }: {
  libelle: string; valeur: string; onChange: (v: string) => void; secret?: boolean;
  clavier?: 'default' | 'phone-pad' | 'decimal-pad' | 'number-pad'; erreur?: string | null;
}) {
  const c = useCouleurs();
  return (
    <View style={{ gap: espace.xs }}>
      <Text style={{ color: c.texteDoux, fontSize: police.petit }}>{libelle}</Text>
      <TextInput
        accessibilityLabel={libelle}
        value={valeur}
        onChangeText={onChange}
        secureTextEntry={secret}
        keyboardType={clavier ?? 'default'}
        style={{ minHeight: TOUCHE_MIN, borderRadius: rayon.s, borderWidth: 1, borderColor: erreur ? c.danger : c.bordure,
                 paddingHorizontal: espace.m, color: c.texte, backgroundColor: c.surface, fontSize: police.normal }}
      />
      {erreur ? <Text style={{ color: c.danger, fontSize: police.petit }}>{erreur}</Text> : null}
    </View>
  );
}

export function MessageErreur({ message }: { message: string | null }) {
  const c = useCouleurs();
  if (!message) return null;
  return <Text accessibilityRole="alert" style={{ color: c.danger }}>{message}</Text>;
}
