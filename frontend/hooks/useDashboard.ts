import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { DashboardStats } from "@/lib/types";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>("/dashboard/stats");
      return data;
    },
  });
}
