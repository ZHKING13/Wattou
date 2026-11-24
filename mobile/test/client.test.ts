import { creerApi } from '../src/api/client';
import { ErreurServeur, HorsLigne, NonAutorise, PilotageIndisponible, Refuse } from '../src/api/erreurs';

type Appel = { url: string; init: RequestInit };

function fauxFetch(reponse: () => Promise<Response> | Response) {
  const appels: Appel[] = [];
  const f = jest.fn(async (url: string, init: RequestInit) => {
    appels.push({ url, init });
    return reponse();
  }) as unknown as typeof fetch;
  return { f, appels };
}

const json = (statut: number, corps: unknown) =>
  new Response(JSON.stringify(corps), { status: statut, headers: { 'Content-Type': 'application/json' } });

const api = (f: typeof fetch, jeton: string | null = 'j') =>
  creerApi({ baseUrl: 'http://srv/', jeton: async () => jeton, fetch: f });

test('resume envoie le jeton et renvoie le JSON', async () => {
  const { f, appels } = fauxFetch(() => json(200, { power_w: 600 }));
  expect(await api(f).resume()).toEqual({ power_w: 600 });
  expect(appels[0].url).toBe('http://srv/api/v1/foyer/summary');
  expect((appels[0].init.headers as Record<string, string>).Authorization).toBe('Bearer j');
});

test('401 -> NonAutorise', async () => {
  const { f } = fauxFetch(() => json(401, { detail: 'Connexion requise.' }));
  await expect(api(f).resume()).rejects.toBeInstanceOf(NonAutorise);
});

test('422 -> Refuse avec le message du serveur', async () => {
  const { f } = fauxFetch(() => json(422, { detail: 'Ce relevé est plus élevé que le précédent.' }));
  const e = await api(f).saisirCredit({ kind: 'reading', kwh: 60 }).catch((x) => x);
  expect(e).toBeInstanceOf(Refuse);
  expect(e.message).toBe('Ce relevé est plus élevé que le précédent.');
  expect(e.statut).toBe(422);
});

test('422 de validation pydantic (liste) -> message générique', async () => {
  const { f } = fauxFetch(() => json(422, { detail: [{ msg: 'x' }] }));
  const e = await api(f).regles(20).catch((x) => x);
  expect(e).toBeInstanceOf(Refuse);
  expect(e.message).toBe('Valeur refusée par le serveur.');
});

test('503 -> PilotageIndisponible', async () => {
  const { f } = fauxFetch(() => json(503, { detail: 'Pilotage indisponible' }));
  await expect(api(f).commander('prise-fer', { on: false })).rejects.toBeInstanceOf(PilotageIndisponible);
});

test('500 -> ErreurServeur', async () => {
  const { f } = fauxFetch(() => new Response('oups', { status: 500 }));
  await expect(api(f).alertes()).rejects.toBeInstanceOf(ErreurServeur);
});

test('fetch qui rejette -> HorsLigne', async () => {
  const f = jest.fn(async () => { throw new TypeError('Network request failed'); }) as unknown as typeof fetch;
  await expect(api(f).resume()).rejects.toBeInstanceOf(HorsLigne);
});

test('délai de 15 s -> HorsLigne', async () => {
  jest.useFakeTimers();
  const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
  const attendu = expect(api(f).resume()).rejects.toBeInstanceOf(HorsLigne);
  await jest.advanceTimersByTimeAsync(15_001);
  await attendu;
  jest.useRealTimers();
});

test('historique encode from/to/step', async () => {
  const { f, appels } = fauxFetch(() => json(200, []));
  await api(f).historique('2026-11-24T00:00:00Z', '2026-11-24T15:00:00Z', 'hour');
  expect(appels[0].url).toBe(
    'http://srv/api/v1/foyer/history?from=2026-11-24T00%3A00%3A00Z&to=2026-11-24T15%3A00%3A00Z&step=hour',
  );
});

test('connecter sans jeton : pas d\'en-tête Authorization, corps JSON', async () => {
  const { f, appels } = fauxFetch(() => json(200, { token: 't', foyer_id: 'f' }));
  expect(await api(f, null).connecter('+2250700000000', 'secret1')).toEqual({ token: 't', foyer_id: 'f' });
  expect((appels[0].init.headers as Record<string, string>).Authorization).toBeUndefined();
  expect(appels[0].init.method).toBe('POST');
  expect(JSON.parse(appels[0].init.body as string)).toEqual({ phone: '+2250700000000', password: 'secret1' });
});

test('renommer fait un PATCH, absence un PUT', async () => {
  const { f, appels } = fauxFetch(() => json(200, { ok: true }));
  await api(f).renommer('a1', 'Clim');
  await api(f).absence(true);
  expect(appels.map((a) => [a.init.method, a.url])).toEqual([
    ['PATCH', 'http://srv/api/v1/appliances/a1'],
    ['PUT', 'http://srv/api/v1/foyer/absence'],
  ]);
});
