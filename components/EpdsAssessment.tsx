"use client";

import { useState } from "react";
import {
  EPDS_ITEM10_INDEX, EPDS_ITEMS, EpdsBand, EpdsEntry, RESPONSE_LABELS,
  bumpStreak, classifyBand, computeTotal, isItem10Flagged, loadStreak, saveEpdsEntry,
} from "@/lib/epds";

const BAND_COPY: Record<EpdsBand, { title: string; body: string }> = {
  low: {
    title: "You're doing okay right now",
    body: "Nothing here points to strong postpartum symptoms today — that's good to hear. Feelings can shift from week to week, so it's worth checking back in with yourself from time to time.",
  },
  medium: {
    title: "A few things worth keeping an eye on",
    body: "Your answers show some signs that are worth paying attention to. This isn't a diagnosis, but it may help to talk with someone you trust, or a health worker, about how you've been feeling lately.",
  },
  high: {
    title: "It looks like you could use some extra support",
    body: "This isn't a diagnosis, but your answers look similar to mothers who often benefit from talking to a health worker soon. Please don't wait to reach out — you don't have to carry this alone.",
  },
};

export default function EpdsAssessment({ onCrisis }: { onCrisis: () => void }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>(() => Array(EPDS_ITEMS.length).fill(-1));
  const [result, setResult] = useState<EpdsEntry | null>(null);
  const [streakCount, setStreakCount] = useState(() => loadStreak().count);

  const item = EPDS_ITEMS[stepIndex];
  const answered = answers[stepIndex] !== -1;

  const selectOption = (optionIndex: number) => {
    const next = [...answers];
    next[stepIndex] = optionIndex;
    setAnswers(next);

    if (stepIndex === EPDS_ITEM10_INDEX && optionIndex > 0) {
      onCrisis();
    }

    if (stepIndex < EPDS_ITEMS.length - 1) {
      setStepIndex(stepIndex + 1);
    } else {
      const total = computeTotal(next);
      const entry: EpdsEntry = {
        date: new Date().toISOString(),
        total,
        band: classifyBand(total),
        item10Flag: isItem10Flagged(next),
      };
      saveEpdsEntry(entry);
      setStreakCount(bumpStreak().count);
      setResult(entry);
    }
  };

  const restart = () => {
    setAnswers(Array(EPDS_ITEMS.length).fill(-1));
    setStepIndex(0);
    setResult(null);
  };

  if (result) {
    const copy = BAND_COPY[result.band];
    return (
      <div className={`card epds-result ${result.band === "high" ? "danger" : ""}`}>
        <b style={{ fontSize: 16 }}>{copy.title}</b>
        <p style={{ marginTop: 10 }}>{copy.body}</p>
        <div className="disc" style={{ marginTop: 12 }}>
          This is a wellness check, not a medical diagnosis.
          {result.item10Flag && " If you are in danger, please use the Help button above right now."}
        </div>
        <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={restart}>
          Take it again
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="epds-progress">
        <div className="epds-progress-fill" style={{ width: `${((stepIndex + (answered ? 1 : 0)) / EPDS_ITEMS.length) * 100}%` }} />
      </div>
      <div className="epds-step-label">
        Question {stepIndex + 1} of {EPDS_ITEMS.length}
        {streakCount > 0 && <span className="epds-streak"> · You've checked in {streakCount} time{streakCount === 1 ? "" : "s"}</span>}
      </div>
      <div className="tt" style={{ marginTop: 10 }}>{item.text}</div>
      {item.reverseScored && (
        <div className="subtext" style={{ marginTop: 4 }}>
          This one's about a positive feeling — "Nearly every day" is the healthy answer here, not "Not at all."
        </div>
      )}
      <div className="epds-options">
        {RESPONSE_LABELS.map((label, i) => (
          <button key={label} type="button" className="epds-option" onClick={() => selectOption(i)}>
            {label}
          </button>
        ))}
      </div>
      {stepIndex > 0 && (
        <button type="button" className="btn btn-sm" style={{ marginTop: 14 }} onClick={() => setStepIndex(stepIndex - 1)}>
          ← Back
        </button>
      )}
      <div className="subtext" style={{ marginTop: 14 }}>
        This assessment is currently available in English only. It is separate from the guided
        check-in and does not store your individual answers — only the date and total score are
        saved, on this device only.
      </div>
    </div>
  );
}
