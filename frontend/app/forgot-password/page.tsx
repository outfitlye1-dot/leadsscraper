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
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const emailSchema = z.object({
  email: z.string().email("Invalid email"),
});

const resetSchema = z
  .object({
    code: z.string().regex(/^\d{6}$/, "Enter the 6-digit code"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string().min(8, "Confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type EmailFormData = z.infer<typeof emailSchema>;
type ResetFormData = z.infer<typeof resetSchema>;

export default function ForgotPasswordPage() {
  const { sendOtp, verifyOtp, isLoading } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<"email" | "reset">("email");
  const [email, setEmail] = useState("");

  const emailForm = useForm<EmailFormData>({ resolver: zodResolver(emailSchema) });
  const resetForm = useForm<ResetFormData>({ resolver: zodResolver(resetSchema) });

  useEffect(() => {
    if (getToken()) {
      router.replace("/dashboard");
    }
  }, [router]);

  const onSendOtp = async (data: EmailFormData) => {
    try {
      const result = await sendOtp(data.email, "reset_password");
      setEmail(data.email);
      setStep("reset");
      toast.success(result.message);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "No account found with this email."));
    }
  };

  const onReset = async (data: ResetFormData) => {
    try {
      await verifyOtp(email, data.code, "reset_password", undefined, data.password);
      toast.success("Password updated. You are now signed in.");
      router.push("/dashboard");
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Invalid code or password could not be updated."));
    }
  };

  const onResend = async () => {
    try {
      const result = await sendOtp(email, "reset_password");
      toast.success(result.message);
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Please wait before requesting another code"));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
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
            <CardTitle className="text-2xl font-semibold">Forgot password</CardTitle>
            <CardDescription>
              {step === "email"
                ? "We will email you a code to reset your password"
                : `Enter the code sent to ${email} and choose a new password`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === "email" ? (
              <form onSubmit={emailForm.handleSubmit(onSendOtp)} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    {...emailForm.register("email")}
                  />
                  {emailForm.formState.errors.email && (
                    <p className="text-xs text-destructive">
                      {emailForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Send reset code
                </Button>
              </form>
            ) : (
              <form onSubmit={resetForm.handleSubmit(onReset)} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="code">Verification code</Label>
                  <Input
                    id="code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="123456"
                    maxLength={6}
                    {...resetForm.register("code")}
                  />
                  {resetForm.formState.errors.code && (
                    <p className="text-xs text-destructive">
                      {resetForm.formState.errors.code.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">New password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    {...resetForm.register("password")}
                  />
                  {resetForm.formState.errors.password && (
                    <p className="text-xs text-destructive">
                      {resetForm.formState.errors.password.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm new password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    {...resetForm.register("confirmPassword")}
                  />
                  {resetForm.formState.errors.confirmPassword && (
                    <p className="text-xs text-destructive">
                      {resetForm.formState.errors.confirmPassword.message}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Reset password & sign in
                </Button>
                <div className="flex items-center justify-between text-sm">
                  <button
                    type="button"
                    className="text-muted-foreground underline-offset-4 hover:underline"
                    onClick={() => setStep("email")}
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
              Remember your password?{" "}
              <Link href="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
