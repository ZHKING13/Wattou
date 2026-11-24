import type { Dependances } from '../src/dependances';
import { Racine } from '../src/racine';

// Carte des routes de l'application pour renderRouter.
export function routesApp(deps: Dependances) {
  const ecran = (nom: string) => require(`../app/${nom}`);
  return {
    _layout: () => <Racine deps={deps} />,
    '(auth)/connexion': ecran('(auth)/connexion'),
    '(auth)/inscription': ecran('(auth)/inscription'),
    '(onglets)/_layout': ecran('(onglets)/_layout'),
    '(onglets)/index': ecran('(onglets)/index'),
    '(onglets)/appareils': ecran('(onglets)/appareils'),
    credit: ecran('credit'),
  };
}
