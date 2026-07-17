"use client";

import { useEffect, useState } from "react";
import TrendLine, { TrendPoint } from "@/components/charts/TrendLine";
import { EpdsEntry, loadEpdsHistory } from "@/lib/epds";

type MoodEntry = { mood: string; date: string };
type CheckinEntry = { date: string; risk: string; elevated: boolean };
type ConcernEntry = { date: string; score: number; level: string };

function formatLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function ProgressDashboard() {
  const [epdsHistory, setEpdsHistory] = useState<EpdsEntry[]>([]);
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([]);
  const [checkinHistory, setCheckinHistory] = useState<CheckinEntry[]>([]);
  const [concernHistory, setConcernHistory] = useState<ConcernEntry[]>([]);

  useEffect(() => {
    setEpdsHistory(loadEpdsHistory());
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

  return (
    <>
      <div className="section-h">How your wellness check has been going</div>
      <div className="card">
        <TrendLine data={epdsPoints} domain={[0, 30]} referenceValue={13} referenceLabel="extra support may help" />
        <div className="subtext">Lower generally means fewer symptoms. The dashed line marks where extra support is often recommended.</div>
      </div>

      <div className="section-h" style={{ marginTop: 20 }}>Mood check-ins</div>
      <div className="card">
        {Object.keys(moodCounts).length === 0 ? (
          <div className="subtext">No mood check-ins yet — log one from Self-care.</div>
        ) : (
          <div className="mood-history">
            {Object.entries(moodCounts).map(([mood, count]) => (
              <span key={mood} className="mood-pill">{mood} · {count}</span>
            ))}
          </div>
        )}
      </div>

      {checkinHistory.length > 0 && (
        <>
          <div className="section-h" style={{ marginTop: 20 }}>Check-in history</div>
          <div className="card">
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

      <div className="subtext" style={{ marginTop: 16 }}>
        Everything here stays on this device — nothing is sent anywhere.
      </div>
    </>
  );
}
