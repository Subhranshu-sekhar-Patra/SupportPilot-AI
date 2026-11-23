// SupportPilot AI — TypeScript Type Definitions

export type UserRole = "owner" | "admin" | "agent" | "viewer";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  organization: Organization;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type TicketStatus =
  | "open"
  | "assigned"
  | "in_progress"
  | "pending_review"
  | "escalated"
  | "resolved"
  | "closed";

export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type TicketChannel = "email" | "chat" | "api" | "webhook" | "portal";
export type MessageAuthorType = "customer" | "agent" | "ai" | "system";

export interface TicketMessage {
  id: string;
  author_type: MessageAuthorType;
  author_id: string | null;
  content: string;
  is_internal: boolean;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface Ticket {
  id: string;
  subject: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  channel: TicketChannel;
  customer_name: string | null;
  customer_email: string | null;
  ai_category: string | null;
  ai_suggested_response: string | null;
  ai_confidence_score: number | null;
  ai_quality_score: number | null;
  organization_id: string;
  assigned_to_id: string | null;
  created_at: string;
  updated_at: string;
  messages: TicketMessage[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  escalated_tickets: number;
  avg_quality_score: number | null;
  tickets_by_category: Record<string, number>;
  tickets_by_priority: Record<string, number>;
}

export interface APIError {
  success: false;
  error: { code: string; message: string };
}
