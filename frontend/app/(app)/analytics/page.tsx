"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDashboardStats } from "@/hooks/useDashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { PageHeader } from "@/components/PageHeader";
import { PageLoader } from "@/components/Loader";
import { PageError } from "@/components/PageError";

const COLORS = ["#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#06b6d4", "#64748b"];

export default function AnalyticsPage() {
  const { data: stats, isLoading, error, refetch } = useDashboardStats();

  if (isLoading) return <PageLoader />;
  if (error || !stats) {
    return <PageError message="Failed to load analytics" onRetry={() => refetch()} />;
  }

  const leadStatusData = [
    { name: "New", value: stats.new_leads },
    { name: "Contacted", value: stats.contacted_leads },
    { name: "Interested", value: stats.interested_leads },
    { name: "Follow Up", value: stats.follow_up_leads },
    { name: "Closed", value: stats.closed_leads },
    { name: "Lost", value: stats.lost_leads },
  ].filter((d) => d.value > 0);

  const performanceData = [
    { name: "Leads", value: stats.total_leads },
    { name: "Campaigns", value: stats.campaign_count },
    { name: "Messages", value: stats.messages_generated },
  ];

  const funnelData = [
    { stage: "New", count: stats.new_leads },
    { stage: "Contacted", count: stats.contacted_leads },
    { stage: "Interested", count: stats.interested_leads },
    { stage: "Follow Up", count: stats.follow_up_leads },
    { stage: "Closed", count: stats.closed_leads },
    { stage: "Lost", count: stats.lost_leads },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Insights"
        title="Analytics"
        description="Visual insights into your lead generation performance"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Lead Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {leadStatusData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={leadStatusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    dataKey="value"
                  >
                    {leadStatusData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[300px] items-center justify-center text-muted-foreground">
                No lead data yet
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Platform Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="name" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Lead Funnel</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={funnelData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis type="number" className="text-xs" />
                <YAxis dataKey="stage" type="category" className="text-xs" width={80} />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Message & Campaign Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg border border-border p-6 text-center">
                <p className="text-3xl font-bold text-primary">{stats.messages_generated}</p>
                <p className="mt-1 text-sm text-muted-foreground">Messages Generated</p>
              </div>
              <div className="rounded-lg border border-border p-6 text-center">
                <p className="text-3xl font-bold text-primary">{stats.campaign_count}</p>
                <p className="mt-1 text-sm text-muted-foreground">Total Campaigns</p>
              </div>
              <div className="rounded-lg border border-border p-6 text-center">
                <p className="text-3xl font-bold text-primary">
                  {stats.total_leads
                    ? Math.round((stats.messages_generated / stats.total_leads) * 100)
                    : 0}
                  %
                </p>
                <p className="mt-1 text-sm text-muted-foreground">Outreach Coverage</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
