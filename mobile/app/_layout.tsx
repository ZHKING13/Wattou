import * as Notifications from 'expo-notifications';
import { dependancesReelles } from '../src/dependances';
import { Racine } from '../src/racine';

// Une alerte reçue pendant que l'app est ouverte s'affiche quand même (bannière + son).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false,
  }),
});

export default function Layout() {
  return <Racine deps={dependancesReelles} />;
}
