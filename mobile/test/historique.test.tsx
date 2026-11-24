import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import type { Resume } from '../src/api/types';
import { deps, fauxApi } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);
const NNBSP = ' ';

test('vue semaine : appel par jour et total de la période', async () => {
  const historique = jest.fn(async (_f: string, _t: string, step: string) =>
    step === 'day'
      ? [{ ts: '2026-11-20T00:00:00+00:00', kwh: 40.1 }, { ts: '2026-11-21T00:00:00+00:00', kwh: 44.1 }]
      : [{ ts: '2026-11-24T10:00:00+00:00', kwh: 1.2 }]);
  const resume = async () => ({ price_fcfa_kwh: 125 }) as Resume;
  await renderRouter(routesApp(deps(fauxApi({ historique, resume }))), { initialUrl: '/historique' });
  await screen.findByText('1,2 kWh · 150 F');
  await fireEvent.press(screen.getByRole('tab', { name: 'Semaine' }));
  await screen.findByText(`84,2 kWh · 10${NNBSP}525 F`);
  await waitFor(() => expect(historique).toHaveBeenLastCalledWith(
    '2026-11-18T00:00:00.000Z', '2026-11-24T15:00:00.000Z', 'day'));
});

test('toucher une barre affiche son détail', async () => {
  const historique = async () => [{ ts: '2026-11-24T10:00:00+00:00', kwh: 1.4 }];
  const resume = async () => ({ price_fcfa_kwh: 150 }) as Resume;
  await renderRouter(routesApp(deps(fauxApi({ historique, resume }))), { initialUrl: '/historique' });
  await fireEvent.press(await screen.findByLabelText('10 h : 1,4 kWh'));
  await screen.findByText('10 h : 1,4 kWh · 210 F');
});
