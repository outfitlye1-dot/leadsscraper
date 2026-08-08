import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { BrainGenerateResponse, BrainProfile } from "@/lib/types";

export type BrainUpdatePayload = {
  name?: string;
  skills?: string[];
  experience?: Record<string, string>[];
  education?: Record<string, string>[];
  projects?: Record<string, string>[];
  services?: string[];
  tools?: string[];
  technologies?: string[];
  professional_summary?: string;
  custom_notes?: string;
  system_prompt?: string;
  pricing_currency?: string;
  pricing_high?: number;
  pricing_floor?: number;
};

export function useBrain() {
  return useQuery({
    queryKey: ["brain"],
    queryFn: async () => {
      const { data } = await api.get<BrainProfile | null>("/brain");
      return data;
    },
  });
}

export function useUpdateBrain() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BrainUpdatePayload) => {
      const { data } = await api.put<BrainProfile>("/brain", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brain"] });
    },
  });
}

export function useImportCvToBrain() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<BrainProfile>("/brain/import-cv");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brain"] });
    },
  });
}

export function useGenerateBrain() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<BrainGenerateResponse>("/brain/generate");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brain"] });
    },
  });
}
