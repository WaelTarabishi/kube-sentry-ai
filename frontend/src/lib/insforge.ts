import { createClient } from "@insforge/sdk";

export const isInsForgeConfigured = Boolean(
  process.env.NEXT_PUBLIC_INSFORGE_BASE_URL,
);

export const insforge = createClient({
  baseUrl:
    process.env.NEXT_PUBLIC_INSFORGE_BASE_URL ?? "http://localhost:7130",
  anonKey: process.env.NEXT_PUBLIC_INSFORGE_ANON_KEY,
});
