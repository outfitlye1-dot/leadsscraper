"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";

function PaymentResultContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");
  const ref = searchParams.get("ref");
  const msg = searchParams.get("msg");
  const success = status === "success";

  return (
    <div className="mx-auto max-w-lg space-y-8">
      <PageHeader eyebrow="Billing" title="Payment result" />
      <Card>
        <CardHeader className="text-center">
          {success ? (
            <CheckCircle2 className="mx-auto h-14 w-14 text-emerald-600" />
          ) : (
            <XCircle className="mx-auto h-14 w-14 text-destructive" />
          )}
          <CardTitle className="mt-4">
            {success ? "Payment successful" : "Payment failed"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-center text-sm text-muted-foreground">
          <p>{msg || (success ? "Your Pro plan is now active." : "Please try again.")}</p>
          {ref && <p className="font-mono text-xs">Ref: {ref}</p>}
          <div className="flex flex-wrap justify-center gap-2 pt-2">
            <Link href="/settings">
              <Button variant="outline">Back to settings</Button>
            </Link>
            {!success && (
              <Link href="/settings/plans">
                <Button>Try again</Button>
              </Link>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function PaymentResultPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <PaymentResultContent />
    </Suspense>
  );
}
