import { apiRequest } from "./client";
import type { AdminVersionInfo, PublicVersionInfo } from "./types";

export function getVersionInfo() {
  return apiRequest<PublicVersionInfo>("/api/version");
}

export function getAdminVersionInfo() {
  return apiRequest<AdminVersionInfo>("/api/admin/version");
}
