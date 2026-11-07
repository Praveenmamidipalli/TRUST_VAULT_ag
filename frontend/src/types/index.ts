export type UserRole = 'ADMIN' | 'OWNER' | 'VIEWER';
export type PermissionLevel = 'READ' | 'EDIT';
export type DocumentCategory = 'FINANCIAL' | 'LEGAL' | 'HR' | 'TECHNICAL' | 'GENERAL';

export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: number;
  title: string;
  description?: string | null;
  file_name: string;
  file_size: number;
  mime_type: string;
  category: DocumentCategory;
  owner_id: number;
  extraction_status: string;
  is_classified: boolean;
  created_at: string;
  updated_at: string;
  owner?: User;
}

export interface DocumentPermission {
  id: number;
  document_id: number;
  user_id: number;
  permission_level: PermissionLevel;
  granted_by_id?: number | null;
  created_at: string;
  updated_at: string;
  user?: User;
}

export interface AuditEvent {
  id: number;
  actor_id?: number | null;
  document_id?: number | null;
  action: string;
  result: 'SUCCESS' | 'DENIED' | 'ERROR';
  timestamp: string;
  details?: string | null;
  previous_hash: string;
  current_hash: string;
  actor?: User;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AdminReport {
  users: {
    total: number;
    active: number;
    inactive: number;
    roles: Record<string, number>;
  };
  documents: {
    total_count: number;
    total_storage_bytes: number;
    total_storage_mb: number;
  };
  compliance: {
    total_audit_events: number;
    unauthorized_attempts: number;
    permission_grants: number;
    permission_revocations: number;
  };
  recent_security_alerts: Array<{
    id: number;
    actor_id?: number | null;
    document_id?: number | null;
    action: string;
    timestamp: string;
    details?: string | null;
  }>;
}
