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

const detailsSchema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Invalid email"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string().min(8, "Confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

const otpSchema = z.object({
  code: z.string().regex(/^\d{6}$/, "Enter the 6-digit code"),
});

type DetailsFormData = z.infer<typeof detailsSchema>;
type OtpFormData = z.infer<typeof otpSchema>;

export default function RegisterPage() {
  const { sendOtp, verifyOtp, isLoading } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<"details" | "otp">("details");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const detailsForm = useForm<DetailsFormData>({ resolver: zodResolver(detailsSchema) });
  const otpForm = useForm<OtpFormData>({ resolver: zodResolver(otpSchema) });

  useEffect(() => {
    if (getToken()) {
      router.replace("/dashboard");
    }
  }, [router]);

  const onSendOtp = async (data: DetailsFormData) => {
    try {
      const result = await sendOtp(data.email, "register");
      setName(data.name);
      setEmail(data.email);
      setPassword(data.password);
      setStep("otp");
      toast.success(result.message);
    } catch (error) {
      toast.error(
        getApiErrorMessage(error, "Registration failed. Email may already be in use.")
      );
    }
  };

  const onVerifyOtp = async (data: OtpFormData) => {
    try {
      await verifyOtp(email, data.code, "register", name, password);
      toast.success("Account created successfully!");
      router.push("/dashboard");
    } catch (error) {
      toast.error(getApiErrorMessage(error, "Invalid or expired code"));
    }
  };

  const onResend = async () => {
    try {
      const result = await sendOtp(email, "register");
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
            <CardTitle className="text-2xl font-semibold">Create account</CardTitle>
            <CardDescription>
              {step === "details"
                ? "Set your password — we will verify your email with a code"
                : `Enter the code sent to ${email}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === "details" ? (
              <form onSubmit={detailsForm.handleSubmit(onSendOtp)} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name</Label>
                  <Input id="name" placeholder="Jane Doe" {...detailsForm.register("name")} />
                  {detailsForm.formState.errors.name && (
                    <p className="text-xs text-destructive">
                      {detailsForm.formState.errors.name.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    {...detailsForm.register("email")}
                  />
                  {detailsForm.formState.errors.email && (
                    <p className="text-xs text-destructive">
                      {detailsForm.formState.errors.email.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    {...detailsForm.register("password")}
                  />
                  {detailsForm.formState.errors.password && (
                    <p className="text-xs text-destructive">
                      {detailsForm.formState.errors.password.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm Password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    {...detailsForm.register("confirmPassword")}
                  />
                  {detailsForm.formState.errors.confirmPassword && (
                    <p className="text-xs text-destructive">
                      {detailsForm.formState.errors.confirmPassword.message}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Send verification code
                </Button>
              </form>
            ) : (
              <form onSubmit={otpForm.handleSubmit(onVerifyOtp)} className="space-y-5">
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
                  Create account
                </Button>
                <div className="flex items-center justify-between text-sm">
                  <button
                    type="button"
                    className="text-muted-foreground underline-offset-4 hover:underline"
                    onClick={() => setStep("details")}
                  >
                    Change details
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
              Already have an account?{" "}
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
