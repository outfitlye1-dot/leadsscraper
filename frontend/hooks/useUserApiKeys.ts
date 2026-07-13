import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  ApiProvider,
  UserApiKey,
  UserApiKeyBulkCreateResponse,
} from "@/lib/types";

export function useUserApiKeys(provider?: ApiProvider) {
  return useQuery({
    queryKey: ["user-api-keys", provider ?? "all"],
    queryFn: async () => {
      const params = provider ? { provider } : undefined;
      const { data } = await api.get<UserApiKey[]>("/user-keys", { params });
      return data;
    },
  });
}

export function useCreateUserApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      provider: ApiProvider;
      api_key: string;
      label?: string;
    }) => {
      const { data } = await api.post<UserApiKey>("/user-keys", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-api-keys"] });
    },
  });
}

export function useBulkCreateUserApiKeys() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      provider: ApiProvider;
      api_keys: string[];
      label_prefix?: string;
    }) => {
      const { data } = await api.post<UserApiKeyBulkCreateResponse>(
        "/user-keys/bulk",
        payload
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-api-keys"] });
    },
  });
}

export function useUpdateUserApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...payload
    }: {
      id: number;
      label?: string;
      priority?: number;
      status?: "active" | "exhausted" | "disabled";
    }) => {
      const { data } = await api.put<UserApiKey>(`/user-keys/${id}`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-api-keys"] });
    },
  });
}

export function useDeleteUserApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/user-keys/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-api-keys"] });
    },
  });
}

export function useResetExhaustedApiKeys() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (provider?: ApiProvider) => {
      const params = provider ? { provider } : undefined;
      const { data } = await api.post<{ reset_count: number }>(
        "/user-keys/reset-exhausted",
        null,
        { params }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-api-keys"] });
    },
  });
}
