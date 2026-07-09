import React, { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, X, Loader2, Gift, Percent, PauseCircle, Sparkles } from "lucide-react";
import DashboardLayout from "@/components/DashboardLayout";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

const REASONS = ["Too expensive", "Missing features", "Not using it enough", "Switching to a competitor", "Technical issues"];
const TYPE_META = {
  discount: { icon: Percent, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  pause: { icon: PauseCircle, color: "text-sky-400", bg: "bg-sky-500/10" },
  bonus: { icon: Sparkles, color: "text-amber-400", bg: "bg-amber-500/10" },
};

const emptyForm = { type: "discount", value: "", description: "", trigger_reason: "", discount_percent: 50, pause_days: 30, active: true };

function OfferModal({ open, onClose, onSaved, editing }) {
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (editing) setForm({ ...emptyForm, ...editing });
    else setForm(emptyForm);
  }, [editing, open]);

  if (!open) return null;
  const upd = (k, v) => setForm({ ...form, [k]: v });

  const save = async () => {
    if (!form.value.trim()) { toast.error("Enter an offer headline"); return; }
    setSaving(true);
    try {
      const payload = {
        type: form.type,
        value: form.value,
        description: form.description,
        trigger_reason: form.trigger_reason || null,
        discount_percent: form.type === "discount" ? Number(form.discount_percent) : null,
        pause_days: form.type === "pause" ? Number(form.pause_days) : null,
        active: form.active,
      };
      if (editing) await api.patch(`/offers/${editing.id}`, payload);
      else await api.post("/offers", payload);
      toast.success(editing ? "Offer updated" : "Offer created");
      onSaved();
      onClose();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const inputCls = "w-full rounded-lg bg-white/5 border border-white/15 px-3 py-2.5 text-white text-sm outline-none focus:ring-2 focus:ring-emerald-500 transition-shadow";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" data-testid="offer-modal">
      <div className="w-full max-w-lg cg-surface rounded-2xl border border-white/10 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-dash-head text-white text-lg font-semibold">{editing ? "Edit offer" : "New retention offer"}</h3>
          <button onClick={onClose} data-testid="close-modal-button" className="text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-400">Offer type</label>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {["discount", "pause", "bonus"].map((t) => (
                <button key={t} onClick={() => upd("type", t)} data-testid={`offer-type-${t}`}
                  className={`rounded-lg border px-3 py-2 text-sm capitalize transition-colors ${form.type === t ? "border-emerald-500 bg-emerald-500/10 text-emerald-400" : "border-white/15 text-slate-400 hover:bg-white/5"}`}>
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">Headline</label>
            <input className={inputCls} data-testid="offer-value-input" value={form.value} onChange={(e) => upd("value", e.target.value)} placeholder="50% off for 2 months" />
          </div>
          <div>
            <label className="text-xs text-slate-400">Description</label>
            <input className={inputCls} data-testid="offer-description-input" value={form.description} onChange={(e) => upd("description", e.target.value)} placeholder="Shown to the customer under the headline" />
          </div>
          {form.type === "discount" && (
            <div>
              <label className="text-xs text-slate-400">Discount percent</label>
              <input type="number" min="1" max="100" className={inputCls} data-testid="offer-discount-input" value={form.discount_percent} onChange={(e) => upd("discount_percent", e.target.value)} />
            </div>
          )}
          {form.type === "pause" && (
            <div>
              <label className="text-xs text-slate-400">Pause duration (days)</label>
              <select className={inputCls} data-testid="offer-pause-select" value={form.pause_days} onChange={(e) => upd("pause_days", e.target.value)}>
                <option value={30}>30 days</option>
                <option value={60}>60 days</option>
              </select>
            </div>
          )}
          <div>
            <label className="text-xs text-slate-400">Trigger reason (optional)</label>
            <select className={inputCls} data-testid="offer-trigger-select" value={form.trigger_reason || ""} onChange={(e) => upd("trigger_reason", e.target.value)}>
              <option value="">Any reason</option>
              {REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onClose} className="rounded-lg border border-white/15 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 transition-colors">Cancel</button>
          <button onClick={save} disabled={saving} data-testid="save-offer-button"
            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-[#0b0f19] hover:bg-emerald-400 transition-colors disabled:opacity-60">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null} {editing ? "Save changes" : "Create offer"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Offers() {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = () => {
    api.get("/offers").then((r) => setOffers(r.data)).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const toggle = async (o) => {
    try {
      await api.patch(`/offers/${o.id}`, { active: !o.active });
      setOffers((prev) => prev.map((x) => (x.id === o.id ? { ...x, active: !x.active } : x)));
    } catch { toast.error("Could not update"); }
  };

  const remove = async (o) => {
    try {
      await api.delete(`/offers/${o.id}`);
      setOffers((prev) => prev.filter((x) => x.id !== o.id));
      toast.success("Offer deleted");
    } catch { toast.error("Delete failed"); }
  };

  return (
    <DashboardLayout title="Offer Manager" subtitle="Create the incentives shown during cancellation">
      <div className="flex justify-between items-center mb-6">
        <p className="text-slate-400 text-sm max-w-lg">Offers are matched to the reason a customer selects. If none match, the first active discount is used as a fallback.</p>
        <button onClick={() => { setEditing(null); setModalOpen(true); }} data-testid="new-offer-button"
          className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-[#0b0f19] hover:bg-emerald-400 transition-colors whitespace-nowrap">
          <Plus className="h-4 w-4" /> New offer
        </button>
      </div>

      {loading ? (
        <div className="text-slate-500">Loading…</div>
      ) : offers.length === 0 ? (
        <div className="cg-surface rounded-xl border border-white/10 p-12 text-center">
          <Gift className="h-8 w-8 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No offers yet. Create your first retention offer.</p>
        </div>
      ) : (
        <div className="cg-surface rounded-xl border border-white/10 overflow-hidden" data-testid="offers-table">
          <div className="grid grid-cols-12 px-6 py-3 border-b border-white/10 cg-overline text-slate-500 text-[0.65rem]">
            <div className="col-span-4">Offer</div>
            <div className="col-span-3">Trigger reason</div>
            <div className="col-span-2">Claims</div>
            <div className="col-span-2">Active</div>
            <div className="col-span-1 text-right">Actions</div>
          </div>
          {offers.map((o) => {
            const meta = TYPE_META[o.type] || TYPE_META.bonus;
            const Icon = meta.icon;
            return (
              <div key={o.id} data-testid={`offer-row-${o.id}`}
                className="grid grid-cols-12 items-center px-6 py-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                <div className="col-span-4 flex items-center gap-3">
                  <div className={`h-9 w-9 rounded-lg ${meta.bg} flex items-center justify-center shrink-0`}>
                    <Icon className={`h-4 w-4 ${meta.color}`} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-sm truncate">{o.value}</p>
                    <p className="text-xs text-slate-500 truncate">{o.description}</p>
                  </div>
                </div>
                <div className="col-span-3 text-sm text-slate-400">{o.trigger_reason || "Any reason"}</div>
                <div className="col-span-2 text-sm text-slate-300">{o.claim_count}</div>
                <div className="col-span-2">
                  <button onClick={() => toggle(o)} data-testid={`toggle-offer-${o.id}`}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${o.active ? "bg-emerald-500" : "bg-white/20"}`}>
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${o.active ? "translate-x-6" : "translate-x-1"}`} />
                  </button>
                </div>
                <div className="col-span-1 flex justify-end gap-1">
                  <button onClick={() => { setEditing(o); setModalOpen(true); }} data-testid={`edit-offer-${o.id}`}
                    className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => remove(o)} data-testid={`delete-offer-${o.id}`}
                    className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-white/5 transition-colors"><Trash2 className="h-4 w-4" /></button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <OfferModal open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} editing={editing} />
    </DashboardLayout>
  );
}
