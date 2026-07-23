"use client";

import { useEffect, useState } from "react";
import TrendLine from "@/components/charts/TrendLine";
import { aggregateTrend } from "@/lib/trends";
import { EpdsBand, EpdsEntry, EpdsStreak, loadEpdsHistory, loadStreak } from "@/lib/epds";

type MoodEntry = { mood: string; date: string };
type CheckinEntry = { date: string; risk: string; elevated: boolean };
type ConcernEntry = { date: string; score: number; level: string };

const BAND_LABEL: Record<EpdsBand, string> = {
  low: "Steady",
  medium: "Some symptoms to watch",
  high: "Extra support suggested",
};

function formatLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86400000));
}

const NUDGE_SNOOZE_KEY = "umubyeyi_weekly_nudge_snoozed_until_v1";
const CHECKIN_LIST_COLLAPSED = 10;

export default function ProgressDashboard({ onGoToSelfcare }: { onGoToSelfcare?: () => void }) {
  const [epdsHistory, setEpdsHistory] = useState<EpdsEntry[]>([]);
  const [streak, setStreak] = useState<EpdsStreak>({ count: 0, lastDate: "" });
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([]);
  const [checkinHistory, setCheckinHistory] = useState<CheckinEntry[]>([]);
  const [concernHistory, setConcernHistory] = useState<ConcernEntry[]>([]);
  const [nudgeSnoozedUntil, setNudgeSnoozedUntil] = useState("");
  const [showAllCheckins, setShowAllCheckins] = useState(false);

  useEffect(() => {
    setEpdsHistory(loadEpdsHistory());
    setStreak(loadStreak());
    try { setMoodHistory(JSON.parse(localStorage.getItem("umubyeyi_moods_v1") || "[]")); } catch { /* ignore */ }
    try { setCheckinHistory(JSON.parse(localStorage.getItem("umubyeyi_checkin_v1") || "[]")); } catch { /* ignore */ }
    try { setConcernHistory(JSON.parse(localStorage.getItem("umubyeyi_concern_v1") || "[]")); } catch { /* ignore */ }
    try { setNudgeSnoozedUntil(localStorage.getItem(NUDGE_SNOOZE_KEY) || ""); } catch { /* ignore */ }
  }, []);

  // One point per day while history is short, one per week once it would otherwise be a
  // wall of same-day dots -- see lib/trends.ts.
  const epdsPoints = aggregateTrend(epdsHistory.map((e) => ({ date: e.date, value: e.total })));
  const concernPoints = aggregateTrend(
    concernHistory.map((e) => ({ date: e.date, value: Math.round(e.score * 100) }))
  );

  const moodCounts = moodHistory.reduce<Record<string, number>>((acc, m) => {
    acc[m.mood] = (acc[m.mood] || 0) + 1;
    return acc;
  }, {});
  const rankedMoods = Object.entries(moodCounts).sort((a, b) => b[1] - a[1]);
  const topMood = rankedMoods[0];

  const latestEpds = epdsHistory[0];
  const previousEpds = epdsHistory[1];
  const epdsDelta = latestEpds && previousEpds ? latestEpds.total - previousEpds.total : null;

  const firstTrackedDate = [...epdsHistory.map((e) => e.date), ...moodHistory.map((m) => m.date),
    ...checkinHistory.map((c) => c.date)].sort()[0];
  const daysTracked = firstTrackedDate ? Math.max(1, daysSince(firstTrackedDate)) : 0;

  const hasAnyData = epdsHistory.length > 0 || moodHistory.length > 0 || checkinHistory.length > 0;

  // A deliberate weekly rhythm, not just passive charting: nudge if it's been a week since
  // any of mood / guided check-in / wellness test, so there's always at least one fresh
  // point a week rather than relying on how much the mother happens to chat.
  const lastActivityDate = [...moodHistory.map((m) => m.date), ...checkinHistory.map((c) => c.date),
    ...epdsHistory.map((e) => e.date)].sort().reverse()[0];
  const daysSinceActivity = lastActivityDate ? daysSince(lastActivityDate) : null;
  const isSnoozed = nudgeSnoozedUntil !== "" && new Date(nudgeSnoozedUntil).getTime() > Date.now();
  const showWeeklyNudge = hasAnyData && daysSinceActivity !== null && daysSinceActivity >= 7 && !isSnoozed;

  const snoozeNudge = () => {
    const until = new Date(Date.now() + 7 * 86400000).toISOString();
    setNudgeSnoozedUntil(until);
    try { localStorage.setItem(NUDGE_SNOOZE_KEY, until); } catch { /* ignore */ }
  };

  return (
    <>
      {showWeeklyNudge && (
        <div className="card" style={{ marginBottom: 14 }}>
          <b>It&apos;s been {daysSinceActivity} days since your last check-in</b>
          <div className="subtext" style={{ marginTop: 4, marginBottom: 10 }}>
            A quick weekly check-in keeps your trends meaningful, even on quiet weeks.
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {onGoToSelfcare && (
              <button className="btn btn-sm btn-primary" onClick={onGoToSelfcare}>Log how you feel</button>
            )}
            <button className="btn btn-sm" onClick={snoozeNudge}>Remind me next week</button>
          </div>
        </div>
      )}

      {hasAnyData && (
        <div className="stat-row">
          <div className="stat-tile">
            <div className="stat-value">{streak.count}</div>
            <div className="stat-label">Wellness check-in streak</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{epdsHistory.length}</div>
            <div className="stat-label">Wellness tests taken</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{moodHistory.length}</div>
            <div className="stat-label">Mood check-ins logged</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{daysTracked}</div>
            <div className="stat-label">Day{daysTracked === 1 ? "" : "s"} since you started</div>
          </div>
        </div>
      )}

      {latestEpds && (
        <div className={`card ${latestEpds.band === "high" ? "danger" : ""}`} style={{ marginTop: hasAnyData ? 14 : 0 }}>
          <b>Most recent wellness check: {BAND_LABEL[latestEpds.band]}</b>
          <div className="subtext" style={{ marginTop: 4 }}>
            {formatLabel(latestEpds.date)} · score {latestEpds.total}/30
            {epdsDelta !== null && epdsDelta !== 0 && (
              <> · {epdsDelta > 0 ? `up ${epdsDelta}` : `down ${Math.abs(epdsDelta)}`} since your last check</>
            )}
          </div>
        </div>
      )}

      <div className="section-h" style={{ marginTop: 20 }}>How your wellness check has been going</div>
      <div className="card">
        <TrendLine data={epdsPoints} domain={[0, 30]} referenceValue={13} referenceLabel="extra support may help" />
        <div className="subtext">Lower generally means fewer symptoms. The dashed line marks where extra support is often recommended.</div>
      </div>

      <div className="section-h" style={{ marginTop: 20 }}>Mood check-ins</div>
      <div className="card">
        {rankedMoods.length === 0 ? (
          <div className="subtext">No mood check-ins yet. Log one from Self-care.</div>
        ) : (
          <>
            <div className="subtext" style={{ marginBottom: 8 }}>
              Most often: <b>{topMood[0]}</b> ({topMood[1]} of {moodHistory.length} check-ins)
            </div>
            <div className="mood-history">
              {rankedMoods.map(([mood, count]) => (
                <span key={mood} className="mood-pill">{mood} · {count}</span>
              ))}
            </div>
          </>
        )}
      </div>

      {checkinHistory.length > 0 && (
        <>
          <div className="section-h" style={{ marginTop: 20 }}>Check-in history</div>
          <div className="card">
            <div className="subtext" style={{ marginBottom: 8 }}>
              {checkinHistory.filter((c) => c.elevated).length} of {checkinHistory.length} guided check-ins suggested extra support.
            </div>
            <div className="mood-history">
              {(showAllCheckins ? checkinHistory : checkinHistory.slice(0, CHECKIN_LIST_COLLAPSED)).map((c, i) => (
                <span key={`${c.date}-${i}`} className="mood-pill">
                  {formatLabel(c.date)} · {c.elevated ? "support suggested" : "steady"}
                </span>
              ))}
            </div>
            {checkinHistory.length > CHECKIN_LIST_COLLAPSED && (
              <button
                type="button"
                className="btn btn-sm"
                style={{ marginTop: 8 }}
                onClick={() => setShowAllCheckins((v) => !v)}
              >
                {showAllCheckins ? "Show fewer" : `Show all ${checkinHistory.length}`}
              </button>
            )}
          </div>
        </>
      )}

      {concernPoints.length > 0 && (
        <>
          <div className="section-h" style={{ marginTop: 20 }}>How your chats have been feeling</div>
          <div className="card">
            <TrendLine data={concernPoints} domain={[0, 100]} color="#356B7D" />
            <div className="subtext">A rough sense of how heavy your recent messages sounded. Just a pattern, not a diagnosis.</div>
          </div>
        </>
      )}

      {!hasAnyData && (
        <div className="card">
          <div className="subtext">
            Nothing tracked yet. Take the wellness test, log a mood in Self-care, or run a guided check-in to start seeing your trends here.
          </div>
        </div>
      )}

      <div className="subtext" style={{ marginTop: 16 }}>
        Everything here stays on this device. Nothing is sent anywhere.
      </div>
    </>
  );
}
