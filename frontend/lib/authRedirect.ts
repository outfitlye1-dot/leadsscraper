export function getHomePathForRole(role?: string | null): "/admin" | "/dashboard" {
  return role === "admin" ? "/admin" : "/dashboard";
}
