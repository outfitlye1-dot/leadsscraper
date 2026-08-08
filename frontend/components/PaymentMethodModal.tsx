"use client";

import { Loader2, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import type { PaymentMethod } from "@/lib/types";

interface PaymentMethodModalProps {
  open: boolean;
  onClose: () => void;
  methods: PaymentMethod[];
  amountPkr?: number | null;
  onPayJazzCash: () => void;
  isPaying: boolean;
}

export function PaymentMethodModal({
  open,
  onClose,
  methods,
  amountPkr,
  onPayJazzCash,
  isPaying,
}: PaymentMethodModalProps) {
  if (!open) return null;

  const jazzcash = methods.find((m) => m.id === "jazzcash");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        aria-label="Close"
        onClick={onClose}
      />
      <Card className="relative z-10 w-full max-w-md shadow-xl">
        <CardHeader>
          <CardTitle>Choose payment method</CardTitle>
          <CardDescription>
            {amountPkr != null
              ? `Pro plan — Rs ${amountPkr.toLocaleString()} / month`
              : "Complete payment to activate Pro plan"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {jazzcash ? (
            <button
              type="button"
              onClick={onPayJazzCash}
              disabled={isPaying}
              className="flex w-full items-center gap-4 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-primary/40 hover:bg-muted/40 disabled:opacity-60"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-600/10 text-red-600">
                <Smartphone className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <p className="font-medium">{jazzcash.name}</p>
                <p className="text-xs text-muted-foreground">{jazzcash.description}</p>
                <p className="mt-1 text-sm font-semibold tabular-nums">
                  Rs {jazzcash.amount.toLocaleString()} PKR
                </p>
              </div>
              {isPaying && <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />}
            </button>
          ) : (
            <p className="text-sm text-muted-foreground">
              JazzCash is not configured yet. Ask admin to add merchant credentials.
            </p>
          )}
          <Button variant="outline" className="w-full" onClick={onClose} disabled={isPaying}>
            Cancel
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
