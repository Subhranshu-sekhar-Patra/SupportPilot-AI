"use client";

import { useState } from "react";
import {
  Building2,
  Users,
  ShieldCheck,
  Webhook,
  Key,
  Plus,
  Copy,
  Check,
  Save,
  Trash2,
  AlertCircle,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { MOCK_TEAM_MEMBERS } from "@/lib/mock-data";

type SettingsTab = "organization" | "team" | "sla" | "webhooks" | "api-keys";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("organization");

  // General Org form
  const [orgName, setOrgName] = useState("Acme Global Technologies");
  const [workspaceSlug, setWorkspaceSlug] = useState("acme-global");
  const [supportEmail, setSupportEmail] = useState("support@acmeglobal.com");
  const [timezone, setTimezone] = useState("America/New_York");
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Team invite modal
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("agent");
  const [teamMembers, setTeamMembers] = useState(MOCK_TEAM_MEMBERS);

  // Webhook settings
  const [webhookUrl, setWebhookUrl] = useState("https://automation.acmeglobal.com/webhook/supportpilot-events");
  const [webhookSecret, setWebhookSecret] = useState("whsec_99bf28d0298a44ecb7150a");
  const [isCopiedSecret, setIsCopiedSecret] = useState(false);
  const [isTestingWebhook, setIsTestingWebhook] = useState(false);
  const [webhookTestStatus, setWebhookTestStatus] = useState<string | null>(null);

  // API keys
  const [apiKeys, setApiKeys] = useState([
    { id: "key_1", name: "Production n8n Automation", prefix: "sp_live_948f...", created: "2026-11-15", lastUsed: "4 mins ago" },
    { id: "key_2", name: "Staging Web Portal", prefix: "sp_test_a03d...", created: "2026-11-01", lastUsed: "2 days ago" },
  ]);
  const [isNewKeyModalOpen, setIsNewKeyModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");

  const handleSaveGeneral = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleCopySecret = () => {
    navigator.clipboard.writeText(webhookSecret);
    setIsCopiedSecret(true);
    setTimeout(() => setIsCopiedSecret(false), 2000);
  };

  const handleTestWebhook = () => {
    setIsTestingWebhook(true);
    setWebhookTestStatus(null);
    setTimeout(() => {
      setIsTestingWebhook(false);
      setWebhookTestStatus("HTTP 200 OK — Ping delivered in 142ms");
    }, 1200);
  };

  const handleInviteMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;
    setTeamMembers((prev) => [
      ...prev,
      {
        id: `usr_${Date.now()}`,
        name: inviteEmail.split("@")[0],
        email: inviteEmail,
        role: inviteRole.charAt(0).toUpperCase() + inviteRole.slice(1),
        status: "online",
        activeTickets: 0,
      },
    ]);
    setInviteEmail("");
    setIsInviteModalOpen(false);
  };

  const handleCreateApiKey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName) return;
    setApiKeys((prev) => [
      ...prev,
      {
        id: `key_${Date.now()}`,
        name: newKeyName,
        prefix: `sp_live_${Math.random().toString(36).substring(2, 8)}...`,
        created: new Date().toISOString().split("T")[0],
        lastUsed: "Never",
      },
    ]);
    setNewKeyName("");
    setIsNewKeyModalOpen(false);
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
          Organization & System Settings
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Manage workspace profile, team roles, SLA rules, n8n webhook triggers, and API credentials.
        </p>
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 overflow-x-auto space-x-6">
        {[
          { id: "organization", label: "Organization", icon: Building2 },
          { id: "team", label: "Team & Roles", icon: Users },
          { id: "sla", label: "SLA & Routing", icon: ShieldCheck },
          { id: "webhooks", label: "Webhooks & n8n", icon: Webhook },
          { id: "api-keys", label: "API Credentials", icon: Key },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as SettingsTab)}
              className={`flex items-center gap-2 py-3 px-1 border-b-2 text-sm font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? "border-brand-600 text-brand-600 dark:text-brand-400 dark:border-brand-400 font-semibold"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Organization Profile */}
      {activeTab === "organization" && (
        <Card className="p-6 max-w-3xl">
          <form onSubmit={handleSaveGeneral} className="space-y-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
              General Organization Profile
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Company / Organization Name
                </label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Workspace Slug
                </label>
                <div className="flex rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden text-sm">
                  <span className="px-3 py-2.5 bg-gray-50 dark:bg-gray-900 text-gray-400 select-none border-r border-gray-200 dark:border-gray-700">
                    app.supportpilot.io/
                  </span>
                  <input
                    type="text"
                    value={workspaceSlug}
                    onChange={(e) => setWorkspaceSlug(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white dark:bg-gray-800 focus:outline-hidden"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Support Inbound Email
                </label>
                <input
                  type="email"
                  value={supportEmail}
                  onChange={(e) => setSupportEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Default Timezone
                </label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500"
                >
                  <option value="America/New_York">Eastern Time (US & Canada)</option>
                  <option value="America/Chicago">Central Time (US & Canada)</option>
                  <option value="America/Los_Angeles">Pacific Time (US & Canada)</option>
                  <option value="Europe/London">London / UTC</option>
                  <option value="Asia/Kolkata">Asia / Kolkata (IST)</option>
                </select>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
              {savedSuccess ? (
                <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                  <Check className="w-4 h-4" /> Changes saved successfully!
                </span>
              ) : (
                <span className="text-xs text-gray-400">Settings update across all active agents immediately.</span>
              )}
              <Button type="submit" variant="primary">
                <Save className="w-4 h-4 mr-1.5" />
                Save Changes
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Tab 2: Team & Roles */}
      {activeTab === "team" && (
        <Card className="overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">Active Team Members</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Staff members authorized to review tickets, draft answers, and manage knowledge assets.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsInviteModalOpen(true)}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Invite Member
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50/80 dark:bg-gray-800/50 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Member</th>
                  <th className="px-5 py-3">Role</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Active Tickets</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {teamMembers.map((member) => (
                  <tr key={member.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-950 text-brand-700 dark:text-brand-300 font-bold flex items-center justify-center text-xs">
                          {member.name.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">{member.name}</div>
                          <div className="text-xs text-gray-400">{member.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge
                        variant={member.role === "Owner" || member.role === "Admin" ? "purple" : "neutral"}
                        size="sm"
                      >
                        {member.role}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            member.status === "online" ? "bg-emerald-500" : "bg-gray-400"
                          }`}
                        />
                        {member.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                      {member.activeTickets} assigned
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button className="text-xs text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors">
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tab 3: SLA & Routing Policies */}
      {activeTab === "sla" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <h3 className="font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
              First Response SLA Targets
            </h3>
            <p className="text-xs text-gray-500">
              When tickets breach these thresholds, they trigger urgent on-call alerts via webhook.
            </p>

            <div className="space-y-3">
              {[
                { priority: "Urgent Priority", target: "15 minutes", badge: "danger" },
                { priority: "High Priority", target: "1 hour", badge: "warning" },
                { priority: "Medium Priority", target: "4 hours", badge: "info" },
                { priority: "Low Priority", target: "24 hours", badge: "neutral" },
              ].map((sla, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/40"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant={sla.badge as any} size="sm">
                      {sla.priority}
                    </Badge>
                  </div>
                  <span className="text-xs font-semibold text-gray-900 dark:text-white">{sla.target}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6 space-y-4">
            <h3 className="font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
              AI Autopilot Decision Gate
            </h3>
            <p className="text-xs text-gray-500">
              Thresholds determining whether an AI agent can send an answer autonomously or require human approval.
            </p>

            <div className="space-y-4 pt-2">
              <div>
                <div className="flex justify-between text-xs font-medium mb-1.5">
                  <span className="text-gray-700 dark:text-gray-300">Autonomous Send Confidence Floor</span>
                  <span className="font-bold text-brand-600 dark:text-brand-400">85% Minimum</span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="98"
                  defaultValue="85"
                  className="w-full accent-brand-600 cursor-pointer"
                />
                <span className="text-[11px] text-gray-400">
                  Responses scoring below 85% confidence are held in Human Inbox for approval.
                </span>
              </div>

              <div className="pt-3 border-t border-gray-100 dark:border-gray-800 space-y-2">
                <label className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded text-brand-600 focus:ring-brand-500" />
                  <span>Always escalate payment refund and legal queries to Human Escalations</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded text-brand-600 focus:ring-brand-500" />
                  <span>Include inline knowledge base citations on all external replies</span>
                </label>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 4: Webhooks & n8n Automation */}
      {activeTab === "webhooks" && (
        <Card className="p-6 max-w-3xl space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">n8n Automation & Webhook Ingestion</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Dispatch real-time payload events to n8n workflows for automated Slack alerts, CRM updates, and escalation routing.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                n8n Webhook Target URL
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm font-mono focus:outline-hidden focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                HMAC SHA-256 Signing Secret
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={webhookSecret}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 font-mono text-sm text-gray-600 dark:text-gray-300 select-all"
                />
                <Button
                  variant="outline"
                  size="md"
                  onClick={handleCopySecret}
                >
                  {isCopiedSecret ? (
                    <>
                      <Check className="w-4 h-4 mr-1 text-emerald-500" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-1" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Subscribed Trigger Events
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {[
                  "ticket.created (New ticket intake)",
                  "ai.response_drafted (Evaluated AI answer ready)",
                  "ticket.escalated (SLA breach / human takeover)",
                  "csat.submitted (Customer rating recorded)",
                ].map((event, i) => (
                  <label
                    key={i}
                    className="flex items-center gap-2 p-2.5 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 cursor-pointer"
                  >
                    <input type="checkbox" defaultChecked className="rounded text-brand-600 focus:ring-brand-500" />
                    <span className="font-mono text-gray-700 dark:text-gray-300">{event}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
              <div>
                {webhookTestStatus && (
                  <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    {webhookTestStatus}
                  </span>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                isLoading={isTestingWebhook}
                onClick={handleTestWebhook}
              >
                Send Test Webhook Ping
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Tab 5: API Credentials */}
      {activeTab === "api-keys" && (
        <Card className="overflow-hidden">
          <div className="p-5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">API Authentication Keys</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Generate secret access tokens for programmatic ticket creation and custom integrations.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsNewKeyModalOpen(true)}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Generate New API Key
            </Button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50/80 dark:bg-gray-800/50 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Key Label</th>
                  <th className="px-5 py-3">Prefix Token</th>
                  <th className="px-5 py-3">Created Date</th>
                  <th className="px-5 py-3">Last Activity</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {apiKeys.map((key) => (
                  <tr key={key.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-gray-900 dark:text-white">{key.name}</td>
                    <td className="px-5 py-3.5 font-mono text-xs text-gray-600 dark:text-gray-300">{key.prefix}</td>
                    <td className="px-5 py-3.5 text-xs text-gray-500">{key.created}</td>
                    <td className="px-5 py-3.5 text-xs text-gray-500">{key.lastUsed}</td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => setApiKeys(apiKeys.filter((k) => k.id !== key.id))}
                        className="text-xs text-red-500 hover:text-red-700 transition-colors"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Invite Member Modal */}
      <Modal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        title="Invite New Team Member"
        description="Send an invitation link to collaborate on SupportPilot AI."
      >
        <form onSubmit={handleInviteMember} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Work Email Address
            </label>
            <input
              type="email"
              placeholder="colleague@acmeglobal.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500 bg-white dark:bg-gray-800"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Assigned Role</label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm bg-white dark:bg-gray-800"
            >
              <option value="agent">Support Agent (Respond & Resolve)</option>
              <option value="admin">Administrator (Manage Team & Settings)</option>
              <option value="viewer">Viewer (Read-only Analytics)</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-3">
            <Button variant="outline" type="button" onClick={() => setIsInviteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>

      {/* Generate API Key Modal */}
      <Modal
        isOpen={isNewKeyModalOpen}
        onClose={() => setIsNewKeyModalOpen(false)}
        title="Generate New API Key"
        description="Provide a label to track where this key is used."
      >
        <form onSubmit={handleCreateApiKey} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Key Name / Description</label>
            <input
              type="text"
              placeholder="e.g. Zapier / Production CRM Ingest"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-sm focus:outline-hidden focus:ring-2 focus:ring-brand-500 bg-white dark:bg-gray-800"
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-3">
            <Button variant="outline" type="button" onClick={() => setIsNewKeyModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit">
              Generate Key
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
