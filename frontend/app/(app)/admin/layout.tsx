import { AdminRoute } from "@/components/AdminRoute";
import { AdminSubNav } from "@/components/admin/AdminSubNav";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminRoute>
      <div className="space-y-6">
        <AdminSubNav />
        {children}
      </div>
    </AdminRoute>
  );
}
