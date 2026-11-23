"use client";

import { useState } from "react";
import {
  User,
  Mail,
  Shield,
  KeyRound,
  Bell,
  Smartphone,
  CheckCircle2,
  Lock,
  Laptop,
  LogOut,
  Save,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useAuthStore } from "@/store/auth";

export default function ProfilePage() {
  const { user } = useAuthStore();

  const [fullName, setFullName] = useState(user?.full_name || "Sarah Jenkins");
  const [email] = useState(user?.email || "s.jenkins@cloudscale.io");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  // Notification toggles
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [urgentEscalations, setUrgentEscalations] = useState(true);
  const [dailyDigest, setDailyDigest] = useState(false);
  const [soundNotifications, setSoundNotifications] = useState(true);

  const handleUpdatePassword = (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    setPasswordSuccess(true);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setTimeout(() => setPasswordSuccess(false), 3000);
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl pb-12">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">User Profile & Account</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Manage your personal credentials, multi-factor authentication, and notifications.
        </p>
      </div>

      {/* Profile Overview Card */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 text-white flex items-center justify-center text-2xl font-bold shadow-md">
              {fullName.substring(0, 2).toUpperCase()}
            </div>
            <span className="absolute bottom-0 right-0 w-4 h-4 bg-emerald-500 border-2 border-white dark:border-gray-900 rounded-full" />
          </div>

          <div className="flex-1 text-center sm:text-left space-y-1">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">{fullName}</h2>
              <Badge variant="purple" size="sm">
                Senior Escalations Lead
              </Badge>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">{email}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Workspace: <span className="font-medium text-gray-600 dark:text-gray-300">CloudScale Enterprise</span> • Joined October 2025
            </p>
          </div>
        </div>
      </Card>

      {/* Personal Information Form */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3 mb-4">
          Personal Information
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Email Address</label>
            <input
              type="email"
              readOnly
              value={email}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-sm text-gray-500 select-all"
            />
          </div>
        </div>
      </Card>

      {/* Security & Password */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3 mb-4">
          Security & Password
        </h3>

        <form onSubmit={handleUpdatePassword} className="space-y-4 max-w-xl">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Current Password</label>
            <input
              type="password"
              placeholder="••••••••••••"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">New Password</label>
              <input
                type="password"
                placeholder="••••••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Confirm New Password</label>
              <input
                type="password"
                placeholder="••••••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                required
              />
            </div>
          </div>

          {passwordError && <p className="text-xs text-red-500 font-medium">{passwordError}</p>}
          {passwordSuccess && (
            <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> Password updated successfully!
            </p>
          )}

          <div className="pt-2">
            <Button type="submit" variant="primary" size="sm">
              <Lock className="w-4 h-4 mr-1.5" />
              Update Password
            </Button>
          </div>
        </form>
      </Card>

      {/* Notification Preferences */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3 mb-4">
          Notification Preferences
        </h3>

        <div className="space-y-4">
          <label className="flex items-center justify-between p-3 rounded-xl border border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 cursor-pointer">
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-white">Urgent SLA Breach Alerts</div>
              <div className="text-xs text-gray-400">Receive instant push & email alerts when high-priority tickets risk SLA breach.</div>
            </div>
            <input
              type="checkbox"
              checked={urgentEscalations}
              onChange={(e) => setUrgentEscalations(e.target.checked)}
              className="w-4 h-4 text-brand-600 rounded focus:ring-brand-500"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-xl border border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 cursor-pointer">
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-white">Email Notifications on Assigned Tickets</div>
              <div className="text-xs text-gray-400">Get an email whenever a customer replies to an assigned ticket.</div>
            </div>
            <input
              type="checkbox"
              checked={emailAlerts}
              onChange={(e) => setEmailAlerts(e.target.checked)}
              className="w-4 h-4 text-brand-600 rounded focus:ring-brand-500"
            />
          </label>

          <label className="flex items-center justify-between p-3 rounded-xl border border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 cursor-pointer">
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-white">Daily Performance Digest</div>
              <div className="text-xs text-gray-400">Summary of total resolved tickets and team CSAT scores delivered at 8:00 AM.</div>
            </div>
            <input
              type="checkbox"
              checked={dailyDigest}
              onChange={(e) => setDailyDigest(e.target.checked)}
              className="w-4 h-4 text-brand-600 rounded focus:ring-brand-500"
            />
          </label>
        </div>
      </Card>

      {/* Active Login Sessions */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3 mb-4">
          Active Login Sessions
        </h3>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-50/20 dark:bg-emerald-950/20">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-600 flex items-center justify-center">
                <Laptop className="w-5 h-5" />
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  Windows 11 • Chrome 131
                  <Badge variant="success" size="sm">Current Device</Badge>
                </div>
                <div className="text-xs text-gray-400">IP: 192.168.1.45 • Active now</div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-xl border border-gray-100 dark:border-gray-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-500 flex items-center justify-center">
                <Smartphone className="w-5 h-5" />
              </div>
              <div>
                <div className="text-sm font-semibold text-gray-900 dark:text-white">iOS 18 • Safari Mobile</div>
                <div className="text-xs text-gray-400">IP: 104.28.192.8 • Last active 3 hours ago</div>
              </div>
            </div>
            <button className="text-xs font-medium text-red-500 hover:text-red-700 transition-colors">
              Revoke
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
