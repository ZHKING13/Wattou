/**
 * Le client de l'app contre l'API réelle de la phase 1a, alimentée par le simulateur.
 * Ignoré sans WATTOU_API_URL. Prérequis : `make up`, API + ingestion + analyse lancées.
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { creerApi } from '../../src/api/client';
import { Refuse } from '../../src/api/erreurs';
import type { Resume } from '../../src/api/types';

const URL = process.env.WATTOU_API_URL;
const decrire = URL ? describe : describe.skip;

decrire('contrat client ↔ API réelle', () => {
  let jeton: string | null = null;
  const api = creerApi({ baseUrl: URL ?? '', jeton: async () => jeton });
  let foyer = '';

  beforeAll(async () => {
    const tel = `+22507${String(Date.now()).slice(-8)}`;
    const j = await api.inscrire(tel, 'secret1', 'Intégration mobile');
    jeton = j.token;
    foyer = j.foyer_id;
    const sim = spawnSync('uv', ['run', 'python', '-m', 'wattou_sim', '--foyer', foyer,
      '--start', '2026-11-01T00:00:00Z', '--backfill-days', '1', '--until', '2026-11-02T00:00:00Z'],
      { cwd: path.resolve(__dirname, '../../../simulator'), stdio: 'ignore' });
    if (sim.status !== 0) throw new Error(`simulateur en échec (code ${sim.status}, ${sim.error ?? ''})`);
    const limite = Date.now() + 240_000;
    let r: Resume | null = null;
    while (Date.now() < limite) {
      r = await api.resume();
      if (r.data_until && r.data_until >= '2026-11-01T23:59:5') break;
      await new Promise((ok) => setTimeout(ok, 2000));
    }
    if (!r?.data_until) throw new Error('aucune donnée ingérée');
  });

  test('résumé conforme, sans relevé de crédit', async () => {
    const r = await api.resume();
    for (const k of ['power_w', 'today_kwh', 'today_fcfa', 'price_fcfa_kwh', 'credit_kwh', 'days_left',
      'month_forecast_fcfa', 'absence_mode', 'low_credit_days', 'data_until'] as const) {
      expect(r).toHaveProperty(k);
    }
    expect(r.credit_kwh).toBeNull();
    expect(r.today_kwh).toBeGreaterThan(5);
  });

  test('relevé de crédit puis relevé incohérent refusé en 422', async () => {
    await api.saisirCredit({ kind: 'reading', kwh: 50 });
    const e = await api.saisirCredit({ kind: 'reading', kwh: 60 }).catch((x) => x);
    expect(e).toBeInstanceOf(Refuse);
    expect(e.statut).toBe(422);
    expect(e.message).toMatch(/plus élevé que le précédent/);
    expect((await api.resume()).credit_kwh).not.toBeNull();
  });

  test('appareils : estimation, fond et autres', async () => {
    const liste = await api.appareils('day');
    expect(liste.length).toBeGreaterThan(0);
    expect(liste.every((a) => a.estimated)).toBe(true);
    expect(liste.map((a) => a.id)).toEqual(expect.arrayContaining(['fond', 'autres']));
  });

  test('historique par heure', async () => {
    const h = await api.historique('2026-11-01T00:00:00Z', '2026-11-02T00:00:00Z', 'hour');
    expect(h.length).toBeGreaterThanOrEqual(23);
  });

  test('dispositifs, commande, programmation, absence, règle, alertes, push', async () => {
    const ids = (await api.dispositifs()).map((d) => d.id);
    expect(ids).toEqual(expect.arrayContaining(['meter', 'clim', 'prise-fer', 'prise-frigo']));
    await api.commander('prise-fer', { on: false });
    const prog = { slots: [{ at: '06:00', days: [0, 1, 2, 3, 4], action: { mode: 'off' as const } }] };
    expect(await api.programmer('clim', prog)).toEqual(prog);
    await api.absence(true);
    await api.regles(3);
    expect((await api.resume()).low_credit_days).toBe(3);
    expect(Array.isArray(await api.alertes())).toBe(true);
    await api.enregistrerPush('ExponentPushToken[integration]');
  });
});
