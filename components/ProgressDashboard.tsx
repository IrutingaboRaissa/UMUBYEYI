"use client";

import { useEffect, useState } from "react";
import TrendLine from "@/components/charts/TrendLine";
import { aggregateTrend } from "@/lib/trends";
import { EpdsBand, EpdsEntry, EpdsStreak, deriveStreak, loadEpdsHistory } from "@/lib/epds";
import { MOOD_LABEL } from "@/lib/chat";
import {
  MoodEntry, CheckinEntry, ConcernEntry,
  loadMoodHistory, loadCheckinHistory, loadConcernHistory,
} from "@/lib/supabase/data";
import { useT, useBi } from "@/lib/language";

const BAND_LABEL: Record<EpdsBand, string> = {
  low: "Biratekanye · Steady",
  medium: "Hari ibimenyetso wagenzura · Some symptoms to watch",
  high: "Ukeneye ubufasha bwinyongera · Extra support suggested",
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
  const tr = useT();
  const bi = useBi();
  const [epdsHistory, setEpdsHistory] = useState<EpdsEntry[]>([]);
  const [streak, setStreak] = useState<EpdsStreak>({ count: 0, lastDate: "" });
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([]);
  const [checkinHistory, setCheckinHistory] = useState<CheckinEntry[]>([]);
  const [concernHistory, setConcernHistory] = useState<ConcernEntry[]>([]);
  const [nudgeSnoozedUntil, setNudgeSnoozedUntil] = useState("");
  const [showAllCheckins, setShowAllCheckins] = useState(false);

  useEffect(() => {
    try { setNudgeSnoozedUntil(localStorage.getItem(NUDGE_SNOOZE_KEY) || ""); } catch { /* ignore */ }
    loadEpdsHistory().then((history) => {
      setEpdsHistory(history);
      setStreak(deriveStreak(history));
    }).catch((err) => console.error("Failed to load wellness test history", err));
    loadMoodHistory().then(setMoodHistory).catch((err) => console.error("Failed to load mood history", err));
    loadCheckinHistory().then(setCheckinHistory).catch((err) => console.error("Failed to load check-in history", err));
    loadConcernHistory().then(setConcernHistory).catch((err) => console.error("Failed to load concern history", err));
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
          <b>{tr(`Haciye iminsi ${daysSinceActivity} udakora isuzuma`, `It's been ${daysSinceActivity} days since your last check-in`)}</b>
          <div className="subtext" style={{ marginTop: 4, marginBottom: 10 }}>
            {tr("Isuzuma rigufi buri cyumweru rifasha kubona neza uko ibintu bigenda, n'igihe nta kintu kigaragara cyane.",
              "A quick weekly check-in keeps your trends meaningful, even on quiet weeks.")}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {onGoToSelfcare && (
              <button className="btn btn-sm btn-primary" onClick={onGoToSelfcare}>{tr("Andika uko wiyumva", "Log how you feel")}</button>
            )}
            <button className="btn btn-sm" onClick={snoozeNudge}>{tr("Nyibutsa mu cyumweru gitaha", "Remind me next week")}</button>
          </div>
        </div>
      )}

      {hasAnyData && (
        <div className="stat-row">
          <div className="stat-tile">
            <div className="stat-value">{streak.count}</div>
            <div className="stat-label">{tr("Iminsi ukurikiranye", "Wellness check-in streak")}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{epdsHistory.length}</div>
            <div className="stat-label">{tr("Ibizamini wakoze", "Wellness tests taken")}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{moodHistory.length}</div>
            <div className="stat-label">{tr("Uko wiyumva wanditse", "Mood check-ins logged")}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-value">{daysTracked}</div>
            <div className="stat-label">{tr("Iminsi kuva watangira", `Day${daysTracked === 1 ? "" : "s"} since you started`)}</div>
          </div>
        </div>
      )}

      {latestEpds && (
        <div className={`card ${latestEpds.band === "high" ? "danger" : ""}`} style={{ marginTop: hasAnyData ? 14 : 0 }}>
          <b>{tr("Isuzuma rya vuba riheruka", "Most recent wellness check")}: {bi(BAND_LABEL[latestEpds.band])}</b>
          <div className="subtext" style={{ marginTop: 4 }}>
            {formatLabel(latestEpds.date)} · {tr("amanota", "score")} {latestEpds.total}/30
            {epdsDelta !== null && epdsDelta !== 0 && (
              <> · {tr(
                epdsDelta > 0 ? `hiyongereyeho ${epdsDelta}` : `hagabanutseho ${Math.abs(epdsDelta)}`,
                epdsDelta > 0 ? `up ${epdsDelta}` : `down ${Math.abs(epdsDelta)}`
              )} {tr("kuva isuzuma riheruka", "since your last check")}</>
            )}
          </div>
        </div>
      )}

      <div className="section-h" style={{ marginTop: 20 }}>{tr("Uko ikizamini cy'imibereho kigenda", "How your wellness check has been going")}</div>
      <div className="card">
        <TrendLine data={epdsPoints} domain={[0, 30]} referenceValue={13} referenceLabel={tr("ubufasha bwinshi", "extra support")} />
        <div className="subtext">
          {tr("Uko umubare ugabanuka, ni ko ibimenyetso bigabanuka. Umurongo utunganye werekana aho ubufasha bwinshi bukunze gusabwa.",
            "Lower generally means fewer symptoms. The dashed line marks where extra support is often recommended.")}
        </div>
      </div>

      <div className="section-h" style={{ marginTop: 20 }}>{tr("Uko wiyumva", "Mood check-ins")}</div>
      <div className="card">
        {rankedMoods.length === 0 ? (
          <div className="subtext">{tr("Nta kwiyumva wanditse. Andika kimwe uva ku Kwiyitaho.", "No mood check-ins yet. Log one from Self-care.")}</div>
        ) : (
          <>
            <div className="subtext" style={{ marginBottom: 8 }}>
              {tr("Akenshi cyane", "Most often")}: <b>{bi(MOOD_LABEL[topMood[0]] ?? topMood[0])}</b> ({topMood[1]} {tr("muri", "of")} {moodHistory.length})
            </div>
            <div className="mood-history">
              {rankedMoods.map(([mood, count]) => (
                <span key={mood} className="mood-pill">{bi(MOOD_LABEL[mood] ?? mood)} · {count}</span>
              ))}
            </div>
          </>
        )}
      </div>

      {checkinHistory.length > 0 && (
        <>
          <div className="section-h" style={{ marginTop: 20 }}>{tr("Amateka y'isuzuma", "Check-in history")}</div>
          <div className="card">
            <div className="subtext" style={{ marginBottom: 8 }}>
              {tr(
                `${checkinHistory.filter((c) => c.elevated).length} muri ${checkinHistory.length} mu masuzuma yagaragaje ko hakenewe ubufasha bwinshi.`,
                `${checkinHistory.filter((c) => c.elevated).length} of ${checkinHistory.length} guided check-ins suggested extra support.`
              )}
            </div>
            <div className="mood-history">
              {(showAllCheckins ? checkinHistory : checkinHistory.slice(0, CHECKIN_LIST_COLLAPSED)).map((c, i) => (
                <span key={`${c.date}-${i}`} className="mood-pill">
                  {formatLabel(c.date)} · {c.elevated ? tr("hakenewe ubufasha", "support suggested") : tr("biratekanye", "steady")}
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
                {showAllCheckins ? tr("Garuka ku bike", "Show fewer") : tr(`Byose ${checkinHistory.length}`, `Show all ${checkinHistory.length}`)}
              </button>
            )}
          </div>
        </>
      )}

      {concernPoints.length > 0 && (
        <>
          <div className="section-h" style={{ marginTop: 20 }}>{tr("Uko ibiganiro byagenze", "How your chats have been feeling")}</div>
          <div className="card">
            <TrendLine data={concernPoints} domain={[0, 100]} color="#356B7D" />
            <div className="subtext">
              {tr("Igitekerezo rusange ku buremere bw'ubutumwa bwawe bwa vuba. Ni ishusho gusa, ntabwo ari isuzuma ry'ubuvuzi.",
                "A rough sense of how heavy your recent messages sounded. Just a pattern, not a diagnosis.")}
            </div>
          </div>
        </>
      )}

      {!hasAnyData && (
        <div className="card">
          <div className="subtext">
            {tr("Nta kintu cyanditswe kugeza ubu. Fata ikizamini cy'imibereho, wandike uko wiyumva ku Kwiyitaho, cyangwa ukore isuzuma ryoroheje kugira ngo utangire kubona uko ugenda hano.",
              "Nothing tracked yet. Take the wellness test, log a mood in Self-care, or run a guided check-in to start seeing your trends here.")}
          </div>
        </div>
      )}

      <div className="subtext" style={{ marginTop: 16 }}>
        {tr("Ibi byose bibikwa kuri konti yawe irinzwe, kandi ubona uko ugenda kuri mudasobwa iyo ari yo yose winjiyeho.",
          "Everything here is saved to your secure account, so your trends follow you across any device you sign into.")}
      </div>
    </>
  );
}
