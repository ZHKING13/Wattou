import { Slot } from 'expo-router';
import type { Dependances } from './dependances';
import { FournisseurApp } from './session/SessionContext';

export function Racine({ deps }: { deps: Dependances }) {
  return (
    <FournisseurApp deps={deps}>
      <Slot />
    </FournisseurApp>
  );
}
