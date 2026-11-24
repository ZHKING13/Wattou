import { useState } from 'react';
import type { PointHistorique, Resume } from '../api/types';
import { useRessource } from '../donnees/useRessource';
import { fcfa, kwh } from '../format';
import { Barres } from '../graphique/Barres';
import { completer, fenetre, type Vue } from '../graphique/echelle';
import { useApi, useDeps } from '../session/SessionContext';
import { Carte, Ecran, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';
import { Segments } from '../ui/Segments';

export function Historique() {
  const api = useApi();
  const deps = useDeps();
  const [vue, setVue] = useState<Vue>('jour');
  const f = fenetre(vue, deps.maintenant());
  const points = useRessource<PointHistorique[]>(`historique:${vue}`, () => api.historique(f.from, f.to, f.step));
  const resume = useRessource<Resume>('resume', () => api.resume());
  const prix = resume.donnees?.price_fcfa_kwh ?? 0;
  return (
    <Ecran testID="ecran-historique" onRefresh={points.rafraichir}>
      <Titre>Historique</Titre>
      <Segments items={[['jour', 'Jour'], ['semaine', 'Semaine'], ['mois', 'Mois']]} actif={vue} onChange={setVue} />
      <EtatRessource ressource={points}>
        {(pts) => {
          const total = pts.reduce((s, p) => s + p.kwh, 0);
          return (
            <Carte>
              <Texte gras>{`${kwh(total)} · ${fcfa(total * prix)}`}</Texte>
              <Barres points={completer(pts, f)} step={f.step} prix={prix} />
            </Carte>
          );
        }}
      </EtatRessource>
    </Ecran>
  );
}
