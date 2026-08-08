"use client";

import { useState } from "react";
import { toast } from "sonner";
import { KeyRound, Trash2, UserPlus } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";
import { Table } from "@/components/Table";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  useAdminUsers,
  useCreateAdminUser,
  useDeleteAdminUser,
  useUpdateAdminUser,
} from "@/hooks/useAdmin";
import type { AdminUserListItem } from "@/lib/types";

export default function AdminUsersPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");

  const { data, isLoading, isError, refetch } = useAdminUsers({
    search: search || undefined,
    page,
    page_size: 20,
  });
  const createUser = useCreateAdminUser();
  const updateUser = useUpdateAdminUser();
  const deleteUser = useDeleteAdminUser();

  const handleCreate = async () => {
    try {
      await createUser.mutateAsync({ name, email, password, role });
      toast.success("User created");
      setShowCreate(false);
      setName("");
      setEmail("");
      setPassword("");
      setRole("user");
    } catch {
      toast.error("Failed to create user");
    }
  };

  const toggleRole = async (user: AdminUserListItem) => {
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        body: { role: user.role === "admin" ? "user" : "admin" },
      });
      toast.success("Role updated");
    } catch {
      toast.error("Failed to update role");
    }
  };

  const toggleApiAccess = async (user: AdminUserListItem) => {
    const enabling = !(user.api_access ?? true);
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        body: { api_access: enabling },
      });
      toast.success(
        enabling
          ? `API access enabled for ${user.name}`
          : `API access disabled for ${user.name}`
      );
    } catch {
      toast.error("Failed to update API access");
    }
  };

  const setDailyTokens = async (user: AdminUserListItem) => {
    const current = String(user.daily_token_limit ?? 50);
    const raw = window.prompt(`Daily tokens for ${user.name}`, current);
    if (raw == null) return;
    const limit = Number(raw);
    if (!Number.isFinite(limit) || limit < 0) {
      toast.error("Enter a valid number");
      return;
    }
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        body: { daily_token_limit: Math.floor(limit), reset_tokens_used_today: true },
      });
      toast.success(`Daily tokens set to ${Math.floor(limit)}`);
    } catch {
      toast.error("Failed to update tokens");
    }
  };

  const togglePlan = async (user: AdminUserListItem) => {
    const next = user.plan === "paid" ? "free" : "paid";
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        body: { plan: next },
      });
      toast.success(next === "paid" ? "Moved to paid plan" : "Moved to free plan");
    } catch {
      toast.error("Failed to update plan");
    }
  };

  const toggleOwnApiKeys = async (user: AdminUserListItem) => {
    const enabling = !user.own_api_keys_enabled;
    try {
      await updateUser.mutateAsync({
        userId: user.id,
        body: { own_api_keys_enabled: enabling },
      });
      toast.success(
        enabling
          ? `Own API keys approved for ${user.name}`
          : `Own API keys revoked for ${user.name}`
      );
    } catch {
      toast.error("Failed to update own-API permission");
    }
  };

  const handleDelete = async (userId: number) => {
    if (!confirm("Delete this user and all their data?")) return;
    try {
      await deleteUser.mutateAsync(userId);
      toast.success("User deleted");
    } catch {
      toast.error("Failed to delete user");
    }
  };

  if (isLoading) return <PageLoader />;
  if (isError || !data) {
    return <PageError message="Failed to load users" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="User management"
        description="Create, promote, demote, and delete platform users."
      >
        <Button size="sm" className="gap-1.5" onClick={() => setShowCreate((v) => !v)}>
          <UserPlus className="h-4 w-4" />
          Add user
        </Button>
      </PageHeader>

      {showCreate ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New user</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <Label>Email</Label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <Label>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            <div>
              <Label>Role</Label>
              <select
                className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="sm:col-span-2 lg:col-span-4">
              <Button onClick={handleCreate} disabled={createUser.isPending}>
                Create user
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search name or email..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-sm"
        />
      </div>

      <Table
        data={data.items}
        keyExtractor={(item) => item.id}
        emptyMessage="No users found"
        columns={[
          { key: "name", header: "Name" },
          { key: "email", header: "Email" },
          {
            key: "role",
            header: "Role",
            render: (user) => (
              <Badge variant={user.role === "admin" ? "default" : "secondary"}>{user.role}</Badge>
            ),
          },
          {
            key: "tokens",
            header: "Daily tokens",
            render: (user) =>
              user.role === "admin" ? (
                <span className="text-xs text-muted-foreground">Unlimited</span>
              ) : (
                <div className="text-xs">
                  <p className="font-medium tabular-nums">
                    {user.tokens_used_today ?? 0} / {user.daily_token_limit ?? 50}
                  </p>
                  <p className="text-muted-foreground">
                    left {user.tokens_remaining ?? Math.max(0, (user.daily_token_limit ?? 50) - (user.tokens_used_today ?? 0))}
                  </p>
                </div>
              ),
          },
          {
            key: "plan",
            header: "Plan",
            render: (user) => (
              <Badge variant={user.plan === "paid" ? "success" : "secondary"}>
                {user.plan === "paid" ? "paid" : "free"}
              </Badge>
            ),
          },
          {
            key: "api_access",
            header: "API",
            render: (user) =>
              user.role === "admin" ? (
                <Badge variant="default">Always</Badge>
              ) : (
                <div className="flex flex-col gap-1">
                  <Badge variant={(user.api_access ?? true) ? "success" : "destructive"}>
                    {(user.api_access ?? true) ? "Platform on" : "Platform off"}
                  </Badge>
                  {user.own_api_keys_enabled ? (
                    <Badge variant="success">Own keys</Badge>
                  ) : user.own_api_keys_requested ? (
                    <Badge variant="warning">Own keys requested</Badge>
                  ) : null}
                  {user.plan !== "paid" && user.paid_plan_requested ? (
                    <Badge variant="warning">Paid requested</Badge>
                  ) : null}
                </div>
              ),
          },
          { key: "lead_count", header: "Leads" },
          {
            key: "actions",
            header: "Actions",
            render: (user) => (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => toggleRole(user)}>
                  {user.role === "admin" ? "Make user" : "Make admin"}
                </Button>
                {user.role !== "admin" && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setDailyTokens(user)}
                      disabled={updateUser.isPending}
                    >
                      Set tokens
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => togglePlan(user)}
                      disabled={updateUser.isPending}
                    >
                      {user.plan === "paid" ? "Make free" : "Make paid"}
                    </Button>
                    <Button
                      size="sm"
                      variant={(user.api_access ?? true) ? "outline" : "default"}
                      className="gap-1.5"
                      onClick={() => toggleApiAccess(user)}
                      disabled={updateUser.isPending}
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                      {(user.api_access ?? true) ? "Disable APIs" : "Enable APIs"}
                    </Button>
                    <Button
                      size="sm"
                      variant={user.own_api_keys_enabled ? "outline" : "default"}
                      onClick={() => toggleOwnApiKeys(user)}
                      disabled={updateUser.isPending}
                    >
                      {user.own_api_keys_enabled ? "Revoke own APIs" : "Approve own APIs"}
                    </Button>
                  </>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive"
                  onClick={() => handleDelete(user.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ),
          },
        ]}
      />

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {data.page} · {data.total} users
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={page * data.page_size >= data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
