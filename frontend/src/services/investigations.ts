import axios from "axios";

import { insforge } from "@/lib/insforge";
import { api } from "@/services/api";
import type {
  ClusterListResponse,
  InvestigationHistory,
  InvestigationResponse,
} from "@/types/investigation";

const INVESTIGATION_TIMEOUT_MS = 120_000;

export async function investigateCluster(
  accessToken: string,
  requestId: string,
  clusterContext: string,
): Promise<InvestigationResponse> {
  const response = await api.post<InvestigationResponse>(
    "/investigate",
    {
      request_id: requestId,
      namespace: "all",
      cluster_context: clusterContext,
    },
    {
      headers: { Authorization: `Bearer ${accessToken}` },
      timeout: INVESTIGATION_TIMEOUT_MS,
    },
  );

  if (!response.data?.diagnosis?.root_cause) {
    throw new Error("The investigation completed without a diagnosis.");
  }
  return response.data;
}

export async function getClusters(
  accessToken: string,
): Promise<ClusterListResponse> {
  const response = await api.get<ClusterListResponse>("/clusters", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
}

export async function getRecentInvestigations(
  userId: string,
): Promise<InvestigationHistory[]> {
  const { data, error } = await insforge.database
    .from("investigations")
    .select(
      "id,request_id,user_id,created_at,root_cause,namespace,cluster_context,confidence,status,progress_step,progress_state,error_message",
    )
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(8);

  if (error) {
    throw error;
  }
  return (data ?? []) as InvestigationHistory[];
}

export function getInvestigationError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNABORTED") {
      return "The investigation timed out. Check the cluster connection and try again.";
    }
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (isApiErrorDetail(detail)) {
      const checklist = detail.guidance.length
        ? `\n\nPlease verify:\n${detail.guidance.map((item) => `- ${item}`).join("\n")}`
        : "";
      return `${detail.message}${checklist}`;
    }
    if (error.response?.status === 401) {
      return "Your session is invalid or expired. Please sign in again.";
    }
    if (!error.response) {
      return "The API is unreachable. Confirm the FastAPI service is running.";
    }
    if (error.response.status >= 500) {
      return "The backend could not complete the investigation. Check the backend logs and try again.";
    }
  }
  return error instanceof Error
    ? error.message
    : "The investigation could not be completed.";
}

interface ApiErrorDetail {
  message: string;
  guidance: string[];
}

function isApiErrorDetail(value: unknown): value is ApiErrorDetail {
  if (!value || typeof value !== "object") return false;
  const detail = value as Record<string, unknown>;
  return (
    typeof detail.message === "string" &&
    Array.isArray(detail.guidance) &&
    detail.guidance.every((item) => typeof item === "string")
  );
}
