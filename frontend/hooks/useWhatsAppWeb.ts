"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  WhatsAppWebJob,
  WhatsAppWebQrResult,
  WhatsAppWebSettings,
  WhatsAppWebStartResult,
  WhatsAppWebStatus,
} from "@/lib/types";

const STATUS_KEY = ["whatsapp-web", "status"] as const;
const SETTINGS_KEY = ["whatsapp-web", "settings"] as const;
const JOBS_KEY = ["whatsapp-web", "jobs"] as const;

export function useWhatsAppWebStatus(pollMs = 4000) {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: async () => {
      const { data } = await api.get<WhatsAppWebStatus>("/whatsapp-web/status");
      return data;
    },
    refetchInterval: (query) => {
      const s = query.state.data;
      if (!s?.enabled) return false;
      // Poll faster while waiting for QR scan
      if (s.browser_started && !s.logged_in) return 2500;
      return pollMs;
    },
    retry: 1,
  });
}

export function useWhatsAppWebSettings() {
  return useQuery({
    queryKey: SETTINGS_KEY,
    queryFn: async () => {
      const { data } = await api.get<WhatsAppWebSettings>("/whatsapp-web/settings");
      return data;
    },
    retry: false,
  });
}

export function useWhatsAppWebJobs(limit = 20, enabled = true) {
  return useQuery({
    queryKey: [...JOBS_KEY, limit],
    queryFn: async () => {
      const { data } = await api.get<WhatsAppWebJob[]>("/whatsapp-web/jobs", {
        params: { limit },
      });
      return data;
    },
    enabled,
    refetchInterval: enabled ? 8000 : false,
    retry: false,
  });
}

export function useWhatsAppWebStart() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<WhatsAppWebStartResult>("/whatsapp-web/start", null, {
        timeout: 120_000,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
      qc.invalidateQueries({ queryKey: SETTINGS_KEY });
      qc.invalidateQueries({ queryKey: JOBS_KEY });
    },
  });
}

export function useWhatsAppWebStop() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<WhatsAppWebStartResult>("/whatsapp-web/stop");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useWhatsAppWebRefreshQr() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.get<WhatsAppWebQrResult>("/whatsapp-web/qr", {
        timeout: 120_000,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useWhatsAppWebUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<WhatsAppWebSettings>) => {
      const { data } = await api.put<WhatsAppWebSettings>("/whatsapp-web/settings", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SETTINGS_KEY });
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useWhatsAppWebReset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<WhatsAppWebStartResult>("/whatsapp-web/reset");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
      qc.invalidateQueries({ queryKey: JOBS_KEY });
    },
  });
}

export function useWhatsAppWebPairCode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (phone: string) => {
      const { data } = await api.post<{
        ok: boolean;
        logged_in: boolean;
        pair_code?: string | null;
        phone?: string | null;
        message?: string | null;
      }>("/whatsapp-web/pair-code", { phone });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useWhatsAppWebReadPairCode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{
        ok: boolean;
        logged_in: boolean;
        pair_code?: string | null;
        phone?: string | null;
        message?: string | null;
      }>("/whatsapp-web/pair-code/read");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useWhatsAppWebLaunchChrome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{
        ok: boolean;
        cdp_url?: string | null;
        message?: string | null;
        logged_in?: boolean;
        attached?: boolean;
        worker_running?: boolean;
      }>("/whatsapp-web/launch-chrome", null, { timeout: 120_000 });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: STATUS_KEY });
      qc.invalidateQueries({ queryKey: JOBS_KEY });
    },
  });
}
