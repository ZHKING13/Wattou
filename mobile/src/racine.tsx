import { Slot, useRouter } from 'expo-router';
import { useEffect } from 'react';
import type { Dependances } from './dependances';
import { FournisseurApp, useApi, useSession } from './session/SessionContext';

/** Une fois connecté : enregistre le jeton push et ouvre les alertes quand on touche une notification. */
function Notifications({ deps }: { deps: Dependances }) {
  const { etat } = useSession();
  const api = useApi();
  const router = useRouter();
  useEffect(() => {
    if (etat !== 'connecte') return;
    void deps.push.demanderEtEnregistrer(api);
    return deps.push.ecouterOuvertures(() => router.push('/alertes'));
  }, [etat, deps, api, router]);
  return null;
}

export function Racine({ deps }: { deps: Dependances }) {
  return (
    <FournisseurApp deps={deps}>
      <Notifications deps={deps} />
      <Slot />
    </FournisseurApp>
  );
}
