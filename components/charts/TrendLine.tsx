"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type TrendPoint = { date: string; value: number; label: string };

export default function TrendLine({
  data, domain, referenceValue, referenceLabel, color = "#5E4A5E",
}: {
  data: TrendPoint[];
  domain: [number, number];
  referenceValue?: number;
  referenceLabel?: string;
  color?: string;
}) {
  if (data.length === 0) {
    return <div className="subtext">No entries yet. Check in to start your trend.</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#EFE6D8" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#A08E97" }} axisLine={{ stroke: "#EADFCF" }} tickLine={false} />
        <YAxis domain={domain} tick={{ fontSize: 11, fill: "#A08E97" }} axisLine={false} tickLine={false} width={32} />
        <Tooltip
          contentStyle={{ background: "#FCF8F2", border: "1px solid #EFE6D8", borderRadius: 10, fontSize: 12.5 }}
          labelStyle={{ color: "#5E4A5E", fontWeight: 600 }}
        />
        {referenceValue !== undefined && (
          <ReferenceLine y={referenceValue} stroke="#C9705A" strokeDasharray="4 4"
            label={{ value: referenceLabel, position: "insideTopRight", fill: "#C9705A", fontSize: 10.5 }} />
        )}
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5}
          dot={{ r: 3.5, fill: color, strokeWidth: 0 }} activeDot={{ r: 5.5 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
