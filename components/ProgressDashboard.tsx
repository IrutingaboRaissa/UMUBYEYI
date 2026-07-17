"use client";

import { useEffect, useState } from "react";
import TrendLine, { TrendPoint } from "@/components/charts/TrendLine";
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

export default function ProgressDashboard() {
  const [epdsHistory, setEpdsHistory] = useState<EpdsEntry[]>([]);
  const [streak, setStreak] = useState<EpdsStreak>({ count: 0, lastDate: "" });
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([]);
  const [checkinHistory, setCheckinHistory] = useState<CheckinEntry[]>([]);
  const [concernHistory, setConcernHistory] = useState<ConcernEntry[]>([]);

  useEffect(() => {
    setEpdsHistory(loadEpdsHistory());
    setStreak(loadStreak());
    try { setMoodHistory(JSON.parse(localStorage.getItem("umubyeyi_moods_v1") || "[]")); } catch { /* ignore */ }
    try { setCheckinHistory(JSON.parse(localStorage.getItem("umubyeyi_checkin_v1") || "[]")); } catch { /* ignore */ }
    try { setConcernHistory(JSON.parse(localStorage.getItem("umubyeyi_concern_v1") || "[]")); } catch { /* ignore */ }
  }, []);

  const epdsPoints: TrendPoint[] = [...epdsHistory].reverse()
    .map((e) => ({ date: e.date, value: e.total, label: formatLabel(e.date) }));
  const concernPoints: TrendPoint[] = [...concernHistory].reverse()
    .map((e) => ({ date: e.date, value: Math.round(e.score * 100), label: formatLabel(e.date) }));

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

  return (
    <>
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
          <div className="subtext">No mood check-ins yet — log one from Self-care.</div>
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
              {checkinHistory.slice(0, 10).map((c, i) => (
                <span key={`${c.date}-${i}`} className="mood-pill">
                  {formatLabel(c.date)} · {c.elevated ? "support suggested" : "steady"}
                </span>
              ))}
            </div>
          </div>
        </>
      )}

      {concernPoints.length > 0 && (
        <>
          <div className="section-h" style={{ marginTop: 20 }}>How your chats have been feeling</div>
          <div className="card">
            <TrendLine data={concernPoints} domain={[0, 100]} color="#356B7D" />
            <div className="subtext">A rough sense of how heavy your recent messages sounded — just a pattern, not a diagnosis.</div>
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
        Everything here stays on this device — nothing is sent anywhere.
      </div>
    </>
  );
}
