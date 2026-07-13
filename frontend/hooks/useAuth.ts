"use client";

import { useEffect } from "react";
import { getToken } from "@/lib/auth";
import { useAuthStore } from "@/store/authStore";

export function useAuth() {
  const {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    sendOtp,
    verifyOtp,
    logout,
    fetchUser,
  } = useAuthStore();

  useEffect(() => {
    const token = getToken();
    if (token && !user) {
      fetchUser();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    sendOtp,
    verifyOtp,
    logout,
    fetchUser,
  };
}
