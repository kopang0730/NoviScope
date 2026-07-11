import { apiRequest } from "./client";
import type { User } from "./types";

export type RegisterPayload = {
  invite_code: string;
  email: string;
  display_name: string;
  password: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export function registerUser(payload: RegisterPayload) {
  return apiRequest<User>("/api/auth/register", {
    body: payload,
    method: "POST",
  });
}

export function loginUser(payload: LoginPayload) {
  return apiRequest<User>("/api/auth/login", {
    body: payload,
    method: "POST",
  });
}

export function logoutUser() {
  return apiRequest<null>("/api/auth/logout", {
    method: "POST",
  });
}

export function getCurrentUser() {
  return apiRequest<User | null>("/api/auth/session");
}
