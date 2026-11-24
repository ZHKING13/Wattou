import { useRouter } from 'expo-router';
import { View } from 'react-native';
import type { Resume } from '../api/types';
import { useRessource } from '../donnees/useRessource';
import { date, depuis, fcfa, heure, jours, kwh } from '../format';
import { useApi, useDeps } from '../session/SessionContext';
import { espace, police, useCouleurs } from '../theme';
import { Bouton, Carte, Ecran, Texte, Titre } from '../ui/base';
import { EtatRessource } from '../ui/Etat';

const CAPTEUR_MUET_MS = 5 * 60_000;

function CarteCredit({ r }: { r: Resume }) {
  const c = useCouleurs();
  const router = useRouter();
  const bas = r.days_left !== null && r.days_left < r.low_credit_days;
  const ton = bas ? 'alerte' : undefined;
  return (
    <Carte testID="carte-credit" ton={ton}>
      {r.credit_kwh === null ? (
        <Texte>Saisissez le crédit affiché par votre compteur pour voir combien de jours il vous reste.</Texte>
      ) : r.days_left === null ? (
        <>
          <Texte doux>Crédit restant</Texte>
          {r.credit_fcfa !== null ? <Texte gras>{`≈ ${fcfa(r.credit_fcfa)} restants`}</Texte> : null}
          <Texte doux>Wattou calcule combien de jours il vous reste : il lui faut encore quelques heures de mesures.</Texte>
        </>
      ) : (
        <>
          <Texte doux>Crédit restant</Texte>
          <Texte gras taille={police.grand} couleur={bas ? c.alerte : c.texte}>{jours(r.days_left)}</Texte>
          {r.credit_fcfa !== null ? <Texte>{`≈ ${fcfa(r.credit_fcfa)} restants`}</Texte> : null}
          {r.depletion_at ? (
            <Texte doux>{`Épuisement prévu ${date(r.depletion_at)} vers ${heure(r.depletion_at).split(' h')[0]} h`}</Texte>
          ) : null}
        </>
      )}
      <Bouton titre="Saisir le crédit du compteur" onPress={() => router.push('/credit')} secondaire />
    </Carte>
  );
}

export function Accueil() {
  const api = useApi();
  const deps = useDeps();
  const c = useCouleurs();
  const ressource = useRessource<Resume>('resume', () => api.resume(), { intervalleMs: 60_000 });
  return (
    <Ecran testID="ecran-accueil" onRefresh={ressource.rafraichir}>
      <Titre>Wattou</Titre>
      <EtatRessource ressource={ressource}>
        {(r) => {
          // capteur muet = la dernière mesure est vieille *au moment où le serveur a répondu* ;
          // hors connexion, c'est le téléphone qui est coupé, pas le capteur.
          const reference = ressource.le ? new Date(ressource.le) : deps.maintenant();
          const muet = ressource.etat !== 'hors_ligne' && (!r.data_until
            || reference.getTime() - new Date(r.data_until).getTime() > CAPTEUR_MUET_MS);
          return (
            <View style={{ gap: espace.l }}>
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
              <Carte>
                <Texte>{`Aujourd’hui : ${fcfa(r.today_fcfa)} (${kwh(r.today_kwh)})`}</Texte>
                <Texte doux>{`Ce mois-ci : ≈ ${fcfa(r.month_forecast_fcfa)} prévus`}</Texte>
              </Carte>
              <Carte>
                <Texte>
                  {muet && r.data_until
                    ? `Dernière mesure : ${Math.round(r.power_w)} W (${heure(r.data_until)})`
                    : `En ce moment : ${Math.round(r.power_w)} W`}
                </Texte>
              </Carte>
            </View>
          );
        }}
      </EtatRessource>
    </Ecran>
  );
}
