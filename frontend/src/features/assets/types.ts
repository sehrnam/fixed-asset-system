export type Asset = {
  id: number;
  asset_code: string;
  name: string;
  category_id: number;
  category_name: string | null;
  cost: number;
  acquisition_date: string;
  useful_life_years: number;
  depreciation_method: "straight_line" | "reducing_balance";
  residual_value: number;
  rate: number | null;
  description: string | null;
  location: string | null;
  status: "ACTIVE" | "DISPOSED" | "RETIRED";
  created_at: string;
  updated_at: string;
};

export type Category = {
  id: number;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AssetInput = {
  asset_code?: string | null;
  name: string;
  category_id: number;
  cost: number;
  acquisition_date: string;
  useful_life_years: number;
  depreciation_method: "straight_line" | "reducing_balance";
  residual_value: number;
  rate?: number | null;
  description?: string | null;
  location?: string | null;
};