import { Redirect, Tabs } from 'expo-router';
import { FournisseurAlertes, useAlertes } from '../../src/donnees/alertes';
import { useSession } from '../../src/session/SessionContext';
import { useCouleurs } from '../../src/theme';

function OngletsConnectes() {
  const c = useCouleurs();
  const { nonLues } = useAlertes();
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: c.accentTexte, tabBarStyle: { backgroundColor: c.surface } }}>
      <Tabs.Screen name="index" options={{ title: 'Accueil' }} />
      <Tabs.Screen name="appareils" options={{ title: 'Appareils' }} />
      <Tabs.Screen name="historique" options={{ title: 'Historique' }} />
      <Tabs.Screen name="controle" options={{ title: 'Contrôle' }} />
      <Tabs.Screen name="alertes" options={{ title: 'Alertes', tabBarBadge: nonLues || undefined }} />
    </Tabs>
  );
}

export default function Onglets() {
  const { etat } = useSession();
  if (etat === 'chargement') return null;
  if (etat === 'deconnecte') return <Redirect href="/connexion" />;
  return (
    <FournisseurAlertes>
      <OngletsConnectes />
    </FournisseurAlertes>
  );
}
