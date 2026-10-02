export type CategorySummary = {
  category_id: number;
  category_name: string;
  asset_count: number;
  total_cost: number;
  total_nbv: number;
};

export type Dashboard = {
  total_asset_cost: number;
  total_accumulated_depreciation: number;
  total_nbv: number;
  current_period_label: string;
  current_period_depreciation: number;
  category_summary: CategorySummary[];
};