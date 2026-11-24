import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Refuse } from '../api/erreurs';
import { nombre } from '../format';
import { useApi } from '../session/SessionContext';
import { Bouton, Champ, Ecran, Texte, Titre } from '../ui/base';
import { Segments } from '../ui/Segments';

type Onglet = 'reading' | 'recharge';

export function Credit() {
  const api = useApi();
  const router = useRouter();
  const [onglet, setOnglet] = useState<Onglet>('reading');
  const [kwhSaisi, setKwh] = useState('');
  const [montant, setMontant] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const k = nombre(kwhSaisi);
  const m = nombre(montant);
  const valide = k !== null && k > 0 && (onglet === 'reading' || (m !== null && m > 0));

  async function enregistrer() {
    if (k === null) return;
    setEnvoi(true);
    setErreur(null);
    try {
      await api.saisirCredit(onglet === 'reading'
        ? { kind: 'reading', kwh: k }
        : { kind: 'recharge', kwh: k, amount_fcfa: Math.round(m ?? 0) });
      router.back();
    } catch (e) {
      setErreur(e instanceof Refuse || e instanceof Error ? e.message : 'Une erreur est survenue.');
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Ecran testID="ecran-credit">
      <Titre>Crédit du compteur</Titre>
      <Segments items={[['reading', 'Relevé du compteur'], ['recharge', 'Recharge']]} actif={onglet}
                onChange={(o) => { setOnglet(o); setErreur(null); }} />
      {onglet === 'reading' ? (
        <>
          <Texte doux>Recopiez le nombre de kWh qu’affiche votre compteur CIE en ce moment.</Texte>
          <Champ libelle="kWh affichés par le compteur" valeur={kwhSaisi} onChange={setKwh} clavier="decimal-pad" erreur={erreur} />
        </>
      ) : (
        <>
          <Texte doux>Indiquez votre dernière recharge : le montant payé et les kWh obtenus.</Texte>
          <Champ libelle="Montant payé (FCFA)" valeur={montant} onChange={setMontant} clavier="number-pad" />
          <Champ libelle="kWh obtenus" valeur={kwhSaisi} onChange={setKwh} clavier="decimal-pad" erreur={erreur} />
        </>
      )}
      <Bouton titre="Enregistrer" onPress={enregistrer} desactive={!valide} chargement={envoi} />
      <Bouton titre="Annuler" onPress={() => router.back()} secondaire />
    </Ecran>
  );
}
