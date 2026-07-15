/**
 * Step 4: 从章节中提取结构化属性（增强版 — 子章节检测 + 多条目拆分）
 *
 * 核心改进：
 *   1. 子章节检测：用行间距启发式切分多段经历/教育
 *   2. 更精确的属性提取：只在章节头部区域查找学校/职位/公司
 *   3. 技能智能识别：150+ 技术关键词匹配
 */

import type {
  TextItems,
  Line,
  ResumeSectionToLines,
  ParsedResume,
  ResumeProfile,
  ResumeWorkExperience,
  ResumeEducation,
  ResumeProject,
  ResumeSkills,
  FeaturedSkill,
} from "./types";
import {
  getTextWithHighestFeatureScore,
  getLineText,
  getSectionLines,
} from "./feature-scoring";
import {
  NAME_FEATURES,
  EMAIL_FEATURES,
  PHONE_FEATURES,
  URL_FEATURES,
  LOCATION_FEATURES,
  DATE_FEATURES,
  SCHOOL_FEATURES,
  DEGREE_FEATURES,
  GPA_FEATURES,
  JOB_TITLE_FEATURES,
  COMPANY_FEATURES,
  SKILL_MATCHER,
} from "./feature-sets";

// ═══════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════

function flattenLines(lines: Line[]): TextItems {
  return lines.flat();
}

function findSection(
  sections: ResumeSectionToLines,
  keywords: string[]
): ResumeSectionToLines[number] | undefined {
  return sections.find((s) =>
    keywords.some((kw) => s.title.toLowerCase().includes(kw.toLowerCase()))
  );
}

/** 计算章节中各行之间的平均 Y 间距 */
function averageLineGap(lines: Line[]): number {
  if (lines.length < 2) return 0;
  let totalGap = 0;
  let count = 0;
  for (let i = 1; i < lines.length; i++) {
    const gap = lines[i - 1][0].y - lines[i][0].y;
    if (gap > 0) {
      totalGap += gap;
      count++;
    }
  }
  return count > 0 ? totalGap / count : 0;
}

/**
 * 子章节检测：按行间距 > 平均值 * 1.3 切分章节
 * 参照 OpenResume 的 subsections 机制
 */
function splitIntoSubsections(lines: Line[]): Line[][] {
  if (lines.length <= 1) return [lines];

  const avgGap = averageLineGap(lines);
  if (avgGap <= 0) return [lines];

  const threshold = avgGap * 1.3;
  const subsections: Line[][] = [];
  let current: Line[] = [lines[0]];

  for (let i = 1; i < lines.length; i++) {
    const gap = lines[i - 1][0].y - lines[i][0].y;
    if (gap > threshold) {
      // 行间距显著大于平均值 → 新子章节
      subsections.push(current);
      current = [lines[i]];
    } else {
      current.push(lines[i]);
    }
  }
  subsections.push(current);
  return subsections;
}

/**
 * 判断一行是否为子章节头部（加粗 或 包含日期/公司/学校信息）
 */
function isSubsectionHeader(line: Line): boolean {
  const items = flattenLines([line]);
  const lineText = getLineText(line);
  const isBold = line.some((item) => item.bold);
  const { text: date } = getTextWithHighestFeatureScore(items, DATE_FEATURES);
  const { text: company } = getTextWithHighestFeatureScore(items, COMPANY_FEATURES);
  const { text: school } = getTextWithHighestFeatureScore(items, SCHOOL_FEATURES);
  return isBold || !!date || !!company || !!school || lineText.length < 80;
}

// ═══════════════════════════════════════════════
// 个人信息提取
// ═══════════════════════════════════════════════

function extractProfile(sections: ResumeSectionToLines): ResumeProfile {
  // ⭐ 全文本扫描（不只是头部区域）— 确保邮箱/电话/URL 100% 命中
  const allText = getAllText(sections);
  const allLines = getAllLinesText(sections);

  // 邮箱：全文本正则扫描 + 特征评分（双保险）
  let email = regexExtract(allText, /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/);
  if (!email) {
    const topItems = sections.slice(0, 4).flatMap((s) => flattenLines(s.lines));
    const { text } = getTextWithHighestFeatureScore(topItems, EMAIL_FEATURES, false);
    email = text;
  }

  // 电话：全文本正则扫描
  let phone = regexExtract(allText, /\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}/);
  if (!phone) {
    const topItems = sections.slice(0, 4).flatMap((s) => flattenLines(s.lines));
    const { text } = getTextWithHighestFeatureScore(topItems, PHONE_FEATURES, false);
    phone = text;
  }

  // URL：全文本正则扫描
  let url = regexExtract(allText, /(?:linkedin\.com\/in\/[a-zA-Z0-9\-]+|github\.com\/[a-zA-Z0-9\-]+)/i);
  if (!url) {
    url = regexExtract(allText, /https?:\/\/[^\s]+/);
  }

  // 地点
  const topItems = sections.slice(0, 4).flatMap((s) => flattenLines(s.lines));
  const { text: location } = getTextWithHighestFeatureScore(topItems, LOCATION_FEATURES, false);

  // 姓名：排除已知的非姓名字段后评分
  const nameItems = topItems.filter(
    (item) =>
      !item.text.includes("@") &&
      !/\d/.test(item.text) &&
      !/linkedin|github|http/i.test(item.text) &&
      item.text !== email &&
      item.text !== phone &&
      item.text !== location
  );
  const { text: name } = getTextWithHighestFeatureScore(nameItems, NAME_FEATURES, false);

  // Summary
  const profileSection = findSection(sections, [
    "个人简历", "个人信息", "Profile", "Summary", "Objective", "About",
  ]);
  let summary = "";
  if (profileSection) {
    const sectionLines = getSectionLines(profileSection.lines);
    summary = sectionLines.filter((l) => l.length > 20).join("\n");
  }

  return { name, email, phone, url, summary, location };
}

/** 全文本正则提取（对关键字段的后备保障） */
function regexExtract(text: string, pattern: RegExp): string {
  const match = text.match(pattern);
  return match ? match[0].trim() : "";
}

/** 获取所有章节的纯文本 */
function getAllText(sections: ResumeSectionToLines): string {
  return sections.flatMap((s) => getSectionLines(s.lines)).join("\n");
}

/** 获取所有章节的行文本数组 */
function getAllLinesText(sections: ResumeSectionToLines): string[] {
  return sections.flatMap((s) => getSectionLines(s.lines));
}

// ═══════════════════════════════════════════════
// 教育经历（子章节检测）
// ═══════════════════════════════════════════════

function extractEducations(sections: ResumeSectionToLines): ResumeEducation[] {
  const eduSection = findSection(sections, [
    "教育背景", "教育经历", "学历", "Education", "EDUCATION", "Academic Background",
  ]);
  if (!eduSection) return [];

  const educations: ResumeEducation[] = [];

  // 直接从教育章节的每行文本中提取
  for (const line of eduSection.lines) {
    const lineText = getLineText(line);
    if (lineText.length < 5) continue;

    // 尝试匹配日期格式: YYYY.MM-YYYY.MM 或 YYYY-YYYY
    const dateMatch = lineText.match(/(\d{4}(?:\.\d{1,2})?\s*[-–—]\s*\d{4}(?:\.\d{1,2})?)/);
    const date = dateMatch ? dateMatch[0] : "";

    // 学校名：去除日期后的剩余文本中，匹配包含"大学/学院/学校"的部分
    const remaining = date ? lineText.replace(date, "").trim() : lineText;

    // 学校：找包含"大学"或"学院"或"学校"的关键词片段
    const schoolMatch = remaining.match(/([^\s()（）]+(?:大学|学院|学校|Institute|University|College)[^\s()（）]*)/i);
    const school = schoolMatch ? schoolMatch[0] : remaining.split(/[\s()（）]+/)[0] || "";

    // 学位：找括号中的内容 或 包含学士/硕士/博士/本科/大专 的文字
    const degreeMatch = remaining.match(/[（(]([^)）]+)[）)]/);
    let degree = degreeMatch ? degreeMatch[1] : "";
    if (!degree) {
      const degMatch = remaining.match(/(学士|硕士|博士|本科|大专|专科|MBA|Ph\.?D|Master|Bachelor)/i);
      degree = degMatch ? degMatch[0] : remaining.replace(school, "").trim();
    }

    if (school || date) {
      educations.push({ school, degree, date, gpa: "", descriptions: [] });
    }
  }

  return educations;
}

// ═══════════════════════════════════════════════
// 工作经历（子章节检测）
// ═══════════════════════════════════════════════

function extractWorkExperiences(
  sections: ResumeSectionToLines
): ResumeWorkExperience[] {
  const expSection = findSection(sections, [
    "工作经历", "工作经验", "实习经历", "Experience", "Work Experience", "Employment",
  ]);
  if (!expSection) return [];

  const subsections = splitIntoSubsections(expSection.lines);
  const experiences: ResumeWorkExperience[] = [];

  for (const subLines of subsections) {
    // 只取前 3 行作为头部（公司/职位/日期）
    const headerLines = subLines.slice(0, 3);
    const bodyLines = subLines.slice(3);
    const headerItems = flattenLines(headerLines);
    const bodyText = getSectionLines(bodyLines);

    const { text: company } = getTextWithHighestFeatureScore(
      headerItems, COMPANY_FEATURES, true, false
    );
    const { text: jobTitle } = getTextWithHighestFeatureScore(
      headerItems, JOB_TITLE_FEATURES, true, false
    );
    const { text: date } = getTextWithHighestFeatureScore(
      headerItems, DATE_FEATURES, true, false
    );

    // 描述 = 身体行的项目符号内容
    const descriptions = bodyText
      .map((line) => line.replace(/^[•\-*▪▸\s]+/, "").trim())
      .filter((line) => line.length > 3);

    if (company || jobTitle) {
      experiences.push({
        company: company || "",
        jobTitle: jobTitle || "",
        date: date || "",
        descriptions,
      });
    }
  }

  return experiences;
}

// ═══════════════════════════════════════════════
// 项目
// ═══════════════════════════════════════════════

function extractProjects(sections: ResumeSectionToLines): ResumeProject[] {
  const projSection = findSection(sections, [
    "项目经验", "项目经历", "项目", "AI 实践", "Projects", "Personal Projects", "Project Experience",
  ]);
  if (!projSection) return [];

  // 按日期行切分：遇到 YYYY.MM-YYYY.MM 或 YYYY.MM-YYYY 格式的行 → 新项目开始
  const datePattern = /^\d{4}(?:\.\d{1,2})?\s*[-–—]\s*\d{4}(?:\.\d{1,2})?/;
  const projects: ResumeProject[] = [];
  let currentProject: { name: string; date: string; lines: string[] } | null = null;

  for (const line of projSection.lines) {
    const text = getLineText(line);
    if (!text) continue;

    const isDateLine = datePattern.test(text);

    if (isDateLine) {
      // 保存上一个项目
      if (currentProject && currentProject.name) {
        projects.push({
          project: currentProject.name,
          date: currentProject.date,
          descriptions: currentProject.lines.filter((l) => l.length > 2),
        });
      }
      // 提取日期和项目名：日期后面的是项目名
      const dateMatch = text.match(datePattern);
      const date = dateMatch ? dateMatch[0] : "";
      const name = dateMatch ? text.slice(dateMatch[0].length).trim() : text;
      currentProject = { name, date, lines: [] };
    } else if (currentProject) {
      // 正文行：去项目符号后加入描述
      const cleaned = text.replace(/^[•\-*▪▸\s]+/, "").trim();
      if (cleaned && cleaned.length > 2) {
        currentProject.lines.push(cleaned);
      }
    }
  }

  // 保存最后一个项目
  if (currentProject && currentProject.name) {
    projects.push({
      project: currentProject.name,
      date: currentProject.date,
      descriptions: currentProject.lines.filter((l) => l.length > 2),
    });
  }

  return projects;
}

// ═══════════════════════════════════════════════
// 技能（150+ 技术关键词识别）
// ═══════════════════════════════════════════════

function extractSkills(sections: ResumeSectionToLines): ResumeSkills {
  const skillSection = findSection(sections, [
    "专业技能", "技能", "技术栈", "Skills", "Technical Skills", "Core Competencies",
  ]);
  if (!skillSection) return { featuredSkills: [], descriptions: [] };

  const lines = getSectionLines(skillSection.lines);
  const featuredSkills: FeaturedSkill[] = [];
  const descriptions: string[] = [];
  const seenSkills = new Set<string>();

  for (const line of lines) {
    // 检测是技能列表还是描述文本
    const hasDelimiters = /[,•|;/]/.test(line);
    const isShort = line.length < 120;

    if (hasDelimiters && isShort) {
      // 技能列表行 → 逐项提取（支持 / 和中文冒号分隔）
      // 先去掉"类别："前缀（如"LLM："、"开发："）
      const cleaned = line.replace(/^[^：:]*[：:]\s*/, "");
      const tokens = cleaned.split(/[,•|;/\/]+/).map((s) => s.trim()).filter((s) => s.length > 0);
      for (const token of tokens) {
        // 尝试智能分组: 如 "Python (Flask, Django)"
        const mainMatch = token.match(/^([^(]+)(?:\s*\(([^)]+)\))?$/);
        if (mainMatch) {
          const mainSkill = mainMatch[1].trim();
          if (SKILL_MATCHER.isSkill({ text: mainSkill }) && !seenSkills.has(mainSkill.toLowerCase())) {
            featuredSkills.push({ skill: mainSkill, rating: 0 });
            seenSkills.add(mainSkill.toLowerCase());
          }
          if (mainMatch[2]) {
            const subSkills = mainMatch[2].split(/[,/]/).map((s) => s.trim());
            for (const sub of subSkills) {
              if (sub.length > 1 && !seenSkills.has(sub.toLowerCase())) {
                featuredSkills.push({ skill: sub, rating: 0 });
                seenSkills.add(sub.toLowerCase());
              }
            }
          }
        }
      }
    } else if (SKILL_MATCHER.isSkill({ text: line.trim() })) {
      if (!seenSkills.has(line.trim().toLowerCase())) {
        featuredSkills.push({ skill: line.trim(), rating: 0 });
        seenSkills.add(line.trim().toLowerCase());
      }
    } else if (line.length > 10) {
      descriptions.push(line);
    }
  }

  return { featuredSkills, descriptions };
}

// ═══════════════════════════════════════════════
// 主解析入口
// ═══════════════════════════════════════════════

export function extractAttributes(sections: ResumeSectionToLines): ParsedResume {
  return {
    profile: extractProfile(sections),
    workExperiences: extractWorkExperiences(sections),
    educations: extractEducations(sections),
    projects: extractProjects(sections),
    skills: extractSkills(sections),
    custom: { descriptions: [] },
  };
}
