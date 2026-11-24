import { useRouter } from 'expo-router';
import { Pressable, View } from 'react-native';
import type { Appareil, PointHistorique, Resume } from '../api/types';
import { comparerAHier, conseilDuJour } from '../conseils';
import { useRessource } from '../donnees/useRessource';
import { date, depuis, fcfa, heure, jours, kwh } from '../format';
import { useApi, useDeps } from '../session/SessionContext';
import { espace, police, rayon, useCouleurs } from '../theme';
import { Ampoule } from '../ui/Ampoule';
import { Bouton, Carte, Ecran, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';
import { nomAppareil } from './Appareils';

const CAPTEUR_MUET_MS = 5 * 60_000;

function Pastille({ texte, fond, couleur }: { texte: string; fond: string; couleur: string }) {
  return (
    <View style={{ alignSelf: 'flex-start', backgroundColor: fond, borderRadius: rayon.s, paddingHorizontal: espace.m,
                   paddingVertical: espace.xs }}>
      <Texte gras taille={police.petit} couleur={couleur}>{texte}</Texte>
    </View>
  );
}

/** La grande carte bleu nuit de la maquette : combien de jours tient le crédit. */
function CarteCredit({ r }: { r: Resume }) {
  const c = useCouleurs();
  const router = useRouter();
  const bas = r.days_left !== null && r.days_left < r.low_credit_days;
  return (
    <Carte testID="carte-credit" ton="fort" style={{ gap: espace.s, padding: espace.xl }}>
      {r.credit_kwh === null ? (
        <Texte couleur={c.surFort}>Saisissez le crédit affiché par votre compteur pour voir combien de jours il vous reste.</Texte>
      ) : (
        <>
          <Texte couleur={c.surFortDoux}>Votre crédit tient encore</Texte>
          {r.days_left !== null ? (
            <Texte taille={police.grand} couleur={c.accentSurFort}>{jours(r.days_left)}</Texte>
          ) : null}
          {r.credit_fcfa !== null ? <Texte gras couleur={c.surFort}>{`≈ ${fcfa(r.credit_fcfa)} restants`}</Texte> : null}
          {r.days_left === null ? (
            <Texte couleur={c.surFortDoux}>Wattou calcule combien de jours il vous reste : il lui faut encore quelques heures de mesures.</Texte>
          ) : null}
          {r.depletion_at ? (
            <Texte couleur={c.surFortDoux}>{`Épuisement prévu ${date(r.depletion_at)} vers ${heure(r.depletion_at).split(' h')[0]} h`}</Texte>
          ) : null}
          {bas ? <Pastille texte="Crédit bas : pensez à recharger" fond={c.accentSurFort} couleur={c.fort} /> : null}
        </>
      )}
      <View style={{ marginTop: espace.s }}>
        <Bouton titre="Saisir le crédit du compteur" onPress={() => router.push('/credit')} secondaire surFort />
      </View>
    </Carte>
  );
}

function Conseil({ texte }: { texte: string }) {
  const c = useCouleurs();
  return (
    <Carte ton="accent" style={{ flexDirection: 'row', alignItems: 'flex-start', gap: espace.m }}>
      <Ampoule taille={44} fond={c.surFort} ampoule={c.accentVif} />
      <View style={{ flex: 1, gap: espace.xs }}>
        <Texte taille={police.petit} couleur={c.surAccent}>Conseil du jour</Texte>
        <Texte gras couleur={c.surAccent}>{texte}</Texte>
      </View>
    </Carte>
  );
}

function Aujourdhui({ r, comparaison }: { r: Resume; comparaison: { ecart: number; texte: string } | null }) {
  const c = useCouleurs();
  return (
    <Carte style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: espace.m }}>
      <View style={{ flex: 1, gap: espace.xs }}>
        <Texte doux>Aujourd’hui</Texte>
        <Texte taille={police.moyen}>{fcfa(r.today_fcfa)}</Texte>
        <Texte doux taille={police.petit}>{`${kwh(r.today_kwh)} · ce mois-ci ≈ ${fcfa(r.month_forecast_fcfa)} prévus`}</Texte>
      </View>
      {comparaison ? (
        <Pastille texte={comparaison.texte}
                  fond={comparaison.ecart <= 0 ? c.succesFond : c.alerteFond}
                  couleur={comparaison.ecart <= 0 ? c.surSuccesFond : c.surAlerteFond} />
      ) : null}
    </Carte>
  );
}

function QuiMange({ liste }: { liste: Appareil[] }) {
  const c = useCouleurs();
  const router = useRouter();
  const top = liste.filter((a) => a.id !== 'fond' && a.id !== 'autres' && a.fcfa > 0)
    .sort((x, y) => y.fcfa - x.fcfa).slice(0, 3);
  if (top.length === 0) return null;
  return (
    <Carte style={{ gap: espace.m }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Texte gras>Qui mange votre crédit ?</Texte>
        <Pressable accessibilityRole="button" accessibilityLabel="Voir tous les appareils" onPress={() => router.push('/appareils')}
                   style={{ minHeight: 44, justifyContent: 'center' }}>
          <Texte couleur={c.accentTexte}>Tout voir</Texte>
        </Pressable>
      </View>
      {top.map((a) => (
        <View key={a.id} style={{ gap: espace.xs }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <Texte>{nomAppareil(a)}</Texte>
            <Texte gras>{`${Math.round(a.share * 100)} %`}</Texte>
          </View>
          <View style={{ height: 10, borderRadius: 5, backgroundColor: c.bordure }}>
            <View style={{ height: 10, borderRadius: 5, width: `${Math.round(a.share * 100)}%`, backgroundColor: c.accentVif }} />
          </View>
        </View>
      ))}
      <Texte doux taille={police.petit}>Estimation sur les 7 derniers jours</Texte>
    </Carte>
  );
}

export function Accueil() {
  const api = useApi();
  const deps = useDeps();
  const c = useCouleurs();
  const maintenant = deps.maintenant();
  const ressource = useRessource<Resume>('resume', () => api.resume(), { intervalleMs: 60_000 });
  const semaine = useRessource<Appareil[]>('appareils:week', () => api.appareils('week'));
  const hier = useRessource<PointHistorique[]>('accueil:hier', () => {
    const minuitHier = new Date(Date.UTC(maintenant.getUTCFullYear(), maintenant.getUTCMonth(), maintenant.getUTCDate() - 1));
    return api.historique(minuitHier.toISOString(), maintenant.toISOString(), 'hour');
  });
  const conseil = semaine.donnees ? conseilDuJour(semaine.donnees) : null;
  const comparaison = hier.donnees ? comparerAHier(hier.donnees, maintenant) : null;
  const rafraichirTout = async () => {
    await Promise.all([ressource.rafraichir(), semaine.rafraichir(), hier.rafraichir()]);
  };

  return (
    <Ecran testID="ecran-accueil" onRefresh={rafraichirTout}>
      <EtatRessource ressource={ressource}>
        {(r) => {
          // capteur muet = la dernière mesure est vieille *au moment où le serveur a répondu* ;
          // hors connexion, c'est le téléphone qui est coupé, pas le capteur.
          const reference = ressource.le ? new Date(ressource.le) : deps.maintenant();
          const muet = ressource.etat !== 'hors_ligne' && (!r.data_until
            || reference.getTime() - new Date(r.data_until).getTime() > CAPTEUR_MUET_MS);
          return (
            <View style={{ gap: espace.l }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <View style={{ flex: 1 }}>
                  <Texte doux>{maintenant.getUTCHours() >= 18 || maintenant.getUTCHours() < 4 ? 'Bonsoir' : 'Bonjour'}</Texte>
                  <Titre>{r.foyer_name}</Titre>
                </View>
                <Ampoule taille={44} />
              </View>
              {muet ? (
                <Carte ton="alerte">
                  <Texte couleur={c.alerte}>
                    {r.data_until
                      ? `Le capteur n’envoie plus de mesures depuis ${depuis(r.data_until, deps.maintenant())}. Vérifiez qu’il est branché.`
                      : 'Le capteur n’a encore envoyé aucune mesure. Vérifiez qu’il est branché.'}
                  </Texte>
                </Carte>
              ) : null}
              <CarteCredit r={r} />
              {conseil ? <Conseil texte={conseil} /> : null}
              <Aujourdhui r={r} comparaison={comparaison} />
              {semaine.donnees ? <QuiMange liste={semaine.donnees} /> : null}
              <Texte doux>
                {muet && r.data_until
                  ? `Dernière mesure : ${Math.round(r.power_w)} W (${heure(r.data_until)})`
                  : `En ce moment : ${Math.round(r.power_w)} W`}
              </Texte>
            </View>
          );
        }}
      </EtatRessource>
    </Ecran>
  );
}
