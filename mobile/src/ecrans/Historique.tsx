import { useState } from 'react';
import type { PointHistorique, Resume } from '../api/types';
import { useRessource } from '../donnees/useRessource';
import { fcfa, kwh } from '../format';
import { Barres } from '../graphique/Barres';
import { completer, fenetre, type Vue } from '../graphique/echelle';
import { useApi, useDeps } from '../session/SessionContext';
import { police, useCouleurs } from '../theme';
import { Carte, Ecran, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';
import { Segments } from '../ui/Segments';

const TITRES = { jour: 'Aujourd’hui', semaine: 'Ces 7 jours', mois: 'Ces 30 jours' } as const;

export function Historique() {
  const c = useCouleurs();
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
            <>
              <Carte ton="fort">
                <Texte couleur={c.surFortDoux}>{TITRES[vue]}</Texte>
                <Texte taille={police.titre} couleur={c.accentSurFort}>{fcfa(total * prix)}</Texte>
                <Texte couleur={c.surFort}>{`${kwh(total)} · ${fcfa(total * prix)}`}</Texte>
              </Carte>
              <Carte>
                <Barres points={completer(pts, f)} step={f.step} prix={prix} />
              </Carte>
            </>
          );
        }}
      </EtatRessource>
    </Ecran>
  );
}
