// Turns raw, one-point-per-event history (which gets noisy fast under regular use) into a
// readable trend: one point per day while the history is still short, one point per week
// once it grows past a few weeks -- so a month of daily chatting reads as a month-shaped
// line, not 30+ overlapping same-day dots.
export type RawPoint = { date: string; value: number };
export type TrendPoint = { date: string; value: number; label: string };

function dayKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function weekKey(iso: string): string {
  const d = new Date(iso);
  const mondayOffset = (d.getDay() + 6) % 7; // Monday = 0 .. Sunday = 6
  const weekStart = new Date(d);
  weekStart.setDate(d.getDate() - mondayOffset);
  return dayKey(weekStart.toISOString());
}

function average(values: number[]): number {
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
}

function bucket(points: RawPoint[], keyFn: (iso: string) => string): Map<string, number[]> {
  const buckets = new Map<string, number[]>();
  for (const p of points) {
    const k = keyFn(p.date);
    if (!buckets.has(k)) buckets.set(k, []);
    buckets.get(k)!.push(p.value);
  }
  return buckets;
}

/** Switches from daily to weekly buckets once daily buckets would exceed this many points
 * (roughly three weeks) -- short histories stay at full daily detail. */
const DAY_BUCKET_LIMIT = 21;

export function aggregateTrend(points: RawPoint[]): TrendPoint[] {
  if (points.length === 0) return [];
  const dayBuckets = bucket(points, dayKey);
  const dayKeys = [...dayBuckets.keys()].sort();

  if (dayKeys.length <= DAY_BUCKET_LIMIT) {
    return dayKeys.map((k) => {
      const d = new Date(k);
      return { date: k, value: average(dayBuckets.get(k)!), label: `${d.getMonth() + 1}/${d.getDate()}` };
    });
  }

  const weekBuckets = bucket(points, weekKey);
  const weekKeys = [...weekBuckets.keys()].sort();
  return weekKeys.map((k) => {
    const d = new Date(k);
    return { date: k, value: average(weekBuckets.get(k)!), label: `Wk ${d.getMonth() + 1}/${d.getDate()}` };
  });
}
