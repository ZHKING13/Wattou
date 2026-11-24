import { fireEvent, renderRouter, screen, waitFor } from 'expo-router/testing-library';
import { NonAutorise, Refuse } from '../src/api/erreurs';
import { deps, fauxApi, stockageMemoire } from './fakes';
import { routesApp } from './routes';

jest.setTimeout(30_000);

test('inscription réussie : jeton stocké et Accueil affiché', async () => {
  const stockage = stockageMemoire(null);
  const inscrire = jest.fn(async () => ({ token: 't1', foyer_id: 'f1' }));
  await renderRouter(routesApp(deps(fauxApi({ inscrire }), stockage)), { initialUrl: '/inscription' });
  await fireEvent.changeText(await screen.findByLabelText('Numéro de téléphone'), '07 00 00 00 01');
  await fireEvent.changeText(screen.getByLabelText('Mot de passe'), 'secret1');
  await fireEvent.changeText(screen.getByLabelText('Nom du foyer'), 'Chez nous');
  await fireEvent.press(screen.getByText('Créer mon compte'));
  await screen.findByTestId('ecran-accueil');
  expect(inscrire).toHaveBeenCalledWith('+2250700000001', 'secret1', 'Chez nous');
  expect(stockage.valeur).toEqual({ token: 't1', foyer_id: 'f1' });
});

test('connexion refusée (401) : message affiché, reste sur la connexion', async () => {
  const connecter = jest.fn(async () => { throw new NonAutorise('x'); });
  await renderRouter(routesApp(deps(fauxApi({ connecter }), stockageMemoire(null))), { initialUrl: '/connexion' });
  await fireEvent.changeText(await screen.findByLabelText('Numéro de téléphone'), '0700000001');
  await fireEvent.changeText(screen.getByLabelText('Mot de passe'), 'mauvais');
  await fireEvent.press(screen.getByText('Se connecter'));
  await screen.findByText('Numéro ou mot de passe incorrect.');
  expect(screen.queryByTestId('ecran-accueil')).toBeNull();
});

test('numéro déjà inscrit (409) : message du serveur', async () => {
  const inscrire = jest.fn(async () => { throw new Refuse(409, 'Ce numéro a déjà un compte.'); });
  await renderRouter(routesApp(deps(fauxApi({ inscrire }), stockageMemoire(null))), { initialUrl: '/inscription' });
  await fireEvent.changeText(await screen.findByLabelText('Numéro de téléphone'), '0700000001');
  await fireEvent.changeText(screen.getByLabelText('Mot de passe'), 'secret1');
  await fireEvent.changeText(screen.getByLabelText('Nom du foyer'), 'X');
  await fireEvent.press(screen.getByText('Créer mon compte'));
  await screen.findByText('Ce numéro a déjà un compte.');
});

test('mot de passe trop court : bouton désactivé', async () => {
  await renderRouter(routesApp(deps(fauxApi(), stockageMemoire(null))), { initialUrl: '/connexion' });
  await fireEvent.changeText(await screen.findByLabelText('Numéro de téléphone'), '0700000001');
  await fireEvent.changeText(screen.getByLabelText('Mot de passe'), '12345');
  expect(screen.getByRole('button', { name: 'Se connecter' })).toBeDisabled();
});

test('jeton stocké : directement sur l\'Accueil', async () => {
  await renderRouter(routesApp(deps(fauxApi())), { initialUrl: '/' });
  await screen.findByTestId('ecran-accueil');
});

test('sans jeton : redirigé vers la connexion', async () => {
  await renderRouter(routesApp(deps(fauxApi(), stockageMemoire(null))), { initialUrl: '/' });
  await screen.findByText('Se connecter');
});

test('session expirée pendant l\'usage : retour à la connexion, jeton effacé', async () => {
  const stockage = stockageMemoire({ token: 'vieux', foyer_id: 'f1' });
  const { useApi } = require('../src/session/SessionContext');
  const Sonde = () => {
    const api = useApi();
    return <Bouton onPress={() => { api.resume().catch(() => {}); }} />;
  };
  const { Pressable, Text } = require('react-native');
  function Bouton({ onPress }: { onPress: () => void }) {
    return <Pressable onPress={onPress}><Text>Appeler</Text></Pressable>;
  }
  const routes = routesApp(deps(fauxApi({ resume: async () => { throw new NonAutorise(); } }), stockage));
  await renderRouter({ ...routes, '(onglets)/index': Sonde }, { initialUrl: '/' });
  await fireEvent.press(await screen.findByText('Appeler'));
  await screen.findByText('Se connecter');
  await waitFor(() => expect(stockage.valeur).toBeNull());
});

test('stockage sécurisé en panne : écran de connexion, pas d\'écran blanc', async () => {
  const stockage = stockageMemoire(null);
  stockage.lire = async () => { throw new Error('keystore'); };
  await renderRouter(routesApp(deps(fauxApi(), stockage)), { initialUrl: '/' });
  await screen.findByText('Se connecter');
});

test('chaque onglet a une icône', async () => {
  const { Icone } = require('../src/ui/icones');
  const { render } = require('@testing-library/react-native');
  for (const nom of ['accueil', 'appareils', 'historique', 'controle', 'alertes']) {
    const r = await render(<Icone nom={nom} couleur="#000" />);
    expect(JSON.stringify(r.toJSON()).length).toBeGreaterThan(100);
  }
});
