// Contrat de l'API Wattou (/api/v1), phase 1a — champs identiques au serveur.

export type Jeton = { token: string; foyer_id: string };

export type Resume = {
  foyer_name: string;
  power_w: number;
  today_kwh: number;
  today_fcfa: number;
  price_fcfa_kwh: number;
  credit_kwh: number | null;
  credit_fcfa: number | null;
  days_left: number | null;
  depletion_at: string | null;
  month_forecast_fcfa: number;
  absence_mode: boolean;
  low_credit_days: number;
  data_until: string | null;
};

export type Periode = 'day' | 'week' | 'month';

export type Appareil = {
  id: string; // uuid, ou "fond" / "autres"
  label: string | null;
  power_w: number | null;
  kwh: number;
  fcfa: number;
  share: number;
  estimated: boolean;
  essential: boolean;
  device_id: string | null;
};

export type PointHistorique = { ts: string; kwh: number };

export type SaisieCredit =
  | { kind: 'reading'; kwh: number }
  | { kind: 'recharge'; kwh: number; amount_fcfa: number };

export type KindAlerte =
  | 'absence_load' | 'meter_gap' | 'night_unknown' | 'credit_low' | 'low_credit_rule'
  | 'peak' | 'stuck' | 'outage' | 'voltage';

export type Alerte = { id: number; ts: string; kind: KindAlerte; message: string; read: boolean };

export type ModeClim = 'off' | 'cool' | 'fan';
export type CommandePrise = { on: boolean };
export type CommandeClim = { mode?: ModeClim; setpoint_c?: number };
export type Creneau = { at: string; days: number[]; action: CommandePrise | CommandeClim };
export type Programmation = { slots: Creneau[] };

export type Dispositif = {
  id: string;
  kind: 'meter' | 'plug' | 'ir_ac';
  name: string;
  essential: boolean;
  last_state: { p_w?: number; on?: boolean; mode?: ModeClim; setpoint_c?: number; ts?: string };
  schedule: Programmation;
};
