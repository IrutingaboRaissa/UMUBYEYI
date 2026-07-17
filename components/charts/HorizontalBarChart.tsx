"use client";

import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type Contribution = {
  feature: string;
  feature_label: string;
  contribution: number;
  direction: "increases" | "decreases";
};

const INCREASE_COLOR = "#C9705A"; // same hue as the existing danger accents
const DECREASE_COLOR = "#356B7D"; // same hue as the existing bot-bubble text

function strengthWord(ratio: number): string {
  if (ratio >= 0.66) return "Strongly";
  if (ratio >= 0.33) return "Somewhat";
  return "Slightly";
}

export default function HorizontalBarChart({ data }: { data: Contribution[] }) {
  if (data.length === 0) return null;
  const magnitude = Math.max(...data.map((d) => Math.abs(d.contribution)), 0.01);

  return (
    <div>
      <div style={{ display: "flex", gap: 18, marginBottom: 6, fontSize: 12.5, color: "#4A3F47" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 3, background: INCREASE_COLOR, display: "inline-block" }} />
          Pointed toward extra support
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 3, background: DECREASE_COLOR, display: "inline-block" }} />
          Pointed toward things being steady
        </span>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(120, data.length * 34)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
          <XAxis type="number" domain={[-magnitude * 1.15, magnitude * 1.15]} hide />
          <YAxis type="category" dataKey="feature_label" width={150}
            tick={{ fontSize: 12, fill: "#4A3F47" }} axisLine={false} tickLine={false} />
          <ReferenceLine x={0} stroke="#C9B9C2" />
          <Tooltip
            contentStyle={{ background: "#FCF8F2", border: "1px solid #EFE6D8", borderRadius: 10, fontSize: 12.5 }}
            formatter={(value, _name, entry) => {
              const row = (entry?.payload ?? {}) as Contribution;
              const ratio = Math.abs(Number(value)) / magnitude;
              const verb = row.direction === "increases" ? "pointed toward extra support" : "pointed toward things being steady";
              return [`${strengthWord(ratio)} ${verb}`, row.feature_label];
            }}
          />
          <Bar dataKey="contribution" radius={4} barSize={16}>
            {data.map((d) => (
              <Cell key={d.feature} fill={d.direction === "increases" ? INCREASE_COLOR : DECREASE_COLOR} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
