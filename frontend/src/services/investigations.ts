import axios from "axios";

import { insforge } from "@/lib/insforge";
import { api } from "@/services/api";
import type {
  InvestigationHistory,
  InvestigationResponse,
} from "@/types/investigation";

const INVESTIGATION_TIMEOUT_MS = 120_000;

export async function investigateCluster(
  accessToken: string,
  requestId: string,
): Promise<InvestigationResponse> {
  const response = await api.post<InvestigationResponse>(
    "/investigate",
    { request_id: requestId, namespace: "all" },
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

export async function getRecentInvestigations(
  userId: string,
): Promise<InvestigationHistory[]> {
  const { data, error } = await insforge.database
    .from("investigations")
    .select(
      "id,request_id,user_id,created_at,root_cause,namespace,confidence,status,progress_step,progress_state,error_message",
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
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (!error.response) {
      return "The API is unreachable. Confirm the FastAPI service is running.";
    }
  }
  return error instanceof Error
    ? error.message
    : "The investigation could not be completed.";
}
