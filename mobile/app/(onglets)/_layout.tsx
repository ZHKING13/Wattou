import { Redirect, Tabs } from 'expo-router';
import { FournisseurAlertes, useAlertes } from '../../src/donnees/alertes';
import { useSession } from '../../src/session/SessionContext';
import { polices, useCouleurs } from '../../src/theme';
import { Icone, type NomIcone } from '../../src/ui/icones';

const ICONES: Record<string, NomIcone> = {
  index: 'accueil', appareils: 'appareils', historique: 'historique', controle: 'controle', alertes: 'alertes',
};

function OngletsConnectes() {
  const c = useCouleurs();
  const { nonLues } = useAlertes();
  return (
    <Tabs screenOptions={({ route }) => ({
      headerShown: false,
      tabBarActiveTintColor: c.accentTexte,
      tabBarInactiveTintColor: c.texteDoux,
      tabBarStyle: { backgroundColor: c.surface, borderTopColor: c.bordure },
      tabBarLabelStyle: { fontFamily: polices.texteGras },
      tabBarIcon: ({ color }) => <Icone nom={ICONES[route.name] ?? 'accueil'} couleur={String(color)} />,
    })}>
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
