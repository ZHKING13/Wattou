import { useIsFocused } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ErreurServeur, HorsLigne } from '../api/erreurs';
import { useDeps, useSession } from '../session/SessionContext';

export type EtatChargement = 'chargement' | 'pret' | 'hors_ligne' | 'erreur';

export type Ressource<T> = {
  donnees: T | null;
  etat: EtatChargement;
  le: string | null; // date des données affichées
  erreur: string | null;
  rafraichir(): Promise<void>;
};

/** Charge une donnée du serveur : cache d'abord, puis réseau ; garde le cache si le réseau manque. */
export function useRessource<T>(cle: string, charger: () => Promise<T>,
                                options: { intervalleMs?: number } = {}): Ressource<T> {
  const deps = useDeps();
  const { foyerId } = useSession();
  const focus = useIsFocused();
  const cleCache = `${foyerId ?? 'anonyme'}:${cle}`;
  const [donnees, setDonnees] = useState<T | null>(null);
  const [etat, setEtat] = useState<EtatChargement>('chargement');
  const [le, setLe] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const aDesDonnees = useRef(false);
  const recu = useRef(false);
  const chargerRef = useRef(charger);
  chargerRef.current = charger;

  const rafraichir = useCallback(async () => {
    try {
      const v = await chargerRef.current();
      const maintenant = deps.maintenant().toISOString();
      recu.current = true;
      aDesDonnees.current = true;
      setDonnees(v);
      setLe(maintenant);
      setErreur(null);
      setEtat('pret');
      await deps.cache.ecrire(cleCache, v, maintenant);
    } catch (e) {
      const reseau = e instanceof HorsLigne || e instanceof ErreurServeur;
      setErreur(e instanceof Error ? e.message : 'Une erreur est survenue.');
      setEtat(reseau && aDesDonnees.current ? 'hors_ligne' : 'erreur');
    }
  }, [deps, cleCache]);

  useEffect(() => {
    let actif = true;
    (async () => {
      const c = await deps.cache.lire<T>(cleCache);
      if (actif && c && !recu.current) {
        aDesDonnees.current = true;
        setDonnees(c.valeur);
        setLe(c.le);
      }
      if (actif) await rafraichir();
    })();
    return () => {
      actif = false;
    };
  }, [deps, cleCache, rafraichir]);

  useEffect(() => {
    if (!options.intervalleMs || !focus) return;
    const id = setInterval(() => void rafraichir(), options.intervalleMs);
    return () => clearInterval(id);
  }, [options.intervalleMs, focus, rafraichir]);

  return { donnees, etat, le, erreur, rafraichir };
}
