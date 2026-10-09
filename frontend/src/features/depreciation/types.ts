export type DepreciationRecord = {
  id: number;
  asset_id: number;
  asset_code: string;
  asset_name: string;
  period_label: string;       // "YYYY-MM"
  period_end_date: string;
  method: string;
  opening_nbv: number;
  depreciation: number;
  accumulated_depreciation: number;
  closing_nbv: number;
  // v3.0 proration + cap tracking
  days_in_month: number;
  eligible_days: number;
  is_first_month: boolean;
  capped: boolean;
  policy_source: string;
};

export type RunResult = {
  through_period: string;     // "YYYY-MM"
  assets_processed: number;
  records_written: number;
};

export type PeriodSummary = {
  period_label: string;
  total_depreciation: number;
  record_count: number;
};