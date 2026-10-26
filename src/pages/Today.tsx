import { ArrowRight, Flame, Keyboard } from "lucide-react";
import { useEffect, useMemo } from "react";
import { prefetch, useAtlas } from "../atlas/context";
import { go } from "../lib/router";
import { cue } from "../lib/sound";
import { buildSession, todayPlan } from "../store/session";
import { dayKey, store, useStore } from "../store/store";

export function streakOf(days: Record<string, { r: number }>) {
  let n = 0;
  const d = new Date();
  if (!(days[dayKey(d)]?.r > 0)) d.setDate(d.getDate() - 1);
  while (days[dayKey(d)]?.r > 0) {
    n++;
    d.setDate(d.getDate() - 1);
  }
  return n;
}

export function Today() {
  const atlas = useAtlas();
  const progress = useStore((s) => s.progress);
  const settings = useStore((s) => s.settings);
  const plan = useMemo(() => todayPlan(atlas, progress, settings), [atlas, progress, settings]);

  // Warm the first cards of today's journey so the session opens instantly.
  const firstIds = [...plan.due.slice(0, 4), ...plan.fresh.slice(0, 6)].join(",");
  useEffect(() => {
    const ids = firstIds.split(",").filter(Boolean);
    const t = window.setTimeout(() => void prefetch(atlas, ids), 800);
    return () => window.clearTimeout(t);
  }, [atlas, firstIds]);

  const today = progress.days[dayKey()];
  const streak = streakOf(progress.days);
  const active = progress.session && !progress.session.finished ? progress.session : null;
  const doneToday = today?.r ?? 0;

  const start = (opts?: { reviewOnly?: boolean; extra?: number }) => {
    if (!active) {
      const s = buildSession(atlas, progress, opts?.extra ? { ...settings, dailyNew: (today?.n ?? 0) + opts.extra } : settings, { reviewOnly: opts?.reviewOnly });
      if (!s.steps.length) return;
      store.progress((p) => ({ ...p, session: s }));
    }
    if (settings.sfx) void cue("start");
    go({ page: "learn" });
  };

  const total = plan.due.length + plan.fresh.length;

  return (
    <div className="page today">
      <section className="journey-section">
        <div className="journey-info">
          {active ? (
            <p className="journey-desc">旅程进行中 · 还剩 <b>{active.steps.length - active.index}</b> 步</p>
          ) : total > 0 ? (
            <p className="journey-desc">
              {plan.due.length > 0 && <>复习 <b>{plan.due.length}</b></>}
              {plan.due.length > 0 && plan.fresh.length > 0 && " · "}
              {plan.fresh.length > 0 && <>新词 <b>{plan.fresh.length}</b></>}
              {" · 约 "}{plan.minutes} 分钟
            </p>
          ) : (
            <p className="journey-desc">今日已完成</p>
          )}
          <div className="streak-line">
            <Flame size={14} />
            <span>连续 {streak} 天</span>
            <span className="muted">· 今日答题 {doneToday}</span>
          </div>
        </div>

        <div className="journey-actions">
          {active || total > 0 ? (
            <button className="btn btn-primary" onClick={() => start()}>
              {active ? "继续" : "开始"} <ArrowRight size={18} />
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => start({ extra: 5 })}>
              再学 5 个 <ArrowRight size={18} />
            </button>
          )}
          {!active && plan.due.length > 0 && plan.fresh.length > 0 && (
            <button className="btn btn-outline" onClick={() => start({ reviewOnly: true })}>
              只复习
            </button>
          )}
          {!active && total === 0 && (
            <button className="btn btn-outline" onClick={() => go({ page: "practice" })}>
              <Keyboard size={16} /> 打字练习
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
