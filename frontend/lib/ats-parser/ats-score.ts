/**
 * ATS 兼容性评分计算
 *
 * 7 个维度，满分 100：
 *   姓名 20 + 邮箱 20 + 电话 10 + 章节 15 + 教育 15 + 经历 15 + 技能 5
 */

import type {
  ParsedResume,
  ResumeSectionToLines,
  AtsScore,
  AtsScoreBreakdown,
  AtsGrade,
  AtsIssue,
} from "./types";

const MAX_SCORES: AtsScoreBreakdown = {
  nameScore: 20,
  emailScore: 20,
  phoneScore: 10,
  sectionsScore: 15,
  educationScore: 15,
  experienceScore: 15,
  skillsScore: 5,
};

function getGrade(total: number): AtsGrade {
  if (total >= 90) return "A+";
  if (total >= 80) return "A";
  if (total >= 70) return "B";
  if (total >= 60) return "C";
  if (total >= 50) return "D";
  return "F";
}

export function computeAtsScore(
  resume: ParsedResume,
  sections: ResumeSectionToLines
): AtsScore {
  const issues: AtsIssue[] = [];
  const breakdown: AtsScoreBreakdown = { ...MAX_SCORES };

  // 姓名 (20)
  if (!resume.profile.name) {
    breakdown.nameScore = 0;
    issues.push({
      severity: "error",
      category: "姓名",
      message: "未能识别出候选人姓名。请确保姓名在简历正文中（非页眉页脚），且为纯字母格式。",
    });
  }

  // 邮箱 (20)
  if (!resume.profile.email) {
    breakdown.emailScore = 0;
    issues.push({
      severity: "error",
      category: "邮箱",
      message: "未找到有效邮箱地址。ATS 无法将简历关联到候选人。",
    });
  }

  // 电话 (10)
  if (!resume.profile.phone) {
    breakdown.phoneScore = 0;
    issues.push({
      severity: "warning",
      category: "电话",
      message: "未识别出电话号码。某些 ATS 需要电话号码来匹配候选人记录。",
    });
  }

  // 章节 (15)
  const sectionTitles = sections.map((s) => s.title.toLowerCase());
  const expectedSections = ["experience", "education", "skills", "经验", "教育", "技能", "项目"];
  const foundExpected = expectedSections.filter((exp) =>
    sectionTitles.some((t) => t.includes(exp))
  );
  breakdown.sectionsScore = Math.round(
    (foundExpected.length / expectedSections.length) * MAX_SCORES.sectionsScore
  );
  if (foundExpected.length < 3) {
    const missing = expectedSections.filter(
      (exp) => !sectionTitles.some((t) => t.includes(exp))
    );
    issues.push({
      severity: "warning",
      category: "章节结构",
      message: `缺少标准章节: ${missing.join("、")}。ATS 依赖标准章节标题来理解简历结构。`,
    });
  }

  // 教育 (15)
  if (resume.educations.length === 0) {
    breakdown.educationScore = 0;
    issues.push({
      severity: "warning",
      category: "教育",
      message: "未能提取教育经历。请使用标准标题 'Education' 并包含学校名称、学位和日期。",
    });
  } else {
    const firstEdu = resume.educations[0];
    let eduOk = 0;
    if (firstEdu.school) eduOk++;
    if (firstEdu.degree || firstEdu.date) eduOk++;
    breakdown.educationScore = Math.round(
      (eduOk / 2) * MAX_SCORES.educationScore
    );
  }

  // 经历 (15)
  if (resume.workExperiences.length === 0) {
    breakdown.experienceScore = 0;
    issues.push({
      severity: "error",
      category: "工作经历",
      message: "未能提取工作经历。请使用标准标题 'Experience' 或 'Work Experience'。",
    });
  } else {
    const firstExp = resume.workExperiences[0];
    let expOk = 0;
    if (firstExp.company) expOk++;
    if (firstExp.jobTitle) expOk++;
    if (firstExp.descriptions.length > 0) expOk++;
    breakdown.experienceScore = Math.round(
      (expOk / 3) * MAX_SCORES.experienceScore
    );
  }

  // 技能 (5)
  if (
    resume.skills.featuredSkills.length === 0 &&
    resume.skills.descriptions.length === 0
  ) {
    breakdown.skillsScore = 0;
    issues.push({
      severity: "info",
      category: "技能",
      message: "未提取到明确技能列表。考虑添加 'Skills' 章节，用逗号或项目符号列出关键技能。",
    });
  }

  const total = Object.values(breakdown).reduce((a, b) => a + b, 0);

  return {
    total,
    grade: getGrade(total),
    breakdown,
    issues,
  };
}
