"use client";

interface MatchStatsProps {
  data: Record<string, unknown>;
}

export function MatchStats({ data }: MatchStatsProps) {
  const matchResults = (data.match_results as Array<{ status: string }>) || [];
  const matched = matchResults.filter((r) => r.status === "match").length;
  const partial = matchResults.filter(
    (r) => r.status === "partial_match"
  ).length;
  const missing = matchResults.filter((r) => r.status === "missing").length;
  const overallScore = (data.overall_score as number) || 0;

  const scoreColor =
    overallScore >= 0.7
      ? "text-green-600"
      : overallScore >= 0.4
        ? "text-yellow-600"
        : "text-red-600";

  const stats = [
    {
      value: `${(overallScore * 100).toFixed(0)}%`,
      label: "综合匹配度",
      color: scoreColor,
    },
    {
      value: matched.toString(),
      label: "已匹配技能",
      color: "text-green-600",
    },
    {
      value: partial.toString(),
      label: "部分匹配",
      color: "text-yellow-600",
    },
    {
      value: missing.toString(),
      label: "缺失技能",
      color: "text-red-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 mb-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="text-center p-2.5 rounded-lg bg-gray-50 border"
        >
          <div className={`text-xl font-bold ${stat.color}`}>{stat.value}</div>
          <div className="text-xs text-gray-500">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
