"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Trash2, UserPlus } from "lucide-react";
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
import { formatDate } from "@/lib/utils";
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
          { key: "lead_count", header: "Leads" },
          { key: "campaign_count", header: "Campaigns" },
          {
            key: "created_at",
            header: "Joined",
            render: (user) => formatDate(user.created_at),
          },
          {
            key: "actions",
            header: "Actions",
            render: (user) => (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => toggleRole(user)}>
                  {user.role === "admin" ? "Make user" : "Make admin"}
                </Button>
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
