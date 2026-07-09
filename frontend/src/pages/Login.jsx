import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowRight, Loader2 } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

const GoogleButton = () => {
  const handleGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <button
      type="button"
      onClick={handleGoogle}
      data-testid="google-login-button"
      className="w-full flex items-center justify-center gap-3 rounded-lg border border-white/15 bg-white/5 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-white/10"
    >
      <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="" className="h-5 w-5" />
      Continue with Google
    </button>
  );
};

export default function Login() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("demo@churnguard.io");
  const [password, setPassword] = useState("ChurnGuard2026!");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      setUser(data);
      toast.success("Welcome back!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cg-dark min-h-screen flex">
      <div className="hidden lg:flex w-1/2 relative overflow-hidden border-r border-white/10">
        <img
          src="https://images.unsplash.com/photo-1768522036770-c615007cf0fd?crop=entropy&cs=srgb&fm=jpg&q=85&w=1400"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-[#0b0f19]/70" />
        <div className="relative z-10 flex flex-col justify-between p-12">
          <div className="flex items-center gap-2 text-white font-dash-head text-xl font-bold">
            <ShieldCheck className="text-emerald-400" /> ChurnGuard
          </div>
          <div>
            <p className="cg-overline text-emerald-400 mb-4">Retention Command Center</p>
            <h2 className="font-dash-head text-4xl font-bold text-white leading-tight max-w-md">
              Turn cancellations into second chances.
            </h2>
            <p className="mt-4 text-slate-400 max-w-md font-dash-body">
              Recover MRR automatically with intelligent, on-brand save flows.
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2 text-white font-dash-head text-xl font-bold mb-8">
            <ShieldCheck className="text-emerald-400" /> ChurnGuard
          </div>
          <p className="cg-overline text-emerald-400 mb-2">Vendor Login</p>
          <h1 className="font-dash-head text-3xl font-bold text-white mb-8">Sign in to your dashboard</h1>

          <GoogleButton />

          <div className="my-6 flex items-center gap-4 text-slate-500 text-xs">
            <div className="h-px flex-1 bg-white/10" /> OR <div className="h-px flex-1 bg-white/10" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-sm text-slate-300 font-dash-body">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email-input"
                className="mt-1 w-full rounded-lg bg-white/5 border border-white/15 px-4 py-3 text-white outline-none focus:ring-2 focus:ring-emerald-500 transition-shadow"
                required
              />
            </div>
            <div>
              <label className="text-sm text-slate-300 font-dash-body">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="login-password-input"
                className="mt-1 w-full rounded-lg bg-white/5 border border-white/15 px-4 py-3 text-white outline-none focus:ring-2 focus:ring-emerald-500 transition-shadow"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-3 font-semibold text-[#0b0f19] transition-colors hover:bg-emerald-400 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Sign in <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>

          <p className="mt-6 text-sm text-slate-400 font-dash-body">
            No account?{" "}
            <Link to="/register" className="text-emerald-400 hover:underline" data-testid="go-to-register-link">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
