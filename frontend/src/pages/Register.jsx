import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowRight, Loader2 } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

export default function Register() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", organization_name: "" });
  const [loading, setLoading] = useState(false);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      setUser(data);
      toast.success("Account created!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="cg-dark min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="flex items-center gap-2 text-white font-dash-head text-xl font-bold mb-8">
          <ShieldCheck className="text-emerald-400" /> ChurnGuard
        </div>
        <p className="cg-overline text-emerald-400 mb-2">Get Started</p>
        <h1 className="font-dash-head text-3xl font-bold text-white mb-8">Create your workspace</h1>

        <button
          type="button"
          onClick={handleGoogle}
          data-testid="google-register-button"
          className="w-full flex items-center justify-center gap-3 rounded-lg border border-white/15 bg-white/5 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-white/10"
        >
          <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="" className="h-5 w-5" />
          Continue with Google
        </button>

        <div className="my-6 flex items-center gap-4 text-slate-500 text-xs">
          <div className="h-px flex-1 bg-white/10" /> OR <div className="h-px flex-1 bg-white/10" />
        </div>

        <form onSubmit={submit} className="space-y-4">
          {[
            { k: "name", label: "Full name", type: "text", testid: "register-name-input" },
            { k: "organization_name", label: "Company / Organization", type: "text", testid: "register-org-input" },
            { k: "email", label: "Work email", type: "email", testid: "register-email-input" },
            { k: "password", label: "Password", type: "password", testid: "register-password-input" },
          ].map((f) => (
            <div key={f.k}>
              <label className="text-sm text-slate-300 font-dash-body">{f.label}</label>
              <input
                type={f.type}
                value={form[f.k]}
                onChange={upd(f.k)}
                data-testid={f.testid}
                className="mt-1 w-full rounded-lg bg-white/5 border border-white/15 px-4 py-3 text-white outline-none focus:ring-2 focus:ring-emerald-500 transition-shadow"
                required={f.k !== "organization_name"}
              />
            </div>
          ))}
          <button
            type="submit"
            disabled={loading}
            data-testid="register-submit-button"
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-3 font-semibold text-[#0b0f19] transition-colors hover:bg-emerald-400 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Create account <ArrowRight className="h-4 w-4" /></>}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-400 font-dash-body">
          Already have an account?{" "}
          <Link to="/login" className="text-emerald-400 hover:underline" data-testid="go-to-login-link">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
