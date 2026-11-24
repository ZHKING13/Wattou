import { Baloo2_700Bold, Baloo2_800ExtraBold } from '@expo-google-fonts/baloo-2';
import { NunitoSans_400Regular, NunitoSans_700Bold } from '@expo-google-fonts/nunito-sans';
import { useFonts } from 'expo-font';
import * as Notifications from 'expo-notifications';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { dependancesReelles } from '../src/dependances';
import { Racine } from '../src/racine';

// Une alerte reçue pendant que l'app est ouverte s'affiche quand même (bannière + son).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false,
  }),
});

void SplashScreen.preventAutoHideAsync();

export default function Layout() {
  // Polices embarquées (hors ligne) ; l'écran de démarrage reste affiché jusqu'à leur chargement
  // (ou leur échec : on affiche alors en police système plutôt que rien).
  const [chargees, erreur] = useFonts({ Baloo2_700Bold, Baloo2_800ExtraBold, NunitoSans_400Regular, NunitoSans_700Bold });
  useEffect(() => {
    if (chargees || erreur) void SplashScreen.hideAsync();
  }, [chargees, erreur]);
  return <Racine deps={dependancesReelles} />;
}
