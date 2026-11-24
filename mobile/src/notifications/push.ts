import type * as N from 'expo-notifications';
import type { Api } from '../api/client';

export type ResultatPush = 'ok' | 'refuse' | 'indisponible';

export interface Push {
  /** Après connexion : permission, canal Android, jeton Expo envoyé au serveur. Sans exception. */
  demanderEtEnregistrer(api: Pick<Api, 'enregistrerPush'>): Promise<ResultatPush>;
  /** Appelle `f` quand l'utilisateur touche une notification ; renvoie de quoi se désabonner. */
  ecouterOuvertures(f: () => void): () => void;
}

export type ModuleNotifications = Pick<typeof N, 'getPermissionsAsync' | 'requestPermissionsAsync'
  | 'getExpoPushTokenAsync' | 'setNotificationChannelAsync'>
  & Partial<Pick<typeof N, 'addNotificationResponseReceivedListener'>>;

export function creerPush(o: {
  notifications: ModuleNotifications; estAppareil: boolean; projectId: string; plateforme: string;
}): Push {
  return {
    async demanderEtEnregistrer(api) {
      if (!o.estAppareil || !o.projectId) return 'indisponible';
      try {
        if (o.plateforme === 'android') {
          await o.notifications.setNotificationChannelAsync('alertes', {
            name: 'Alertes Wattou', importance: 4 /* HIGH */,
          });
        }
        let { status } = await o.notifications.getPermissionsAsync();
        if (status !== 'granted') status = (await o.notifications.requestPermissionsAsync()).status;
        if (status !== 'granted') return 'refuse';
        const { data } = await o.notifications.getExpoPushTokenAsync({ projectId: o.projectId });
        await api.enregistrerPush(data);
        return 'ok';
      } catch {
        return 'indisponible';
      }
    },
    ecouterOuvertures(f) {
      const abo = o.notifications.addNotificationResponseReceivedListener?.(() => f());
      return () => abo?.remove();
    },
  };
}
