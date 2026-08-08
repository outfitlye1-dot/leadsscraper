"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { getApiErrorMessage } from "@/lib/errors";
import { Zap } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { getToken } from "@/lib/auth";
import { getHomePathForRole } from "@/lib/authRedirect";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { GoogleAuthHandler } from "@/components/GoogleAuthHandler";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";

const passwordSchema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

const otpEmailSchema = z.object({
  email: z.string().email("Invalid email"),
});

const otpSchema = z.object({
  code: z.string().regex(/^\d{6}$/, "Enter the 6-digit code"),
});

type PasswordFormData = z.infer<typeof passwordSchema>;
type OtpEmailFormData = z.infer<typeof otpEmailSchema>;
type OtpFormData = z.infer<typeof otpSchema>;

type LoginMode = "password" | "otp-email" | "otp-code";

export default function LoginPage() {
  const { login, sendOtp, verifyOtp, isLoading } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<LoginMode>("password");
  const [email, setEmail] = useState("");
  const [otpDevMode, setOtpDevMode] = useState(false);

  const passwordForm = useForm<PasswordFormData>({ resolver: zodResolver(passwordSchema) });
  const otpEmailForm = useForm<OtpEmailFormData>({ resolver: zodResolver(otpEmailSchema) });
  const otpForm = useForm<OtpFormData>({ resolver: zodResolver(otpSchema) });

  useEffect(() => {
    const redirectIfLoggedIn = async () => {
      if (!getToken()) return;
      if (!useAuthStore.getState().user) {
        await useAuthStore.getState().fetchUser();
      }
      router.replace(getHomePathForRole(useAuthStore.getState().user?.role));
    };
    redirectIfLoggedIn();
  }, [router]);

  const onPasswordLogin = async (data: PasswordFormData) => {
    try {
      await login(data.email, data.password);
      const role = useAuthStore.getState().user?.role;
      toast.success(role === "admin" ? "Welcome, Admin!" : "Welcome back!");
      router.push(getHomePathForRole(role));
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Invalid email or password"));
    }
  };

  const onSendOtp = async (data: OtpEmailFormData) => {
    try {
      const result = await sendOtp(data.email, "login");
      setEmail(data.email);
      setOtpDevMode(result.message.toLowerCase().includes("dev mode"));
      setMode("otp-code");
      toast.success(result.message);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Could not send code. Register first or check email."));
    }
  };

  const onVerifyOtp = async (data: OtpFormData) => {
    try {
      await verifyOtp(email, data.code, "login");
      const role = useAuthStore.getState().user?.role;
      toast.success(role === "admin" ? "Welcome, Admin!" : "Welcome back!");
      router.push(getHomePathForRole(role));
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Invalid or expired code"));
    }
  };

  const onResend = async () => {
    try {
      const result = await sendOtp(email, "login");
      setOtpDevMode(result.message.toLowerCase().includes("dev mode"));
      toast.success(result.message);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Please wait before requesting another code"));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <GoogleAuthHandler />
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="mx-auto mb-5 flex h-11 w-11 items-center justify-center rounded-xl border border-border/80 bg-foreground">
            <Zap className="h-5 w-5 text-background" />
          </div>
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
            LeadGen AI
          </p>
        </div>

        <Card className="app-panel">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-semibold">Welcome back</CardTitle>
            <CardDescription>
              {mode === "password" && "Sign in with your email and password"}
              {mode === "otp-email" && "We will email you a one-time sign-in code"}
              {mode === "otp-code" && `Enter the code sent to ${email}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              <GoogleSignInButton />
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-border/60" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">or</span>
                </div>
              </div>
            </div>

            {mode === "password" && (
              <form onSubmit={passwordForm.handleSubmit(onPasswordLogin)} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    {...passwordForm.register("email")}
                  />
                  {passwordForm.formState.errors.email && (
                    <p className="text-xs text-destructive">
                      {passwordForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    <Link
                      href="/forgot-password"
                      className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                    >
                      Forgot password?
                    </Link>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    {...passwordForm.register("password")}
                  />
                  {passwordForm.formState.errors.password && (
                    <p className="text-xs text-destructive">
                      {passwordForm.formState.errors.password.message}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Sign in
                </Button>
                <button
                  type="button"
                  className="w-full text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
                  onClick={() => setMode("otp-email")}
                >
                  Sign in with email code instead
                </button>
              </form>
            )}

            {mode === "otp-email" && (
              <form onSubmit={otpEmailForm.handleSubmit(onSendOtp)} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="otp-email">Email</Label>
                  <Input
                    id="otp-email"
                    type="email"
                    placeholder="you@example.com"
                    {...otpEmailForm.register("email")}
                  />
                  {otpEmailForm.formState.errors.email && (
                    <p className="text-xs text-destructive">
                      {otpEmailForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Send code
                </Button>
                <button
                  type="button"
                  className="w-full text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
                  onClick={() => setMode("password")}
                >
                  Back to password login
                </button>
              </form>
            )}

            {mode === "otp-code" && (
              <form onSubmit={otpForm.handleSubmit(onVerifyOtp)} className="space-y-5">
                {otpDevMode ? (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
                    Email is not configured yet. The code is printed in the backend terminal only
                    (not sent to Gmail). Add a Gmail <strong>App Password</strong> to{" "}
                    <code className="rounded bg-background/60 px-1">SMTP_PASSWORD</code> in{" "}
                    <code className="rounded bg-background/60 px-1">.env</code> — OAuth client
                    secret does not send OTP emails.
                  </div>
                ) : null}
                <div className="space-y-2">
                  <Label htmlFor="code">Verification code</Label>
                  <Input
                    id="code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="123456"
                    maxLength={6}
                    {...otpForm.register("code")}
                  />
                  {otpForm.formState.errors.code && (
                    <p className="text-xs text-destructive">
                      {otpForm.formState.errors.code.message}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Sign in
                </Button>
                <div className="flex items-center justify-between text-sm">
                  <button
                    type="button"
                    className="text-muted-foreground underline-offset-4 hover:underline"
                    onClick={() => setMode("otp-email")}
                  >
                    Change email
                  </button>
                  <button
                    type="button"
                    className="font-medium text-foreground underline-offset-4 hover:underline"
                    onClick={onResend}
                    disabled={isLoading}
                  >
                    Resend code
                  </button>
                </div>
              </form>
            )}

            <p className="mt-6 text-center text-sm font-light text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="font-medium text-foreground underline-offset-4 hover:underline">
                Register
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
