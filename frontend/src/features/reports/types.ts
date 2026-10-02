export type TableReport = {
  title: string;
  columns: string[];
  rows: string[][];
  totals: Record<string, number> | null;
};

export type AssetMovementRow = {
  category_id: number | null;
  category_name: string;
  opening_cost: number;
  additions: number;
  disposals: number;
  closing_cost: number;
  opening_accum: number;
  dep_charge: number;
  disposals_accum: number;
  closing_accum: number;
  closing_nbv: number;
};

export type AssetMovementReport = {
  period_label: string;
  rows: AssetMovementRow[];
  totals: AssetMovementRow;
};