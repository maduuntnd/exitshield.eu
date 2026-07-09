import React, { useEffect, useState } from "react";
import { Plug, Check, Copy, Loader2, ShieldCheck, AlertTriangle, Link2Off } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

export default function Settings() {
  const [info, setInfo] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [copied, setCopied] = useState(null);

  const load = () => api.get("/settings/integration").then((r) => setInfo(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const connect = async () => {
    setConnecting(true);
    try {
      const { data } = await api.post("/settings/stripe/connect");
      if (data.mode === "oauth") {
        window.location.href = data.url;
        return;
      }
      toast.success("Stripe connected (test account)");
      await load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Connection failed");
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = async () => {
    try {
      await api.post("/settings/stripe/disconnect");
      toast.success("Stripe disconnected");
      await load();
    } catch { toast.error("Could not disconnect"); }
  };

  const copy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    toast.success("Copied");
    setTimeout(() => setCopied(null), 1500);
  };

  if (!info) {
    return (
      <DashboardLayout title="Settings" subtitle="Integration & Stripe">
        <div className="text-slate-500">Loading…</div>
      </DashboardLayout>
    );
  }

  const connected = info.stripe_connect.connected;
  const origin = window.location.origin;
  const buttonSnippet =
    `<a href="${origin}/cancel?user_id={{USER_ID}}&subscription_id={{SUBSCRIPTION_ID}}&api_key=${info.api_key}">\n  Cancel subscription\n</a>`;
  const urlTemplate = `${origin}/cancel?user_id={{USER_ID}}&subscription_id={{SUBSCRIPTION_ID}}&api_key=${info.api_key}`;

  return (
    <DashboardLayout title="Settings" subtitle="Connect Stripe & install ChurnGuard">
      <div className="space-y-6 max-w-4xl">
        {/* Stripe Connect */}
        <div className="cg-surface rounded-xl border border-white/10 p-6" data-testid="stripe-connect-card">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="h-11 w-11 rounded-xl bg-[#635BFF]/15 flex items-center justify-center shrink-0">
                <Plug className="h-5 w-5 text-[#8b85ff]" />
              </div>
              <div>
                <h3 className="font-dash-head text-white text-lg font-semibold">Connect your Stripe</h3>
                <p className="text-slate-400 text-sm mt-1 max-w-xl">
                  ChurnGuard needs permission to modify your customers' subscriptions (apply coupons,
                  pause, or cancel). Authorize once and every save action runs securely on your Stripe account.
                </p>
              </div>
            </div>
            {connected ? (
              <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400 shrink-0" data-testid="connect-status-connected">
                <Check className="h-4 w-4" /> Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-sm text-amber-400 shrink-0" data-testid="connect-status-disconnected">
                <AlertTriangle className="h-4 w-4" /> Not connected
              </span>
            )}
          </div>

          {connected ? (
            <div className="mt-5 flex flex-col sm:flex-row sm:items-center gap-3">
              <code className="text-xs text-slate-300 bg-black/40 rounded-lg px-4 py-2.5 border border-white/10">
                {info.stripe_connect.account_id}
              </code>
              {info.stripe_connect.simulated && (
                <span className="text-xs text-amber-400/80">Test connection (simulated) — plug in a live Stripe platform key for real Connect.</span>
              )}
              <button onClick={disconnect} data-testid="disconnect-stripe-button"
                className="sm:ml-auto inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-2.5 text-sm text-slate-300 hover:text-red-400 hover:bg-white/5 transition-colors">
                <Link2Off className="h-4 w-4" /> Disconnect
              </button>
            </div>
          ) : (
            <div className="mt-5">
              <button onClick={connect} disabled={connecting} data-testid="connect-stripe-button"
                className="inline-flex items-center gap-2 rounded-lg bg-[#635BFF] px-5 py-3 text-sm font-semibold text-white hover:bg-[#514bcc] transition-colors disabled:opacity-60">
                {connecting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plug className="h-4 w-4" />}
                Connect with Stripe
              </button>
              {!info.live_platform && (
                <p className="mt-3 text-xs text-slate-500">
                  Demo mode: this creates a simulated test connection so you can see the full flow. Real Stripe Connect activates once a live platform key is configured.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Integration snippet */}
        <div className="cg-surface rounded-xl border border-white/10 p-6" data-testid="integration-snippet-card">
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <h3 className="font-dash-head text-white text-lg font-semibold">Install the save flow</h3>
          </div>
          <p className="text-slate-400 text-sm mb-5 max-w-xl">
            Point your app's "Cancel" button at ChurnGuard. Fill <code className="text-slate-300">{"{{USER_ID}}"}</code> and{" "}
            <code className="text-slate-300">{"{{SUBSCRIPTION_ID}}"}</code> from your own backend when you render the link.
          </p>

          <div className="space-y-4">
            <div>
              <p className="cg-overline text-slate-500 mb-2">Your redirect URL</p>
              <div className="flex items-start gap-2">
                <code className="flex-1 text-xs text-slate-300 bg-black/40 rounded-lg px-4 py-3 border border-white/10 break-all">{urlTemplate}</code>
                <button onClick={() => copy(urlTemplate, "url")} data-testid="copy-url-button"
                  className="rounded-lg border border-white/15 p-3 text-slate-300 hover:bg-white/5 transition-colors">
                  {copied === "url" ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <p className="cg-overline text-slate-500 mb-2">Button snippet (HTML)</p>
              <div className="flex items-start gap-2">
                <pre className="flex-1 text-xs text-slate-300 bg-black/40 rounded-lg px-4 py-3 border border-white/10 overflow-x-auto whitespace-pre">{buttonSnippet}</pre>
                <button onClick={() => copy(buttonSnippet, "snippet")} data-testid="copy-snippet-button"
                  className="rounded-lg border border-white/15 p-3 text-slate-300 hover:bg-white/5 transition-colors">
                  {copied === "snippet" ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <p className="cg-overline text-slate-500 mb-2">API key</p>
              <div className="flex items-center gap-2">
                <code className="text-xs text-slate-300 bg-black/40 rounded-lg px-4 py-2.5 border border-white/10">{info.api_key}</code>
                <button onClick={() => copy(info.api_key, "key")} data-testid="copy-key-button"
                  className="rounded-lg border border-white/15 p-2.5 text-slate-300 hover:bg-white/5 transition-colors">
                  {copied === "key" ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>

          <a href={urlTemplate.replace("{{USER_ID}}", "ext_1001").replace("{{SUBSCRIPTION_ID}}", "sub_demo_1001")}
            target="_blank" rel="noopener noreferrer" data-testid="settings-test-flow-link"
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-[#0b0f19] hover:bg-emerald-400 transition-colors">
            Preview the save flow →
          </a>
        </div>
      </div>
    </DashboardLayout>
  );
}
