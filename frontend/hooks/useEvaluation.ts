/**
 * useEvaluation — TypeScript 移植 Python 的 compute_evaluation_metrics()
 *
 * 四维评估指标：
 *   1. JD 覆盖率 (jd_coverage)
 *   2. 匹配质量 (match_quality)
 *   3. 事实可信度 (fact_trust)
 *   4. 格式完整度 (format_score)
 *
 * 四种智能 Badcase：
 *   - critical: 事实虚构
 *   - warning: 严重漂移、匹配矛盾/假阴性
 *   - info: 低质量匹配、简历解析提示
 */

import { useMemo } from "react";
import type {
  OptimizationResult,
  FactCheckReport,
  EvaluationMetrics,
  Badcase,
} from "@/lib/types";

export function useEvaluation(
  result: OptimizationResult | null,
  factCheck: FactCheckReport | null
): EvaluationMetrics {
  return useMemo(() => {
    if (!result) {
      return {
        jd_coverage: 0,
        match_quality: 0,
        fact_trust: 0,
        format_score: 0,
        badcases: [],
      };
    }

    const jdSkills = result.jd_skills || [];
    const matchResults = result.match_results || [];
    const parsedResume = result.parsed_resume || {};
    const optimizedMd = result.optimized_resume_md || "";

    // 1. JD 覆盖率：JD 技能被简历覆盖的比例
    const matchedCount = matchResults.filter(
      (r) => r.status === "match" || r.status === "partial_match"
    ).length;
    const jdCoverage = jdSkills.length > 0 ? matchedCount / jdSkills.length : 0;

    // 2. 匹配质量：有详细证据（>20字符）的匹配比例
    const withEvidence = matchResults.filter(
      (r) => (r.detail?.length || 0) > 20
    ).length;
    const matchQuality =
      matchResults.length > 0 ? withEvidence / matchResults.length : 0;

    // 3. 事实可信度：无漂移 + 轻微漂移占总数比例
    // overall_trust_score = -1 表示"未核查"（无 bullet 可供对比）
    let factTrust = 0;
    if (factCheck && factCheck.overall_trust_score === -1) {
      factTrust = -1;  // 特殊值：表示 N/A
    } else if (factCheck && factCheck.verdicts?.length > 0) {
      const okCount =
        (factCheck.none_count || 0) + (factCheck.minor_count || 0);
      factTrust = okCount / factCheck.verdicts.length;
    }

    // 4. 格式完整度：检查标准章节
    const standardSections = ["summary", "skills", "experience", "education"];
    const foundSections = standardSections.filter((s) =>
      optimizedMd.toLowerCase().includes(s)
    );
    const formatScore = foundSections.length / standardSections.length;

    // 智能诊断 Badcase
    const badcases: Badcase[] = [];

    // Critical: 事实虚构
    if (factCheck && factCheck.fabricated_count > 0) {
      badcases.push({
        type: "事实虚构",
        severity: "critical",
        detail: `检测到 ${factCheck.fabricated_count} 处虚构内容。AI 编造了原文不存在的数字、技术栈或职责描述。`,
      });
    }

    // Warning: 严重漂移
    if (factCheck && factCheck.major_count > 0) {
      badcases.push({
        type: "严重漂移",
        severity: "warning",
        detail: `${factCheck.major_count} 处重要信息被改变（职责夸大/角色升级等）。`,
      });
    }

    // Warning: 匹配矛盾（JD要求但简历完全没有）
    const missingSkills = matchResults.filter(
      (r) => r.status === "missing"
    );
    if (missingSkills.length > 3) {
      badcases.push({
        type: "大量缺失技能",
        severity: "warning",
        detail: `${missingSkills.length} 个JD核心技能在简历中完全找不到：${missingSkills.map((r) => r.skill).join("、")}`,
      });
    }

    // Info: 简历解析提示
    const resumeSkills = (parsedResume.skills as unknown[]) || [];
    const resumeExp = (parsedResume.experience as unknown[]) || [];
    if ((resumeSkills.length === 0 || resumeExp.length === 0) && optimizedMd) {
      badcases.push({
        type: "简历解析不完整",
        severity: "info",
        detail: `简历解析得到 ${resumeSkills.length} 个技能、${resumeExp.length} 条经历。如不准确请检查PDF格式。`,
      });
    }

    return {
      jd_coverage: jdCoverage,
      match_quality: matchQuality,
      fact_trust: factTrust,
      format_score: formatScore,
      badcases,
    };
  }, [result, factCheck]);
}
