export type DepreciationRecord = {
  id: number;
  asset_id: number;
  asset_code: string;
  asset_name: string;
  period_label: string;
  period_end_date: string;
  method: string;
  opening_nbv: number;
  depreciation: number;
  accumulated_depreciation: number;
  closing_nbv: number;
  months_charged_this_period: number;
  months_charged_cumulative: number;
  policy_source: string;
};

export type RunResult = {
  through_period: string;
  assets_processed: number;
  records_written: number;
};

export type PeriodSummary = {
  period_label: string;
  total_depreciation: number;
  record_count: number;
};