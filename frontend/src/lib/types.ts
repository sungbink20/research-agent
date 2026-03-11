/**
 * TypeScript types mirroring the backend Pydantic schemas.
 *
 * These are manually kept in sync with backend/app/schemas.py.
 * For a larger project, we'd generate these from an OpenAPI spec.
 * For MVP, manual sync is fine -- it's one file and changes rarely.
 */

export interface Source {
  title: string;
  url: string | null;
  snippet: string | null;
  source_type: string;
}

export interface InvestmentMemo {
  company_name: string;
  website: string | null;
  category: string;
  summary: string;
  product: string;
  customer: string;
  business_model: string;
  traction_signals: string[];
  competitors: string[];
  bull_case: string[];
  bear_case: string[];
  risks: string[];
  open_questions: string[];
  sources: Source[];
}

export interface MemoResponse {
  id: string;
  memo: InvestmentMemo;
  generated_at: string;
}

export interface MemoRecord {
  id: string;
  query: string;
  context: string | null;
  memo: InvestmentMemo;
  feedback: string | null;
  rating: number | null;
  created_at: string;
  updated_at: string;
}

export interface MemoListItem {
  id: string;
  query: string;
  company_name: string;
  category: string;
  created_at: string;
}

export interface FeedbackRequest {
  rating?: number;
  feedback?: string;
}
