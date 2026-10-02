export type SheetSummary = {
  id: number;
  name: string;
  order_index: number;
  kind: "SYSTEM" | "USER";
  system_view: "asset_register" | "depreciation" | "disposal" | null;
  is_dirty: boolean;
};

export type Workbook = {
  id: number;
  name: string;
  active_sheet_id: number | null;
  revision: number;
  sheets: SheetSummary[];
  created_at: string;
  updated_at: string;
};

export type Cell = {
  row: number;
  col: number;
  raw: string;
  computed: string | null;
  is_formula: boolean;
  error: string | null;
};

export type SheetRender = {
  sheet_id: number;
  sheet_name: string;
  sheet_kind: "SYSTEM" | "USER";
  grid: {
    kind: "grid";
    rows: number;
    cols: number;
    cells: Cell[];
  } | null;
  table: {
    kind: "table";
    title: string;
    columns: string[];
    rows: string[][];
  } | null;
};