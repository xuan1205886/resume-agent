/**
 * ATS 解析器类型定义
 *
 * 对应 OpenResume 的 parse-resume-from-pdf 类型体系
 */

// ===== Step 1: 原始文本项 =====

/** PDF.js 提取的原始文本项（带坐标和字体信息） */
export interface TextItem {
  text: string;
  x1: number;        // 左边缘 X 坐标 (transform[4])
  x2: number;        // 右边缘 X 坐标 (x1 + width)
  y: number;         // Y 坐标 (PDF 空间左下角原点)
  height: number;    // 渲染高度 ≈ 字号（pt）
  width: number;     // 渲染宽度
  fontSize: number;  // 从 transform 矩阵提取的字号
  fontName: string;  // 字体标识符
  bold: boolean;     // 是否加粗
  newLine: boolean;  // 是否开始新行
}

export type TextItems = TextItem[];

// ===== Step 2: 行分组 =====

/** 一行 = 多个文本项（按 x 坐标排序） */
export type Line = TextItems;

/** 整个文档的所有行（按 y 坐标降序 = 从上到下） */
export type Lines = Line[];

// ===== Step 3: 章节分组 =====

/** 一个章节 = 标题 + 行列表 */
export interface ResumeSection {
  title: string;
  lines: Lines;
}

export type ResumeSectionToLines = ResumeSection[];

// ===== Step 4: 特征评分 =====

/** 单个特征：匹配函数 + 分数 */
export interface Feature {
  match: (item: TextItem) => boolean;
  score: number;
  description?: string;
}

/** 特征集 = 一组特征，用于评分某个属性 */
export type FeatureSet = Feature[];

/** 文本项得分 */
export interface TextScore {
  text: string;
  score: number;
}

export type TextScores = TextScore[];

// ===== 解析输出（AST）=====

export interface ResumeProfile {
  name: string;
  email: string;
  phone: string;
  url: string;
  summary: string;
  location: string;
}

export interface ResumeWorkExperience {
  company: string;
  jobTitle: string;
  date: string;
  descriptions: string[];
}

export interface ResumeEducation {
  school: string;
  degree: string;
  date: string;
  gpa: string;
  descriptions: string[];
}

export interface ResumeProject {
  project: string;
  date: string;
  descriptions: string[];
}

export interface FeaturedSkill {
  skill: string;
  rating: number;
}

export interface ResumeSkills {
  featuredSkills: FeaturedSkill[];
  descriptions: string[];
}

export interface ResumeCustom {
  descriptions: string[];
}

/** 完整简历解析结果 */
export interface ParsedResume {
  profile: ResumeProfile;
  workExperiences: ResumeWorkExperience[];
  educations: ResumeEducation[];
  projects: ResumeProject[];
  skills: ResumeSkills;
  custom: ResumeCustom;
}

// ===== ATS 兼容性评分 =====

export interface AtsScoreBreakdown {
  nameScore: number;        // 20
  emailScore: number;       // 20
  phoneScore: number;       // 10
  sectionsScore: number;    // 15
  educationScore: number;   // 15
  experienceScore: number;  // 15
  skillsScore: number;      // 5
}

export type AtsGrade = "A+" | "A" | "B" | "C" | "D" | "F";

export interface AtsScore {
  total: number;            // 0-100
  grade: AtsGrade;
  breakdown: AtsScoreBreakdown;
  issues: AtsIssue[];
}

export interface AtsIssue {
  severity: "error" | "warning" | "info";
  category: string;
  message: string;
}
