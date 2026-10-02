export type Disposal = {
  id: number;
  asset_id: number;
  asset_code: string;
  asset_name: string;
  disposal_date: string;
  proceeds: number;
  reason: string | null;
  nbv_at_disposal: number;
  gain_loss: number;
  method_used: string;
  period_label_used: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  requested_by: number;
  approved_by: number | null;
  approved_at: string | null;
  created_at: string;
};

export type DisposalCreate = {
  asset_id: number;
  disposal_date: string;
  proceeds: number;
  reason?: string | null;
};