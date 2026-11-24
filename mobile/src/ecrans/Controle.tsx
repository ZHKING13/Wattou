import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, Switch, View } from 'react-native';
import type { CommandeClim, CommandePrise, Dispositif, Resume } from '../api/types';
import { useRessource } from '../donnees/useRessource';
import { useApi } from '../session/SessionContext';
import { espace, police, rayon, TOUCHE_MIN, useCouleurs } from '../theme';
import { Carte, Ecran, MessageErreur, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';
import { Segments } from '../ui/Segments';

const CONSIGNE_MIN = 16;
const CONSIGNE_MAX = 30;

/** Envoie une commande ; en cas d'échec, revient à l'état précédent et donne le message. */
function useCommande(id: string) {
  const api = useApi();
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  async function envoyer(cmd: CommandePrise | CommandeClim, annuler: () => void) {
    setErreur(null);
    setEnvoi(true);
    try {
      await api.commander(id, cmd);
    } catch (e) {
      annuler();
      setErreur(e instanceof Error ? e.message : 'Une erreur est survenue.');
    } finally {
      setEnvoi(false);
    }
  }
  return { erreur, envoyer, envoi };
}

function BoutonRond({ libelle, signe, onPress, desactive }: {
  libelle: string; signe: string; onPress: () => void; desactive: boolean;
}) {
  const c = useCouleurs();
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={libelle} accessibilityState={{ disabled: desactive }}
               disabled={desactive} onPress={onPress}
               style={{ width: TOUCHE_MIN, height: TOUCHE_MIN, borderRadius: TOUCHE_MIN / 2, alignItems: 'center',
                        justifyContent: 'center', borderWidth: 1.5, borderColor: c.accentTexte, opacity: desactive ? 0.4 : 1 }}>
      <Texte gras couleur={c.accentTexte} taille={police.titre}>{signe}</Texte>
    </Pressable>
  );
}

function LienProgrammer({ d }: { d: Dispositif }) {
  const c = useCouleurs();
  const router = useRouter();
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={`Programmer ${d.name}`}
               onPress={() => router.push({ pathname: '/programmation/[id]', params: { id: d.id } })}
               style={{ minHeight: TOUCHE_MIN, justifyContent: 'center' }}>
      <Texte couleur={c.accentTexte}>
        {d.schedule.slots.length ? `Programmations (${d.schedule.slots.length})` : 'Programmer'}
      </Texte>
    </Pressable>
  );
}

function Clim({ d }: { d: Dispositif }) {
  const [marche, setMarche] = useState(d.last_state.mode !== undefined && d.last_state.mode !== 'off');
  const [consigne, setConsigne] = useState(d.last_state.setpoint_c ?? 26);
  const { erreur, envoyer, envoi } = useCommande(d.id);
  // l'état réel (programmation, règle crédit bas) remplace l'affichage, sauf pendant un envoi
  useEffect(() => {
    if (envoi) return;
    setMarche(d.last_state.mode !== undefined && d.last_state.mode !== 'off');
    if (d.last_state.setpoint_c !== undefined) setConsigne(d.last_state.setpoint_c);
  }, [d.last_state.mode, d.last_state.setpoint_c]); 
  const changerConsigne = (delta: number) => {
    const avant = consigne;
    const apres = Math.min(CONSIGNE_MAX, Math.max(CONSIGNE_MIN, avant + delta));
    setConsigne(apres);
    void envoyer({ setpoint_c: apres }, () => setConsigne(avant));
  };
  return (
    <Carte testID={`dispositif-${d.id}`}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Texte gras>{d.name}</Texte>
        <Switch accessibilityRole="switch" accessibilityLabel={d.name} value={marche} disabled={envoi}
                onValueChange={(v) => {
                  setMarche(v);
                  void envoyer({ mode: v ? 'cool' : 'off' }, () => setMarche(!v));
                }} />
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: espace.l }}>
        <BoutonRond libelle="Baisser la consigne" signe="−" onPress={() => changerConsigne(-1)} desactive={consigne <= CONSIGNE_MIN} />
        <Texte gras taille={police.titre}>{`${consigne} °C`}</Texte>
        <BoutonRond libelle="Monter la consigne" signe="+" onPress={() => changerConsigne(1)} desactive={consigne >= CONSIGNE_MAX} />
      </View>
      <Texte doux taille={police.petit}>Chaque degré en plus réduit la consommation de la clim d’environ 6 %.</Texte>
      <MessageErreur message={erreur} />
      <LienProgrammer d={d} />
    </Carte>
  );
}

function Prise({ d }: { d: Dispositif }) {
  const [on, setOn] = useState(Boolean(d.last_state.on));
  const { erreur, envoyer, envoi } = useCommande(d.id);
  useEffect(() => {
    if (!envoi) setOn(Boolean(d.last_state.on));
  }, [d.last_state.on]); 
  return (
    <Carte testID={`dispositif-${d.id}`}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View style={{ flex: 1 }}>
          <Texte gras>{d.name}</Texte>
          <Texte doux>{`${Math.round(d.last_state.p_w ?? 0)} W`}</Texte>
        </View>
        {d.essential ? null : (
          <Switch accessibilityRole="switch" accessibilityLabel={d.name} value={on} disabled={envoi}
                  onValueChange={(v) => {
                    setOn(v);
                    void envoyer({ on: v }, () => setOn(!v));
                  }} />
        )}
      </View>
      {d.essential ? <Texte doux>Toujours allumée (appareil essentiel)</Texte> : <LienProgrammer d={d} />}
      <MessageErreur message={erreur} />
    </Carte>
  );
}

function RegleCreditBas() {
  const api = useApi();
  const resume = useRessource<Resume>('resume', () => api.resume());
  const [jours, setJours] = useState<string>('2');
  const [erreur, setErreur] = useState<string | null>(null);
  useEffect(() => {
    if (resume.donnees) setJours(String(resume.donnees.low_credit_days));
  }, [resume.donnees]);
  async function choisir(v: string) {
    const avant = jours;
    setJours(v);
    setErreur(null);
    try {
      await api.regles(Number(v));
    } catch (e) {
      setJours(avant);
      setErreur(e instanceof Error ? e.message : 'Une erreur est survenue.');
    }
  }
  return (
    <Carte>
      <Texte gras>Crédit bas</Texte>
      <Texte doux>
        {`Quand il reste moins de ${jours} jour${jours === '1' ? '' : 's'} de crédit, Wattou coupe les prises non essentielles et règle la clim sur 27 °C.`}
      </Texte>
      <Segments items={[['1', '1 jour'], ['2', '2 jours'], ['3', '3 jours'], ['5', '5 jours']]} actif={jours}
                onChange={(v) => void choisir(v)} />
      <MessageErreur message={erreur} />
    </Carte>
  );
}

export function Controle() {
  const api = useApi();
  const c = useCouleurs();
  const ressource = useRessource<Dispositif[]>('dispositifs', () => api.dispositifs());
  return (
    <Ecran testID="ecran-controle" onRefresh={ressource.rafraichir}>
      <Titre>Contrôle</Titre>
      <EtatRessource ressource={ressource}>
        {(liste) => {
          const pilotables = liste.filter((d) => d.kind !== 'meter');
          return (
            <View style={{ gap: espace.m }}>
              {pilotables.length === 0 ? (
                <View style={{ padding: espace.m, borderRadius: rayon.m, backgroundColor: c.surface }}>
                  <Texte doux>Aucune prise ni clim connectée pour l’instant.</Texte>
                </View>
              ) : null}
              {pilotables.map((d) => (d.kind === 'ir_ac' ? <Clim key={d.id} d={d} /> : <Prise key={d.id} d={d} />))}
            </View>
          );
        }}
      </EtatRessource>
      <RegleCreditBas />
    </Ecran>
  );
}
