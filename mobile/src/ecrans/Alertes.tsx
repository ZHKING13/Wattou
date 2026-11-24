import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, Switch, View } from 'react-native';
import type { Alerte, KindAlerte, Resume } from '../api/types';
import { useAlertes } from '../donnees/alertes';
import { useRessource } from '../donnees/useRessource';
import { depuis } from '../format';
import { useApi, useDeps } from '../session/SessionContext';
import { espace, rayon, useCouleurs } from '../theme';
import { Carte, Ecran, MessageErreur, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';

const DANGER: KindAlerte[] = ['absence_load', 'meter_gap', 'night_unknown'];
const NEUTRE: KindAlerte[] = ['outage'];

function ton(k: KindAlerte): 'danger' | 'alerte' | undefined {
  if (DANGER.includes(k)) return 'danger';
  if (NEUTRE.includes(k)) return undefined;
  return 'alerte';
}

function Absence() {
  const api = useApi();
  const c = useCouleurs();
  const resume = useRessource<Resume>('resume', () => api.resume());
  const [actif, setActif] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  useEffect(() => {
    if (resume.donnees) setActif(resume.donnees.absence_mode);
  }, [resume.donnees]);
  async function basculer(v: boolean) {
    setActif(v);
    setErreur(null);
    try {
      await api.absence(v);
    } catch (e) {
      setActif(!v);
      setErreur(e instanceof Error ? e.message : 'Une erreur est survenue.');
    }
  }
  return (
    <Carte ton={actif ? 'alerte' : undefined}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Texte gras>Je m’absente</Texte>
        <Switch accessibilityRole="switch" accessibilityLabel="Je m’absente" value={actif}
                onValueChange={(v) => void basculer(v)} trackColor={{ true: c.alerte, false: c.bordure }}
                thumbColor={c.surface} />
      </View>
      <Texte doux>
        {actif
          ? 'Wattou vous prévient si quelque chose consomme pendant votre absence.'
          : 'Activez-le quand vous partez : toute consommation inconnue déclenchera une alerte.'}
      </Texte>
      <MessageErreur message={erreur} />
    </Carte>
  );
}

function Ligne({ a, onLire }: { a: Alerte; onLire: () => void }) {
  const deps = useDeps();
  const c = useCouleurs();
  const t = ton(a.kind);
  const couleur = t === 'danger' ? c.danger : t === 'alerte' ? c.alerte : c.texteDoux;
  return (
    <Pressable testID={`alerte-${a.id}`} accessibilityHint={t ?? 'normal'} accessibilityRole="button"
               onPress={() => !a.read && onLire()}
               style={{ backgroundColor: c.surface, borderRadius: rayon.m, padding: espace.l, gap: espace.xs,
                        borderLeftWidth: 4, borderLeftColor: couleur }}>
      <Texte gras={!a.read}>{a.message}</Texte>
      <Texte doux>{depuis(a.ts, deps.maintenant())}</Texte>
    </Pressable>
  );
}

export function Alertes() {
  const { ressource, alertes, nonLues, marquerLue } = useAlertes();
  useFocusEffect(useCallback(() => {
    void ressource.rafraichir();
  }, [ressource.rafraichir]));
  return (
    <Ecran testID="ecran-alertes" onRefresh={ressource.rafraichir}>
      <Titre>Alertes</Titre>
      <Absence />
      <EtatRessource ressource={ressource}>
        {() => (
          <View style={{ gap: espace.m }}>
            <Texte doux accessibilityLabel={`${nonLues} alerte${nonLues > 1 ? 's' : ''} non lue${nonLues > 1 ? 's' : ''}`}>
              {nonLues ? `${nonLues} non lue${nonLues > 1 ? 's' : ''}` : 'Tout est lu'}
            </Texte>
            {alertes.length === 0 ? <Texte>Aucune alerte. Tout va bien.</Texte> : null}
            {alertes.map((a) => <Ligne key={a.id} a={a} onLire={() => void marquerLue(a.id)} />)}
          </View>
        )}
      </EtatRessource>
    </Ecran>
  );
}
