import { apiRequest } from "./client";
import type { InviteCode } from "./types";

type InvitesResponse = {
  invites: InviteCode[];
};

export type CreateInvitePayload = {
  code: string;
  max_uses: number;
  expires_at?: string | null;
};

export async function getInvites() {
  const response = await apiRequest<InvitesResponse>("/api/admin/invites");
  return response.invites;
}

export function createInvite(payload: CreateInvitePayload) {
  return apiRequest<InviteCode>("/api/admin/invites", {
    body: payload,
    method: "POST",
  });
}
