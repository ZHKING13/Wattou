import { creerPush, type ModuleNotifications } from '../src/notifications/push';

function module(statut: 'granted' | 'denied', dejaAccorde = false): ModuleNotifications & { canaux: string[] } {
  const m = {
    canaux: [] as string[],
    getPermissionsAsync: jest.fn(async () => ({ status: dejaAccorde ? 'granted' : 'undetermined' })),
    requestPermissionsAsync: jest.fn(async () => ({ status: statut })),
    getExpoPushTokenAsync: jest.fn(async () => ({ data: 'ExponentPushToken[x]' })),
    setNotificationChannelAsync: jest.fn(async (id: string) => { m.canaux.push(id); return null; }),
  };
  return m as unknown as ModuleNotifications & { canaux: string[] };
}

test('permission accordée : jeton envoyé au serveur, canal Android créé', async () => {
  const enregistrerPush = jest.fn(async () => {});
  const n = module('granted');
  const push = creerPush({ notifications: n, estAppareil: true, projectId: 'p1', plateforme: 'android' });
  expect(await push.demanderEtEnregistrer({ enregistrerPush })).toBe('ok');
  expect(enregistrerPush).toHaveBeenCalledWith('ExponentPushToken[x]');
  expect(n.canaux).toEqual(['alertes']);
  expect(n.getExpoPushTokenAsync).toHaveBeenCalledWith({ projectId: 'p1' });
});

test('permission refusée : aucun appel', async () => {
  const enregistrerPush = jest.fn(async () => {});
  const push = creerPush({ notifications: module('denied'), estAppareil: true, projectId: 'p1', plateforme: 'android' });
  expect(await push.demanderEtEnregistrer({ enregistrerPush })).toBe('refuse');
  expect(enregistrerPush).not.toHaveBeenCalled();
});

test('sans projet EAS ou sur simulateur : indisponible, sans erreur', async () => {
  const enregistrerPush = jest.fn(async () => {});
  expect(await creerPush({ notifications: module('granted'), estAppareil: true, projectId: '', plateforme: 'android' })
    .demanderEtEnregistrer({ enregistrerPush })).toBe('indisponible');
  expect(await creerPush({ notifications: module('granted'), estAppareil: false, projectId: 'p1', plateforme: 'android' })
    .demanderEtEnregistrer({ enregistrerPush })).toBe('indisponible');
  expect(enregistrerPush).not.toHaveBeenCalled();
});

test('erreur réseau à l\'enregistrement : indisponible, pas d\'exception', async () => {
  const enregistrerPush = jest.fn(async () => { throw new Error('réseau'); });
  const push = creerPush({ notifications: module('granted', true), estAppareil: true, projectId: 'p1', plateforme: 'android' });
  expect(await push.demanderEtEnregistrer({ enregistrerPush })).toBe('indisponible');
});
