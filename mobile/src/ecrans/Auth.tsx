import { Link } from 'expo-router';
import { useState } from 'react';
import { HorsLigne, NonAutorise, Refuse } from '../api/erreurs';
import { useSession } from '../session/SessionContext';
import { Bouton, Champ, Ecran, MessageErreur, Texte, Titre } from '../ui/base';

/** « 07 00 00 00 01 » -> « +2250700000001 » ; null si ce n'est pas un numéro ivoirien à 10 chiffres. */
export function numeroCI(saisie: string): string | null {
  let chiffres = saisie.replace(/\D/g, '');
  if (chiffres.startsWith('225') && chiffres.length === 13) chiffres = chiffres.slice(3);
  return chiffres.length === 10 ? `+225${chiffres}` : null;
}

function messagePour(e: unknown): string {
  if (e instanceof NonAutorise) return 'Numéro ou mot de passe incorrect.';
  if (e instanceof Refuse) return e.message;
  if (e instanceof HorsLigne) return 'Pas de connexion internet.';
  return 'Une erreur est survenue. Réessayez.';
}

export function Connexion({ inscription }: { inscription?: boolean }) {
  const session = useSession();
  const [tel, setTel] = useState('');
  const [mdp, setMdp] = useState('');
  const [nom, setNom] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const numero = numeroCI(tel);
  const valide = numero !== null && mdp.length >= 6 && (!inscription || nom.trim().length > 0);

  async function valider() {
    if (!numero) return;
    setEnvoi(true);
    setErreur(null);
    try {
      if (inscription) await session.inscrire(numero, mdp, nom.trim());
      else await session.connecter(numero, mdp);
    } catch (e) {
      setErreur(messagePour(e));
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Ecran testID={inscription ? 'ecran-inscription' : 'ecran-connexion'}>
      <Titre>{inscription ? 'Créer votre compte' : 'Wattou'}</Titre>
      <Texte doux>
        {inscription ? 'Suivez votre crédit CIE et protégez votre compteur.' : 'Connectez-vous pour suivre votre consommation.'}
      </Texte>
      <Champ libelle="Numéro de téléphone" valeur={tel} onChange={setTel} clavier="phone-pad" />
      <Champ libelle="Mot de passe" valeur={mdp} onChange={setMdp} secret />
      {inscription ? <Champ libelle="Nom du foyer" valeur={nom} onChange={setNom} /> : null}
      <MessageErreur message={erreur} />
      <Bouton titre={inscription ? 'Créer mon compte' : 'Se connecter'} onPress={valider} desactive={!valide} chargement={envoi} />
      <Link href={inscription ? '/connexion' : '/inscription'}>
        <Texte doux>{inscription ? 'J’ai déjà un compte' : 'Créer un compte'}</Texte>
      </Link>
    </Ecran>
  );
}
