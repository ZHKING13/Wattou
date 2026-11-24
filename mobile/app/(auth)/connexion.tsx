import { Redirect } from 'expo-router';
import { Connexion } from '../../src/ecrans/Auth';
import { useSession } from '../../src/session/SessionContext';

export default function Page() {
  const { etat } = useSession();
  if (etat === 'connecte') return <Redirect href="/" />;
  return <Connexion />;
}
