import type { ReactNode } from 'react';
import { ActivityIndicator, View } from 'react-native';
import type { Ressource } from '../donnees/useRessource';
import { heure } from '../format';
import { espace, rayon, useCouleurs } from '../theme';
import { Bouton, Texte } from './base';

export function BandeauEtat({ etat, le }: { etat: Ressource<unknown>['etat']; le: string | null }) {
  const c = useCouleurs();
  if (etat !== 'hors_ligne') return null;
  return (
    <View accessibilityRole="alert" style={{ backgroundColor: c.surface, borderColor: c.alerte, borderWidth: 1,
                                             borderRadius: rayon.s, padding: espace.m }}>
      <Texte couleur={c.alerte}>{le ? `Données de ${heure(le)} — hors connexion` : 'Hors connexion'}</Texte>
    </View>
  );
}

/** Affiche chargement / erreur / données (avec bandeau hors connexion si besoin). */
export function EtatRessource<T>({ ressource, children }: { ressource: Ressource<T>; children: (d: T) => ReactNode }) {
  const c = useCouleurs();
  const { donnees, etat, le, erreur, rafraichir } = ressource;
  if (donnees === null) {
    if (etat === 'chargement') return <ActivityIndicator color={c.accentVif} />;
    return (
      <View style={{ gap: espace.m }}>
        <Texte>{erreur ?? 'Une erreur est survenue.'}</Texte>
        <Bouton titre="Réessayer" onPress={() => void rafraichir()} secondaire />
      </View>
    );
  }
  return (
    <>
      <BandeauEtat etat={etat} le={le} />
      {children(donnees)}
    </>
  );
}
