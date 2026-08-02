export type ProgressState = "pending" | "active" | "completed" | "failed";

export type ProgressStepId =
  | "checking_pods"
  | "reading_logs"
  | "analyzing_events"
  | "inspecting_deployments"
  | "checking_networking"
  | "ai_reasoning"
  | "root_cause_found";

export interface ProgressStep {
  id: ProgressStepId;
  label: string;
  state: ProgressState;
}

export interface Diagnosis {
  root_cause: string;
  explanation: string;
  fix: string;
  kubectl_commands: string[];
  prevention_recommendation: string;
  confidence: number;
  confidence_reasoning: string[];
}

export interface InvestigationResponse {
  status: "success";
  outcome: "issue_found" | "healthy";
  cluster_context: string;
  investigation: Record<string, unknown>;
  diagnosis: Diagnosis;
}

export interface KubernetesCluster {
  name: string;
  server: string;
  contexts: string[];
  selected_context: string;
  is_current: boolean;
}

export interface ClusterListResponse {
  clusters: KubernetesCluster[];
  current_context: string | null;
}

export interface InvestigationHistory {
  id: string;
  request_id: string;
  user_id: string;
  created_at: string;
  root_cause: string | null;
  namespace: string;
  cluster_context: string;
  confidence: number | null;
  status: "running" | "success" | "failed";
  progress_step: ProgressStepId | null;
  progress_state: ProgressState | null;
  error_message: string | null;
}

export const INITIAL_PROGRESS: ProgressStep[] = [
  { id: "checking_pods", label: "Checking Pods", state: "pending" },
  { id: "reading_logs", label: "Reading Logs", state: "pending" },
  { id: "analyzing_events", label: "Analyzing Events", state: "pending" },
  {
    id: "inspecting_deployments",
    label: "Inspecting Deployments",
    state: "pending",
  },
  {
    id: "checking_networking",
    label: "Checking Networking",
    state: "pending",
  },
  { id: "ai_reasoning", label: "AI Reasoning", state: "pending" },
  { id: "root_cause_found", label: "Root Cause Found", state: "pending" },
];
