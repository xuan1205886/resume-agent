/**
 * Step 3: 将行分组为章节
 *
 * 支持中英文简历的章节标题检测：
 *   - 英文：加粗 + 全大写 + 关键字
 *   - 中文：短文本行 + 关键字 + 字号
 */

import type { Line, Lines, ResumeSectionToLines } from "./types";

// 中文章节关键字
const CN_SECTION_KEYWORDS = [
  "个人简历", "个人信息", "基本信息", "简历",
  "教育背景", "教育经历", "学历", "教育",
  "主修课程", "课程",
  "专业技能", "技能", "技术栈", "技术能力",
  "项目经验", "项目经历", "项目",
  "工作经历", "工作经验", "实习经历", "实习",
  "自我评价", "个人总结", "自我介绍",
  "获奖经历", "荣誉", "证书", "语言能力",
  "联系方式", "社交链接",
  "科研经历", "论文", "专利",
];

// 英文关键字（用于大小写不敏感匹配）
const EN_SECTION_KEYWORDS = [
  "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT",
  "SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES",
  "PROJECTS", "PERSONAL PROJECTS", "PROJECT EXPERIENCE",
  "SUMMARY", "PROFESSIONAL SUMMARY", "OBJECTIVE", "ABOUT",
  "CERTIFICATIONS", "LANGUAGES", "INTERESTS",
  "PUBLICATIONS", "AWARDS", "REFERENCES",
  "VOLUNTEER", "LEADERSHIP", "COURSEWORK", "ACTIVITIES",
  "ACHIEVEMENTS", "HONORS", "CONTACT", "LINKS",
];

function getAvgFontSize(lines: Line[]): number {
  let total = 0, count = 0;
  for (const line of lines.slice(0, 20)) {
    for (const item of line) {
      total += item.fontSize || item.height;
      count++;
    }
  }
  return count > 0 ? total / count : 12;
}

/** 是否包含中文字符 */
function hasChinese(text: string): boolean {
  return /[一-鿿]/.test(text);
}

/** 是否为英文全大写 */
function isAllUppercase(text: string): boolean {
  const letters = text.replace(/[^a-zA-Z]/g, "");
  return letters.length >= 2 && letters === letters.toUpperCase();
}

/**
 * 核心判断：一行是否是章节标题
 *
 * 中文简历：短文本(2-15字) + 包含中文 + 不含长句标点
 * 英文简历：全大写/加粗/大字号/关键字
 */
function isSectionTitle(line: Line, avgFontSize: number): boolean {
  const text = line.map((item) => item.text).join(" ").trim();
  if (!text || text.length < 2 || text.length > 40) return false;

  const isChinese = hasChinese(text);
  const isBold = line.some((item) => item.bold);
  const fontSize = Math.max(...line.map((item) => item.fontSize || item.height || 10));
  const isLarger = fontSize > avgFontSize * 1.1;
  const isUpper = isAllUppercase(text);

  // ==== 通用排除：非标题特征 ====
  // 含冒号 → 是描述行（如"项目亮点："、"技术栈："）
  if (/[：:]/.test(text)) return false;
  // 项目符号开头
  if (/^[•\-*▪▸\s]/.test(text)) return false;
  // 含句号 → 是正文
  if (/[。！？]/.test(text)) return false;

  // ==== 关键字匹配（中英文）====
  const textUpper = text.toUpperCase();
  for (const kw of [...CN_SECTION_KEYWORDS, ...EN_SECTION_KEYWORDS]) {
    if (text === kw || textUpper === kw) return true;
    // startsWith 仅对长度 ≥4 的关键词生效（避免"项目"匹配"项目亮点"）
    if (kw.length >= 4 && (text.startsWith(kw) || textUpper.startsWith(kw))) return true;
  }

  // ==== 中文：短标题行 ====
  if (isChinese) {
    const chineseChars = text.replace(/[^一-鿿]/g, "");
    if (chineseChars.length >= 2 && chineseChars.length <= 6 &&
        line.length <= 3 && !/[，。；！？、]/.test(text)) {
      return true;
    }
    return false;
  }

  // ==== 英文：样式规则 ====
  if (isBold && isUpper) return true;
  if (isUpper && isLarger) return true;
  if (isBold && fontSize > avgFontSize * 1.2) return true;
  if (line.length === 1 && isUpper) return true;

  return false;
}

export function groupLinesIntoSections(lines: Lines): ResumeSectionToLines {
  if (lines.length === 0) return [];

  const avgFontSize = getAvgFontSize(lines);
  const sections: ResumeSectionToLines = [];
  let currentTitle = "Profile";
  let currentLines: Lines = [];

  for (const line of lines) {
    if (isSectionTitle(line, avgFontSize)) {
      if (currentLines.length > 0 || currentTitle !== "Profile") {
        sections.push({ title: currentTitle, lines: currentLines });
      }
      currentTitle = line.map((item) => item.text).join(" ").trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }

  sections.push({ title: currentTitle, lines: currentLines });

  if (sections.length > 1 && sections[0].title === "Profile" && sections[0].lines.length === 0) {
    sections.shift();
  }

  return sections;
}
