export class HorsLigne extends Error {
  constructor() {
    super('Pas de connexion internet.');
    this.name = 'HorsLigne';
  }
}

export class NonAutorise extends Error {
  constructor(message = 'Votre session a expiré. Reconnectez-vous.') {
    super(message);
    this.name = 'NonAutorise';
  }
}

/** Requête refusée (4xx) : `message` est le texte du serveur, à montrer tel quel. */
export class Refuse extends Error {
  constructor(readonly statut: number, message: string) {
    super(message);
    this.name = 'Refuse';
  }
}

export class PilotageIndisponible extends Error {
  constructor() {
    super('Le pilotage est momentanément indisponible. Réessayez dans un instant.');
    this.name = 'PilotageIndisponible';
  }
}

export class ErreurServeur extends Error {
  constructor(readonly statut: number) {
    super('Le serveur Wattou ne répond pas correctement. Réessayez plus tard.');
    this.name = 'ErreurServeur';
  }
}
