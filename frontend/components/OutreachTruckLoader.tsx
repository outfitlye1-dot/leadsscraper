"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { TypewriterLoader } from "@/components/TypewriterLoader";

export type OutreachLoaderPhase = "loading" | "complete" | "error";

interface OutreachTruckLoaderProps {
  open: boolean;
  phase: OutreachLoaderPhase;
  companyName?: string | null;
  toEmail?: string;
  subject?: string;
  error?: string;
  onFinish: () => void;
  onRetry?: () => void;
}

const LOADING_STEPS = [
  "Gathering lead details…",
  "AI crafting outreach message…",
  "Typing personalized email…",
  "Sending to inbox…",
];

export function OutreachTruckLoader({
  open,
  phase,
  companyName,
  toEmail,
  subject,
  error,
  onFinish,
  onRetry,
}: OutreachTruckLoaderProps) {
  const [mounted, setMounted] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!open || phase !== "loading") return;
    setStepIndex(0);

    const stepTimer = setInterval(() => {
      setStepIndex((i) => (i + 1) % LOADING_STEPS.length);
    }, 1600);

    return () => clearInterval(stepTimer);
  }, [open, phase]);

  if (!mounted || !open) return null;

  const showFinish = phase === "complete";
  const showError = phase === "error";
  const isLoading = phase === "loading";

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[300] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-black/55 backdrop-blur-sm" />

          <motion.div
            className="relative w-full max-w-md overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
            initial={{ opacity: 0, scale: 0.92, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
          >
            <div className="border-b border-border bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 px-5 py-4 text-white">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-300">
                AI Email Outreach
              </p>
              <h3 className="mt-1 text-lg font-semibold">
                {showError
                  ? "Send failed"
                  : showFinish
                    ? "Email sent!"
                    : "Writing your message…"}
              </h3>
              {companyName && (
                <p className="mt-0.5 truncate text-sm text-slate-300">
                  {companyName}
                  {toEmail ? ` · ${toEmail}` : ""}
                </p>
              )}
            </div>

            <div className="px-5 py-6">
              {isLoading && <TypewriterLoader />}

              <div className="min-h-[72px] text-center">
                {showError ? (
                  <div className="flex flex-col items-center gap-2 text-destructive">
                    <XCircle className="h-8 w-8" />
                    <p className="text-sm font-medium">{error || "Could not send email"}</p>
                  </div>
                ) : showFinish ? (
                  <motion.div
                    className="flex flex-col items-center gap-2"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <CheckCircle2 className="h-9 w-9 text-emerald-500" />
                    <p className="text-sm font-medium text-foreground">Message sent successfully</p>
                    {subject && (
                      <p className="max-w-sm truncate text-xs text-muted-foreground">{subject}</p>
                    )}
                  </motion.div>
                ) : (
                  <motion.p
                    key={stepIndex}
                    className="text-sm font-medium text-muted-foreground"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    {LOADING_STEPS[stepIndex]}
                  </motion.p>
                )}
              </div>

              <div className="mt-4 flex justify-center gap-2">
                {showFinish && (
                  <Button onClick={onFinish} className="min-w-[120px]">
                    Finish
                  </Button>
                )}
                {showError && (
                  <>
                    {onRetry && (
                      <Button variant="outline" onClick={onRetry}>
                        Try again
                      </Button>
                    )}
                    <Button variant="default" onClick={onFinish}>
                      Close
                    </Button>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}
