import { dependancesReelles } from '../src/dependances';
import { Racine } from '../src/racine';

export default function Layout() {
  return <Racine deps={dependancesReelles} />;
}
