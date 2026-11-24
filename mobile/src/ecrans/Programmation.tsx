import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';
import type { Creneau, Dispositif } from '../api/types';
import { useRessource } from '../donnees/useRessource';
import { JOURS_COURTS, resumer, trier, valider } from '../programmation/creneaux';
import { useApi } from '../session/SessionContext';
import { espace, rayon, TOUCHE_MIN, useCouleurs } from '../theme';
import { Bouton, Carte, Champ, Ecran, MessageErreur, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';
import { Segments } from '../ui/Segments';

const HEURE = /^([01]\d|2[0-3]):[0-5]\d$/;

function Jours({ choisis, onChange }: { choisis: number[]; onChange: (j: number[]) => void }) {
  const c = useCouleurs();
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: espace.s }}>
      {JOURS_COURTS.map((nom, j) => {
        const coche = choisis.includes(j);
        return (
          <Pressable key={nom} accessibilityRole="checkbox" accessibilityLabel={nom} accessibilityState={{ checked: coche }}
                     onPress={() => onChange(coche ? choisis.filter((x) => x !== j) : [...choisis, j].sort())}
                     style={{ minWidth: TOUCHE_MIN, minHeight: TOUCHE_MIN, alignItems: 'center', justifyContent: 'center',
                              borderRadius: rayon.s, backgroundColor: coche ? c.accent : c.surface,
                              borderWidth: 1, borderColor: c.accent }}>
            <Texte couleur={coche ? c.surAccent : c.accent}>{nom}</Texte>
          </Pressable>
        );
      })}
    </View>
  );
}

function Editeur({ d }: { d: Dispositif }) {
  const api = useApi();
  const router = useRouter();
  const clim = d.kind === 'ir_ac';
  const [slots, setSlots] = useState<Creneau[]>(trier(d.schedule.slots));
  const [heure, setHeure] = useState('');
  const [jours, setJours] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [action, setAction] = useState<'on' | 'off'>('on');
  const [consigne, setConsigne] = useState('26');
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  function ajouter() {
    const nouveau: Creneau = {
      at: heure, days: jours,
      action: clim
        ? (action === 'off' ? { mode: 'off' } : { mode: 'cool', setpoint_c: Number(consigne) })
        : { on: action === 'on' },
    };
    const liste = trier([...slots, nouveau]);
    const e = valider(liste);
    setErreur(e);
    if (!e) {
      setSlots(liste);
      setHeure('');
    }
  }

  async function enregistrer() {
    const e = valider(slots);
    if (e) {
      setErreur(e);
      return;
    }
    setEnvoi(true);
    try {
      await api.programmer(d.id, { slots });
      router.back();
    } catch (x) {
      setErreur(x instanceof Error ? x.message : 'Une erreur est survenue.');
    } finally {
      setEnvoi(false);
    }
  }

  const consigneOk = !clim || action === 'off' || /^(1[6-9]|2\d|30)$/.test(consigne);
  return (
    <>
      <Titre>{`Programmer ${d.name}`}</Titre>
      <Texte doux>Les programmations sont gardées dans l’appareil : elles marchent même sans internet.</Texte>
      {slots.map((s, i) => (
        <Carte key={`${s.at}-${i}`}>
          <Texte>{resumer(s)}</Texte>
          <Bouton titre={`Supprimer ${resumer(s)}`} secondaire onPress={() => setSlots(slots.filter((_, k) => k !== i))} />
        </Carte>
      ))}
      <Carte>
        <Texte gras>Nouvelle action</Texte>
        <Champ libelle="Heure (HH:MM)" valeur={heure} onChange={setHeure} clavier="number-pad" />
        <Jours choisis={jours} onChange={setJours} />
        <Segments items={[['on', 'Allumer'], ['off', 'Éteindre']]} actif={action} onChange={setAction} />
        {clim && action === 'on' ? (
          <Champ libelle="Consigne (°C)" valeur={consigne} onChange={setConsigne} clavier="number-pad" />
        ) : null}
        <Bouton titre="Ajouter" onPress={ajouter} desactive={!HEURE.test(heure) || !consigneOk} secondaire />
      </Carte>
      <MessageErreur message={erreur} />
      <Bouton titre="Enregistrer" onPress={() => void enregistrer()} chargement={envoi} />
      <Bouton titre="Annuler" onPress={() => router.back()} secondaire />
    </>
  );
}

export function Programmation() {
  const api = useApi();
  const { id } = useLocalSearchParams<{ id: string }>();
  const ressource = useRessource<Dispositif[]>('dispositifs', () => api.dispositifs());
  const [d, setD] = useState<Dispositif | null>(null);
  useEffect(() => {
    if (!d && ressource.donnees) setD(ressource.donnees.find((x) => x.id === id) ?? null);
  }, [ressource.donnees, id, d]);
  return (
    <Ecran testID="ecran-programmation">
      <EtatRessource ressource={ressource}>
        {() => (d ? <Editeur d={d} /> : <Texte>Appareil introuvable.</Texte>)}
      </EtatRessource>
    </Ecran>
  );
}
