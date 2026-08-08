"use client";

import { Suspense, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Check, Crown, Loader2, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { submitJazzCashForm } from "@/lib/jazzcash";
import { useAuth } from "@/hooks/useAuth";
import { PaymentMethodModal } from "@/components/PaymentMethodModal";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import type { PlansCatalog, PurchaseProPlanResult } from "@/lib/types";

function PlansPageContent() {
  const router = useRouter();
  const { user, fetchUser } = useAuth();
  const queryClient = useQueryClient();
  const [payModalOpen, setPayModalOpen] = useState(false);

  const { data: catalog, isLoading } = useQuery({
    queryKey: ["plans-catalog"],
    queryFn: async () => {
      const { data } = await api.get<PlansCatalog>("/settings/plans");
      return data;
    },
    enabled: !!user && user.role !== "admin",
  });

  const purchasePro = useMutation({
    mutationFn: async (paymentMethod: string) => {
      const { data } = await api.post<PurchaseProPlanResult>("/settings/purchase-pro-plan", {
        payment_method: paymentMethod,
      });
      return data;
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["plans-catalog"] });
      queryClient.invalidateQueries({ queryKey: ["usage-quota"] });

      if (result.action === "jazzcash_form" && result.post_url && result.fields) {
        toast.success("Opening JazzCash…");
        setPayModalOpen(false);
        submitJazzCashForm(result.post_url, result.fields);
        return;
      }
      if (result.action === "redirect" && result.checkout_url) {
        toast.success("Opening secure checkout…");
        window.open(result.checkout_url, "_blank", "noopener,noreferrer");
        return;
      }
      if (result.action === "already_active") {
        toast.info(result.message);
        fetchUser?.();
        return;
      }
      fetchUser?.();
      toast.success(result.message);
      setPayModalOpen(false);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Could not start payment";
      toast.error(String(msg));
    },
  });

  if (!user || user.role === "admin") {
    return (
      <div className="space-y-6">
        <PageHeader title="Plans" description="Subscription plans are managed per user account." />
        <p className="text-sm text-muted-foreground">Admins have unlimited platform API access.</p>
        <Link href="/settings">
          <Button variant="outline" size="sm">
            Back to settings
          </Button>
        </Link>
      </div>
    );
  }

  if (isLoading || !catalog) return <PageLoader />;

  const proPlan = catalog.plans.find((p) => p.id === "pro");
  const freePlan = catalog.plans.find((p) => p.id === "free");
  const isPro = catalog.current_plan === "paid";
  const hasJazzCash = (catalog.payment_methods?.length ?? 0) > 0;
  const pricePkr = catalog.price_pkr ?? catalog.payment_methods?.[0]?.amount;

  return (
    <div className="space-y-8">
      <PaymentMethodModal
        open={payModalOpen}
        onClose={() => setPayModalOpen(false)}
        methods={catalog.payment_methods ?? []}
        amountPkr={pricePkr}
        onPayJazzCash={() => purchasePro.mutate("jazzcash")}
        isPaying={purchasePro.isPending}
      />

      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => router.push("/settings")}>
          <ArrowLeft className="h-4 w-4" />
          Settings
        </Button>
      </div>

      <PageHeader
        eyebrow="Billing"
        title="Choose your plan"
        description="Upgrade to Pro for more daily API tokens and higher limits."
      />

      {catalog.paid_plan_requested && !isPro && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="pt-6 text-sm text-muted-foreground">
            Your Pro plan request is pending.{" "}
            {catalog.contact_email ? (
              <>Contact {catalog.contact_email} if you need help.</>
            ) : (
              <>An admin will activate your plan shortly.</>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {freePlan && (
          <Card className={freePlan.is_current ? "ring-2 ring-border" : ""}>
            <CardHeader>
              <CardTitle>{freePlan.name}</CardTitle>
              <CardDescription>For getting started</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-4xl font-semibold">Free</p>
                <p className="text-sm text-muted-foreground">{freePlan.daily_tokens} tokens / day</p>
              </div>
              <ul className="space-y-2">
                {freePlan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    {feature}
                  </li>
                ))}
              </ul>
              {freePlan.is_current ? (
                <Badge variant="secondary">Current plan</Badge>
              ) : (
                <p className="text-xs text-muted-foreground">Included with every account</p>
              )}
            </CardContent>
          </Card>
        )}

        {proPlan && (
          <Card className="relative overflow-hidden border-primary/30 bg-primary/[0.03] ring-2 ring-primary/20">
            <div className="absolute right-4 top-4">
              <Badge className="gap-1">
                <Sparkles className="h-3 w-3" />
                Recommended
              </Badge>
            </div>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Crown className="h-5 w-5 text-primary" />
                {proPlan.name}
              </CardTitle>
              <CardDescription>For power users & teams</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                {pricePkr != null ? (
                  <>
                    <p className="text-4xl font-semibold">
                      Rs {pricePkr.toLocaleString()}
                      <span className="text-lg font-normal text-muted-foreground">/mo</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      ≈ ${proPlan.price_usd}/mo · {proPlan.daily_tokens} tokens / day
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-4xl font-semibold">
                      ${proPlan.price_usd}
                      <span className="text-lg font-normal text-muted-foreground">/mo</span>
                    </p>
                    <p className="text-sm text-muted-foreground">{proPlan.daily_tokens} tokens / day</p>
                  </>
                )}
              </div>
              <ul className="space-y-2">
                {proPlan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    {feature}
                  </li>
                ))}
              </ul>
              {isPro ? (
                <Badge variant="success">Current plan</Badge>
              ) : (
                <Button
                  className="w-full gap-2"
                  size="lg"
                  onClick={() => {
                    if (hasJazzCash) {
                      setPayModalOpen(true);
                    } else {
                      purchasePro.mutate("request");
                    }
                  }}
                  disabled={purchasePro.isPending}
                >
                  {purchasePro.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Crown className="h-4 w-4" />
                  )}
                  {hasJazzCash ? "Purchase Pro Plan" : "Request Pro Plan"}
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function SettingsPlansPage() {
  return (
    <Suspense fallback={<PageLoader />}>
      <PlansPageContent />
    </Suspense>
  );
}
