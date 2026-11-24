import { Redirect, Tabs } from 'expo-router';
import { useSession } from '../../src/session/SessionContext';
import { useCouleurs } from '../../src/theme';

export default function Onglets() {
  const { etat } = useSession();
  const c = useCouleurs();
  if (etat === 'chargement') return null;
  if (etat === 'deconnecte') return <Redirect href="/connexion" />;
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: c.accent, tabBarStyle: { backgroundColor: c.surface } }}>
      <Tabs.Screen name="index" options={{ title: 'Accueil' }} />
      <Tabs.Screen name="appareils" options={{ title: 'Appareils' }} />
      <Tabs.Screen name="historique" options={{ title: 'Historique' }} />
      <Tabs.Screen name="controle" options={{ title: 'Contrôle' }} />
    </Tabs>
  );
}
