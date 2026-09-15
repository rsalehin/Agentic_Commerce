export interface AuditEvent {
  session_id: string;
  seq: number;
  ts: string;
  actor: string;
  from_state: string;
  to_state: string;
  tool: string | null;
  reason_codes: string[];
  evidence_hash: string | null;
  hash: string;
}

export interface SessionSnapshot {
  session_id: string;
  state: string;
  blocked_from: string | null;
  reason_codes: string[];
  service_mode: string | null;
  audit_chain_ok: boolean;
  events: AuditEvent[];
}

export interface Escalation {
  id: string;
  session_id: string;
  queue: "customer" | "review";
  actor_role: "customer" | "adviser" | "compliance";
  reasons: string[];
  blocked_from: string | null;
  blocked_tool: string | null;
  confidential: boolean;
  status: "open" | "approved" | "appointment" | "rejected";
  note: string | null;
  decided_by: string | null;
}

export interface RuleInfo {
  id: string;
  step: string;
  outcome: string;
  reason_code: string | null;
  law: string;
  message_de: string | null;
}

export interface AgentCard {
  name: string;
  description?: string;
  provider: {
    organization: string;
    url: string;
    lei?: string;
    bafin_id?: string;
    custodian?: string;
  };
  signatures?: Array<{ protected: string; signature: string }>;
}
