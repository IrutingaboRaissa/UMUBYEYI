"use client";

import { useState } from "react";
import {
  EPDS_ITEM10_INDEX, EPDS_ITEMS, EpdsBand, EpdsEntry, RESPONSE_LABELS,
  bumpStreak, classifyBand, computeTotal, isItem10Flagged, loadStreak, saveEpdsEntry,
} from "@/lib/epds";
import { useT } from "@/lib/language";

// Band interpretation copy is this project's own authored wording (not the clinical
// instrument's item text), so unlike EPDS_ITEMS/RESPONSE_LABELS below it's fine to
// translate -- same category as the rest of the app's bilingual UI copy.
const BAND_COPY: Record<EpdsBand, { titleRw: string; titleEn: string; bodyRw: string; bodyEn: string }> = {
  low: {
    titleRw: "Ubu uri mu mimerere myiza",
    titleEn: "You're doing okay right now",
    bodyRw: "Nta kimenyetso gikomeye cy'ibibazo byo nyuma yo kubyara kigaragara uyu munsi. Ni byiza kubyumva. Uko wiyumva bishobora guhinduka buri cyumweru, bityo birakwiye kongera kwisuzuma buri gihe.",
    bodyEn: "Nothing here points to strong postpartum symptoms today. That's good to hear. Feelings can shift from week to week, so it's worth checking back in with yourself from time to time.",
  },
  medium: {
    titleRw: "Hari ibintu bike wagenzura",
    titleEn: "A few things worth keeping an eye on",
    bodyRw: "Ibisubizo byawe byerekana ibimenyetso bike bikwiye kwitabwaho. Iri si isuzuma ry'ubuvuzi, ariko byaba byiza kuvugana n'umuntu wizeye, cyangwa umukozi w'ubuzima, ku byerekeye uko wiyumva vuba aha.",
    bodyEn: "Your answers show some signs that are worth paying attention to. This isn't a diagnosis, but it may help to talk with someone you trust, or a health worker, about how you've been feeling lately.",
  },
  high: {
    titleRw: "Bisa n'aho ukeneye ubufasha bwinyongera",
    titleEn: "It looks like you could use some extra support",
    bodyRw: "Iri si isuzuma ry'ubuvuzi, ariko ibisubizo byawe bisa n'aby'ababyeyi bakunze kunguka mu kuvugana n'umukozi w'ubuzima vuba. Nyamuneka ntutinde kwegera ubufasha. Ntugomba kubyihanganira wenyine.",
    bodyEn: "This isn't a diagnosis, but your answers look similar to mothers who often benefit from talking to a health worker soon. Please don't wait to reach out. You don't have to carry this alone.",
  },
};

export default function EpdsAssessment({ onCrisis }: { onCrisis: () => void }) {
  const tr = useT();
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
        <b style={{ fontSize: 16 }}>{tr(copy.titleRw, copy.titleEn)}</b>
        <p style={{ marginTop: 10 }}>{tr(copy.bodyRw, copy.bodyEn)}</p>
        <div className="disc" style={{ marginTop: 12 }}>
          {tr("Iri ni isuzuma ry'imibereho myiza, si isuzuma ry'ubuvuzi.", "This is a wellness check, not a medical diagnosis.")}
          {result.item10Flag && " " + tr("Niba uri mu kaga, koresha buto ya Ubufasha hejuru nonaha.", "If you are in danger, please use the Help button above right now.")}
        </div>
        <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={restart}>
          {tr("Ongera ukore", "Take it again")}
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
        {tr(`Ikibazo ${stepIndex + 1} muri ${EPDS_ITEMS.length}`, `Question ${stepIndex + 1} of ${EPDS_ITEMS.length}`)}
        {streakCount > 0 && (
          <span className="epds-streak">
            {" · "}
            {tr(`Wisuzumye inshuro ${streakCount}`, `You've checked in ${streakCount} time${streakCount === 1 ? "" : "s"}`)}
          </span>
        )}
      </div>
      <div className="tt" style={{ marginTop: 10 }}>{tr(item.textRw, item.text)}</div>
      {item.reverseScored && (
        <div className="subtext" style={{ marginTop: 4 }}>
          {tr(
            `Iki kibazo kijyanye n'ibyiyumvo byiza: "${RESPONSE_LABELS[3][1]}" ni cyo gisubizo cyiza hano, si "${RESPONSE_LABELS[0][1]}."`,
            `This one's about a positive feeling: "${RESPONSE_LABELS[3][0]}" is the healthy answer here, not "${RESPONSE_LABELS[0][0]}."`
          )}
        </div>
      )}
      <div className="epds-options">
        {RESPONSE_LABELS.map(([en, rw], i) => (
          <button key={en} type="button" className="epds-option" onClick={() => selectOption(i)}>
            {tr(rw, en)}
          </button>
        ))}
      </div>
      {stepIndex > 0 && (
        <button type="button" className="btn btn-sm" style={{ marginTop: 14 }} onClick={() => setStepIndex(stepIndex - 1)}>
          {tr("← Inyuma", "← Back")}
        </button>
      )}
      <div className="subtext" style={{ marginTop: 14 }}>
        {tr(
          "Ibisobanuro by'Ikinyarwanda by'iki kizamini cy'ubuvuzi (EPDS-10) byakozwe n'iki gikorwa ubwacyo, kandi ntibyemejwe n'inzobere mu buvuzi cyangwa umuvugizi w'Ikinyarwanda nk'ururimi rwavukiyemo -- ntibigomba gufatwa nk'ibisa n'icyongereza cy'umwimerere ku buryo bunoze. Iki kizamini gitandukanye n'isuzuma ryoroheje, kandi ntikibika ibisubizo byawe kuri buri kibazo -- itariki n'amanota rusange gusa ni byo bibikwa, kuri iyi terefone gusa.",
          "The Kinyarwanda wording of this clinical instrument (EPDS-10) was authored by this project and has not been reviewed by a clinician or a native Kinyarwanda speaker -- it should not be assumed to precisely match the original validated English. It is separate from the guided check-in and does not store your individual answers. Only the date and total score are saved, on this device only."
        )}
      </div>
    </div>
  );
}
