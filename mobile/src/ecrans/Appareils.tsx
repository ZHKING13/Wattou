import { useState } from 'react';
import { Pressable, View } from 'react-native';
import type { Appareil, Periode } from '../api/types';
import { useRessource } from '../donnees/useRessource';
import { fcfa } from '../format';
import { useApi } from '../session/SessionContext';
import { espace, police, rayon, TOUCHE_MIN, useCouleurs } from '../theme';
import { Bouton, Carte, Champ, Ecran, MessageErreur, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';
import { Segments } from '../ui/Segments';

const SUGGESTIONS = ['Clim', 'Frigo', 'Congélateur', 'Ventilateur', 'Télévision', 'Fer à repasser', 'Chauffe-eau'];
const PRISES: Record<string, string> = { frigo: 'Frigo', fer: 'Fer à repasser', tv: 'Télévision', clim: 'Clim' };

export function nomAppareil(a: Appareil): string {
  if (a.id === 'fond') return 'Consommation de fond (veilles, box)';
  if (a.id === 'autres') return 'Autres petits appareils';
  if (a.device_id) {
    const base = a.label && a.label !== a.device_id
      ? a.label
      : PRISES[a.device_id.replace(/^prise-/, '')] ?? a.device_id.replace(/^prise-/, '');
    return `${base} (prise connectée)`;
  }
  if (!a.label) return `Appareil inconnu (≈ ${a.power_w ?? '?'} W)`;
  return a.label;
}

function Pastille({ texte }: { texte: string }) {
  const c = useCouleurs();
  return (
    <View style={{ alignSelf: 'flex-start', borderRadius: rayon.s, borderWidth: 1, borderColor: c.bordure,
                   paddingHorizontal: espace.s, paddingVertical: 2 }}>
      <Texte doux taille={police.petit}>{texte}</Texte>
    </View>
  );
}

function Nommer({ appareil, onFini }: { appareil: Appareil; onFini: () => void }) {
  const api = useApi();
  const c = useCouleurs();
  const [libre, setLibre] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  async function nommer(nom: string) {
    const propre = nom.trim().slice(0, 60);
    if (!propre) return;
    try {
      await api.renommer(appareil.id, propre);
      onFini();
    } catch (e) {
      setErreur(e instanceof Error ? e.message : 'Une erreur est survenue.');
    }
  }
  return (
    <View style={{ gap: espace.s }}>
      <Texte doux>Qu’est-ce que c’est ?</Texte>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: espace.s }}>
        {SUGGESTIONS.map((s) => (
          <Pressable key={s} accessibilityRole="button" accessibilityLabel={s} onPress={() => void nommer(s)}
                     style={{ minHeight: TOUCHE_MIN, justifyContent: 'center', paddingHorizontal: espace.m,
                              borderRadius: rayon.l, borderWidth: 1, borderColor: c.accent }}>
            <Texte couleur={c.accent}>{s}</Texte>
          </Pressable>
        ))}
      </View>
      <Champ libelle="Autre nom" valeur={libre} onChange={setLibre} />
      <Bouton titre="Valider le nom" onPress={() => void nommer(libre)} desactive={!libre.trim()} />
      <MessageErreur message={erreur} />
    </View>
  );
}

function Ligne({ a, onRenomme }: { a: Appareil; onRenomme: () => void }) {
  const c = useCouleurs();
  const [nommer, setNommer] = useState(false);
  const special = a.id === 'fond' || a.id === 'autres';
  return (
    <Carte testID={`appareil-${a.id}`}>
      <Texte gras>{nomAppareil(a)}</Texte>
      <View style={{ height: 8, borderRadius: 4, backgroundColor: c.bordure }}>
        <View style={{ height: 8, borderRadius: 4, width: `${Math.round(a.share * 100)}%`, backgroundColor: c.accent }} />
      </View>
      <Texte>{`${fcfa(a.fcfa)} · ${Math.round(a.share * 100)} %`}</Texte>
      {!special ? <Pastille texte="Estimation" /> : null}
      {!special && !a.label && !a.device_id && !nommer ? (
        <Bouton titre="Nommer" onPress={() => setNommer(true)} secondaire />
      ) : null}
      {nommer ? <Nommer appareil={a} onFini={() => { setNommer(false); onRenomme(); }} /> : null}
    </Carte>
  );
}

export function Appareils() {
  const api = useApi();
  const [periode, setPeriode] = useState<Periode>('day');
  const ressource = useRessource<Appareil[]>(`appareils:${periode}`, () => api.appareils(periode));
  return (
    <Ecran testID="ecran-appareils">
      <Titre>Où part votre argent</Titre>
      <Segments items={[['day', 'Aujourd’hui'], ['week', '7 jours'], ['month', '30 jours']]} actif={periode} onChange={setPeriode} />
      <EtatRessource ressource={ressource}>
        {(liste) => liste.length === 0 ? (
          <Texte doux>Wattou apprend à reconnaître vos appareils. Revenez demain.</Texte>
        ) : (
          <View style={{ gap: espace.m }}>
            {[...liste].sort((x, y) => y.fcfa - x.fcfa).map((a) => (
              <Ligne key={a.id} a={a} onRenomme={() => void ressource.rafraichir()} />
            ))}
          </View>
        )}
      </EtatRessource>
    </Ecran>
  );
}
