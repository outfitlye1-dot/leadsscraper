"use client";

import { useState } from "react";
import { Mail, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import {
  useConnectSmtpAccount,
  useDeleteEmailAccount,
  useEmailAccounts,
  useStartGoogleOAuth,
  useStartMicrosoftOAuth,
} from "@/hooks/useEmailOutreach";
import { statusVariant } from "@/components/email-outreach/outreachEmailUtils";

export function EmailAccountsSection() {
  const { data: accounts = [] } = useEmailAccounts();
  const connectSmtp = useConnectSmtpAccount();
  const deleteAccount = useDeleteEmailAccount();
  const startGoogle = useStartGoogleOAuth();
  const startMicrosoft = useStartMicrosoftOAuth();

  const [showSmtpForm, setShowSmtpForm] = useState(false);
  const [smtpEmail, setSmtpEmail] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-4 w-4" />
          Email accounts
        </CardTitle>
        <CardDescription>
          Connect your Gmail, Outlook, or SMTP account. Outreach limits are set by your admin.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              startGoogle.mutate(undefined, {
                onSuccess: (url) => {
                  window.location.href = url;
                },
                onError: () => toast.error("Google OAuth not configured on server"),
              })
            }
          >
            Connect Gmail
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              startMicrosoft.mutate(undefined, {
                onSuccess: (url) => {
                  window.location.href = url;
                },
                onError: () => toast.error("Microsoft OAuth not configured on server"),
              })
            }
          >
            Connect Outlook
          </Button>
          <Button size="sm" variant="outline" onClick={() => setShowSmtpForm((v) => !v)}>
            <Plus className="mr-1 h-3 w-3" />
            SMTP
          </Button>
        </div>

        {showSmtpForm && (
          <div className="space-y-3 rounded-lg border border-border/60 p-4">
            <p className="text-xs text-muted-foreground">
              Gmail: normal password will fail. Turn on 2-Step Verification, then create an{" "}
              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noreferrer"
                className="font-medium underline underline-offset-2"
              >
                App Password
              </a>{" "}
              and paste it below (or use <span className="font-medium">Connect Gmail</span> instead).
            </p>
            <div>
              <Label>Email</Label>
              <Input value={smtpEmail} onChange={(e) => setSmtpEmail(e.target.value)} />
            </div>
            <div>
              <Label>App password</Label>
              <Input
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder="16-character Google App Password"
              />
            </div>
            <Button
              size="sm"
              onClick={() =>
                connectSmtp.mutate(
                  { email_address: smtpEmail, password: smtpPassword },
                  {
                    onSuccess: () => {
                      toast.success("SMTP account connected");
                      setShowSmtpForm(false);
                      setSmtpPassword("");
                    },
                    onError: (err) =>
                      toast.error(
                        // Surface backend detail (e.g. Gmail App Password help)
                        (err as { response?: { data?: { detail?: string } } })?.response?.data
                          ?.detail || "Failed to connect SMTP account"
                      ),
                  }
                )
              }
            >
              Save account
            </Button>
          </div>
        )}

        <div className="space-y-2">
          {accounts.length === 0 && (
            <p className="text-sm text-muted-foreground">No accounts connected yet.</p>
          )}
          {accounts.map((account) => (
            <div
              key={account.id}
              className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium">{account.email_address}</p>
                <p className="text-xs text-muted-foreground">
                  {account.provider}
                  {account.is_default ? " · default" : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={statusVariant(account.status)}>{account.status}</Badge>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() =>
                    deleteAccount.mutate(account.id, {
                      onSuccess: () => toast.success("Account removed"),
                    })
                  }
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
