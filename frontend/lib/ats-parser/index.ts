/**
 * ATS 简历解析器 — 主入口
 *
 * 纯浏览器端运行，模拟 ATS 系统（Greenhouse/Lever）解析 PDF 简历。
 * 4 步算法：提取 → 行分组 → 章节分组 → 特征评分
 *
 * 用法：
 *   import { parseResumeFromPdf } from "@/lib/ats-parser";
 *   const { resume, sections, score } = await parseResumeFromPdf(file);
 */

import { readPdf } from "./read-pdf";
import { groupTextItemsIntoLines } from "./group-text-items-into-lines";
import { groupLinesIntoSections } from "./group-lines-into-sections";
import { extractAttributes } from "./extract-attributes";
import { computeAtsScore } from "./ats-score";
import type { ParsedResume, ResumeSectionToLines, AtsScore, TextItems } from "./types";

export interface ParseResult {
  resume: ParsedResume;
  sections: ResumeSectionToLines;
  score: AtsScore;
  /** 调试信息：原始 PDF 文本行 */
  debug: {
    rawLines: string[];
    sectionNames: string[];
    textItemCount: number;
  };
}

/**
 * 从 PDF 文件中解析简历并计算 ATS 兼容性评分
 */
export async function parseResumeFromPdf(file: File): Promise<ParseResult> {
  // Step 1: 提取文本项（含坐标、字体）
  const textItems = await readPdf(file);

  // Step 2: 行分组（水平合并 + 垂直分组）
  const lines = groupTextItemsIntoLines(textItems);

  // Step 3: 章节分组
  const sections = groupLinesIntoSections(lines);

  // 生成调试用的原始行文本
  const rawLines = lines.map((line) => line.map((item) => item.text).join(" ")).filter((t) => t.trim());

  // Step 4: 特征评分提取属性
  const resume = extractAttributes(sections);

  // ATS 兼容性评分
  const score = computeAtsScore(resume, sections);

  return {
    resume,
    sections,
    score,
    debug: {
      rawLines,
      sectionNames: sections.map((s) => s.title),
      textItemCount: textItems.length,
    },
  };
}

// 导出类型
export type { ParsedResume, ResumeSectionToLines, AtsScore, AtsIssue } from "./types";
