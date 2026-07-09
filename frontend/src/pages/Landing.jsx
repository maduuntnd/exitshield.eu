import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ShieldCheck, ArrowRight, Percent, PauseCircle, Sparkles, TrendingUp, Zap, LineChart } from "lucide-react";

const HERO = "https://images.unsplash.com/photo-1768522036770-c615007cf0fd?crop=entropy&cs=srgb&fm=jpg&q=85&w=1920";
const SOCIAL = "https://images.unsplash.com/photo-1748609622257-bb917eda4d14?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.1, ease: "easeOut" } }),
};

const Feature = ({ icon: Icon, title, desc }) => (
  <motion.div variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
    className="cg-surface rounded-2xl border border-white/10 p-8 transition-colors hover:border-emerald-500/40">
    <div className="h-11 w-11 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-5">
      <Icon className="h-5 w-5 text-emerald-400" />
    </div>
    <h3 className="font-dash-head text-white text-lg font-semibold mb-2">{title}</h3>
    <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
  </motion.div>
);

export default function Landing() {
  return (
    <div className="cg-dark min-h-screen font-dash-body">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-white/10 bg-[#0b0f19]/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-16">
          <div className="flex items-center gap-2 text-white font-dash-head font-bold text-lg">
            <ShieldCheck className="text-emerald-400" /> ChurnGuard
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" data-testid="nav-login-link" className="text-sm text-slate-300 hover:text-white px-4 py-2 transition-colors">Sign in</Link>
            <Link to="/register" data-testid="nav-register-link"
              className="text-sm font-semibold rounded-full bg-emerald-500 text-[#0b0f19] px-5 py-2.5 hover:bg-emerald-400 transition-colors">
              Start free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <img src={HERO} alt="" className="absolute inset-0 h-full w-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-[#0b0f19]/60" />
        <div className="relative max-w-6xl mx-auto px-6 py-28 md:py-40">
          <motion.p custom={0} variants={fadeUp} initial="hidden" animate="show" className="cg-overline text-emerald-400 mb-6">
            Customer Retention Infrastructure
          </motion.p>
          <motion.h1 custom={1} variants={fadeUp} initial="hidden" animate="show"
            className="font-market-head text-5xl md:text-7xl font-black text-white leading-[0.95] max-w-4xl tracking-tight">
            Stop the churn <span className="text-emerald-400">before</span> the cancel.
          </motion.h1>
          <motion.p custom={2} variants={fadeUp} initial="hidden" animate="show"
            className="mt-6 text-lg text-slate-300 max-w-xl font-light leading-relaxed">
            ChurnGuard drops into your cancel button and turns leaving customers into saved revenue with dynamic, on-brand retention offers — powered by Stripe.
          </motion.p>
          <motion.div custom={3} variants={fadeUp} initial="hidden" animate="show" className="mt-10 flex flex-wrap gap-4">
            <Link to="/register" data-testid="hero-cta-button"
              className="flex items-center gap-2 rounded-full bg-emerald-500 text-[#0b0f19] px-7 py-4 font-semibold hover:bg-emerald-400 transition-colors">
              Get your save flow <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/login" data-testid="hero-demo-button"
              className="rounded-full border border-white/20 text-white px-7 py-4 font-medium hover:bg-white/5 transition-colors">
              View live demo
            </Link>
          </motion.div>

          <motion.div custom={4} variants={fadeUp} initial="hidden" animate="show"
            className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl">
            {[
              { v: "38%", l: "Avg. cancellations saved" },
              { v: "$4.2M", l: "MRR recovered" },
              { v: "12s", l: "Time to integrate" },
              { v: "0", l: "Engineering lift" },
            ].map((s) => (
              <div key={s.l}>
                <p className="font-dash-head text-3xl font-bold text-emerald-400">{s.v}</p>
                <p className="text-xs text-slate-500 mt-1">{s.l}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <p className="cg-overline text-emerald-400 mb-3">How it works</p>
        <h2 className="font-market-head text-3xl md:text-4xl font-bold text-white max-w-2xl mb-12">
          Three ways to keep revenue that was about to walk out.
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Feature icon={Percent} title="Offer a discount" desc="Auto-apply a Stripe coupon to their active subscription the moment they hesitate on price." />
          <Feature icon={PauseCircle} title="Offer a pause" desc="Let them pause billing for 30 or 60 days instead of leaving — keep the relationship alive." />
          <Feature icon={Sparkles} title="Learn from goodbyes" desc="Every cancellation is surveyed so you know exactly why customers leave and what to fix." />
        </div>
      </section>

      {/* Split */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center cg-surface rounded-3xl border border-white/10 p-8 md:p-12">
          <div>
            <p className="cg-overline text-emerald-400 mb-3">The command center</p>
            <h2 className="font-market-head text-3xl md:text-4xl font-bold text-white mb-4">Watch saved revenue add up in real time.</h2>
            <p className="text-slate-400 leading-relaxed mb-6">
              A precision dashboard shows churn saved, MRR recovered, and the top reasons customers try to leave — so you can act, not guess.
            </p>
            <div className="space-y-3">
              {[
                { icon: TrendingUp, t: "MRR recovery trends over time" },
                { icon: LineChart, t: "Top cancellation reasons, ranked" },
                { icon: Zap, t: "Rule-based offers that fire automatically" },
              ].map((x) => (
                <div key={x.t} className="flex items-center gap-3 text-slate-300 text-sm">
                  <div className="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                    <x.icon className="h-4 w-4 text-emerald-400" />
                  </div>
                  {x.t}
                </div>
              ))}
            </div>
          </div>
          <div className="relative rounded-2xl overflow-hidden border border-white/10">
            <img src={SOCIAL} alt="Team analyzing retention dashboard" className="w-full h-full object-cover" />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-6 pb-28">
        <div className="rounded-3xl border border-emerald-500/20 cg-glow bg-emerald-500/[0.04] p-10 md:p-16 text-center">
          <h2 className="font-market-head text-3xl md:text-5xl font-bold text-white mb-4">Your cancel button is leaking money.</h2>
          <p className="text-slate-400 max-w-xl mx-auto mb-8">Plug in ChurnGuard in minutes and start saving subscriptions today.</p>
          <Link to="/register" data-testid="footer-cta-button"
            className="inline-flex items-center gap-2 rounded-full bg-emerald-500 text-[#0b0f19] px-8 py-4 font-semibold hover:bg-emerald-400 transition-colors">
            Start free <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-white/10">
        <div className="max-w-6xl mx-auto px-6 py-8 flex items-center justify-between text-sm text-slate-500">
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-400" /> ChurnGuard</div>
          <p>© 2026 ChurnGuard. Retention infrastructure for SaaS.</p>
        </div>
      </footer>
    </div>
  );
}
