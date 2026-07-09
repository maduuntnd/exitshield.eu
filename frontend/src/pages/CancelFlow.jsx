import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, ArrowRight, Check, Loader2, PartyPopper, Heart, PauseCircle } from "lucide-react";
import { api, formatApiError } from "@/lib/api";

const SIDE_IMAGE =
  "https://images.unsplash.com/photo-1519120944692-1a8d8cfc107f?crop=entropy&cs=srgb&fm=jpg&q=85&w=1400";

const stepVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

function Stepper({ step }) {
  return (
    <div className="flex items-center gap-2 mb-10" data-testid="wizard-stepper">
      {[1, 2, 3].map((s) => (
        <div key={s} className={`h-0.5 w-12 rounded-full transition-colors duration-500 ${s <= step ? "bg-[#111827]" : "bg-gray-200"}`} />
      ))}
    </div>
  );
}

export default function CancelFlow() {
  const [params] = useSearchParams();
  const apiKey = params.get("api_key");
  const userId = params.get("user_id");
  const subId = params.get("subscription_id");

  const [step, setStep] = useState(1);
  const [initData, setInitData] = useState(null);
  const [token, setToken] = useState(null);
  const [error, setError] = useState(null);
  const [selectedReason, setSelectedReason] = useState(null);
  const [offer, setOffer] = useState(null);
  const [outcome, setOutcome] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!apiKey || !userId) {
      setError("This cancellation link is missing required parameters.");
      return;
    }
    api
      .post("/v1/session/init", { api_key: apiKey, external_user_id: userId, subscription_id: subId })
      .then((r) => { setInitData(r.data); setToken(r.data.token); })
      .catch((err) => setError(formatApiError(err.response?.data?.detail) || "Could not start session."));
  }, [apiKey, userId, subId]);

  const chooseReason = async () => {
    if (!selectedReason) return;
    setBusy(true);
    try {
      const { data } = await api.post("/v1/session/respond", { token, selected_reason: selectedReason });
      setOffer(data.offer);
      setStep(2);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const applyAction = async (action) => {
    setBusy(true);
    try {
      const { data } = await api.post("/v1/stripe/apply-offer", { token, action, offer_id: offer?.id });
      setOutcome(data);
      setStep(3);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally { setBusy(false); }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center p-6 font-portal-body">
        <div className="text-center max-w-md">
          <h1 className="font-portal-head text-2xl font-bold text-[#111827] mb-2">Something went wrong</h1>
          <p className="text-[#6B7280]" data-testid="cancel-error">{error}</p>
        </div>
      </div>
    );
  }

  if (!initData) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#111827]" />
      </div>
    );
  }

  const isPause = offer?.type === "pause";
  const acceptAction = isPause ? "accept_pause" : "accept_discount";

  return (
    <div className="min-h-screen bg-[#F9FAFB] font-portal-body flex flex-col lg:flex-row">
      {/* Left: interaction */}
      <div className="flex-1 lg:w-3/5 flex flex-col">
        <div className="flex items-center gap-2 p-6 lg:p-10 text-[#111827]">
          <ShieldCheck className="h-5 w-5" />
          <span className="font-portal-head font-bold">{initData.org_name}</span>
        </div>

        <div className="flex-1 flex items-center px-6 lg:px-16 pb-16">
          <div className="w-full max-w-xl">
            <Stepper step={step} />
            <AnimatePresence mode="wait">
              {/* STEP 1 — Reason */}
              {step === 1 && (
                <motion.div key="s1" variants={stepVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.4, ease: "easeOut" }} data-testid="wizard-step-1">
                  <p className="text-[#6B7280] mb-2 text-sm">{initData.customer_email}</p>
                  <h1 className="font-portal-head text-3xl md:text-4xl font-bold text-[#111827] leading-tight">
                    {initData.flow.title}
                  </h1>
                  <p className="text-[#6B7280] mt-3 leading-relaxed">Before you go, help us understand what happened. Why are you canceling?</p>
                  <div className="mt-8 space-y-3">
                    {initData.flow.reasons.map((r) => (
                      <button key={r} onClick={() => setSelectedReason(r)} data-testid={`reason-${r.replace(/\s+/g, "-").toLowerCase()}`}
                        className={`w-full flex items-center justify-between rounded-xl border px-5 py-4 text-left transition-colors ${selectedReason === r ? "border-[#111827] bg-[#111827]/[0.03]" : "border-black/10 hover:border-black/25"}`}>
                        <span className="text-[#111827]">{r}</span>
                        <span className={`h-5 w-5 rounded-full border flex items-center justify-center ${selectedReason === r ? "border-[#111827] bg-[#111827]" : "border-gray-300"}`}>
                          {selectedReason === r && <Check className="h-3 w-3 text-white" />}
                        </span>
                      </button>
                    ))}
                  </div>
                  <button onClick={chooseReason} disabled={!selectedReason || busy} data-testid="reason-continue-button"
                    className="mt-8 flex items-center gap-2 rounded-full bg-[#111827] px-7 py-3.5 font-semibold text-white transition-colors hover:bg-black disabled:opacity-40">
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Continue <ArrowRight className="h-4 w-4" /></>}
                  </button>
                </motion.div>
              )}

              {/* STEP 2 — Offer */}
              {step === 2 && (
                <motion.div key="s2" variants={stepVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.4, ease: "easeOut" }} data-testid="wizard-step-2">
                  {offer ? (
                    <>
                      <span className="inline-block rounded-full bg-[#4F46E5]/10 text-[#4F46E5] text-xs font-semibold px-3 py-1 mb-4">Wait — a special offer for you</span>
                      <h1 className="font-portal-head text-3xl md:text-4xl font-bold text-[#111827] leading-tight">
                        {isPause ? "Need a break instead?" : `How about ${offer.value}?`}
                      </h1>
                      <p className="text-[#6B7280] mt-3 leading-relaxed">{offer.description}</p>

                      <div className="mt-8 rounded-2xl cg-portal-card bg-white p-6" data-testid="offer-card">
                        <div className="flex items-center gap-3">
                          <div className="h-11 w-11 rounded-xl bg-[#111827] flex items-center justify-center text-white">
                            {isPause ? <PauseCircle className="h-5 w-5" /> : <Heart className="h-5 w-5" />}
                          </div>
                          <div>
                            <p className="font-portal-head font-bold text-[#111827] text-lg">{offer.value}</p>
                            <p className="text-sm text-[#6B7280]">Applied instantly to your subscription</p>
                          </div>
                        </div>
                      </div>

                      <div className="mt-8 flex flex-col sm:flex-row gap-3">
                        <button onClick={() => applyAction(acceptAction)} disabled={busy} data-testid="accept-offer-button"
                          className="flex items-center justify-center gap-2 rounded-full bg-[#111827] px-7 py-3.5 font-semibold text-white transition-colors hover:bg-black disabled:opacity-40">
                          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>{isPause ? "Pause my plan" : "Claim this offer"}</>}
                        </button>
                        <button onClick={() => applyAction("cancel")} disabled={busy} data-testid="decline-offer-button"
                          className="rounded-full border border-black/15 px-7 py-3.5 font-medium text-[#6B7280] transition-colors hover:bg-black/[0.03]">
                          No thanks, cancel anyway
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <h1 className="font-portal-head text-3xl font-bold text-[#111827]">Are you sure you want to cancel?</h1>
                      <p className="text-[#6B7280] mt-3">We'd hate to see you go.</p>
                      <button onClick={() => applyAction("cancel")} disabled={busy} data-testid="confirm-cancel-button"
                        className="mt-8 rounded-full bg-[#111827] px-7 py-3.5 font-semibold text-white transition-colors hover:bg-black disabled:opacity-40">
                        Confirm cancellation
                      </button>
                    </>
                  )}
                </motion.div>
              )}

              {/* STEP 3 — Result */}
              {step === 3 && (
                <motion.div key="s3" variants={stepVariants} initial="initial" animate="animate" exit="exit" transition={{ duration: 0.4, ease: "easeOut" }} data-testid="wizard-step-3">
                  {outcome?.outcome !== "canceled" ? (
                    <>
                      <div className="h-14 w-14 rounded-2xl bg-emerald-500 flex items-center justify-center text-white mb-6">
                        <PartyPopper className="h-7 w-7" />
                      </div>
                      <h1 className="font-portal-head text-3xl md:text-4xl font-bold text-[#111827] leading-tight" data-testid="success-heading">
                        {outcome?.outcome === "retained_pause" ? "Your plan is paused" : "You're all set!"}
                      </h1>
                      <p className="text-[#6B7280] mt-3 leading-relaxed max-w-md">{outcome?.stripe?.message}</p>
                      <p className="text-[#6B7280] mt-2">Thanks for staying with {outcome?.org_name}. 💚</p>
                    </>
                  ) : (
                    <>
                      <div className="h-14 w-14 rounded-2xl bg-[#111827] flex items-center justify-center text-white mb-6">
                        <Heart className="h-7 w-7" />
                      </div>
                      <h1 className="font-portal-head text-3xl md:text-4xl font-bold text-[#111827] leading-tight" data-testid="goodbye-heading">
                        We're sad to see you go
                      </h1>
                      <p className="text-[#6B7280] mt-3 leading-relaxed max-w-md">
                        Your subscription will remain active until the end of your billing period, then cancel automatically. {outcome?.stripe?.message}
                      </p>
                      <p className="text-[#6B7280] mt-2">You're always welcome back.</p>
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Right: calming visual */}
      <div className="hidden lg:block lg:w-2/5 relative">
        <img src={SIDE_IMAGE} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
      </div>
    </div>
  );
}
