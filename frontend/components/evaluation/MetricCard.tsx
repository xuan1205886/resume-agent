"use client";

interface MetricCardProps {
  label: string;
  value: number | string;
  description: string;
  isNA?: boolean;
}

export function MetricCard({
  label,
  value,
  description,
  isNA,
}: MetricCardProps) {
  let colorClass = "text-green-600";
  let displayValue: string;

  if (isNA) {
    colorClass = "text-gray-400";
    displayValue = "N/A";
  } else if (typeof value === "number") {
    displayValue = `${(value * 100).toFixed(0)}%`;
    if (value < 0.5) colorClass = "text-red-600";
    else if (value < 0.8) colorClass = "text-yellow-600";
    else colorClass = "text-green-600";
  } else {
    displayValue = value;
  }

  return (
    <div className="text-center p-4 rounded-lg border bg-white">
      <div className={`text-2xl font-bold ${colorClass}`}>{displayValue}</div>
      <div className="text-sm font-semibold text-gray-700 mt-1">{label}</div>
      <div className="text-xs text-gray-400 mt-0.5">{description}</div>
    </div>
  );
}
