/**
 * 特征集定义 — 200+ 关键词库
 *
 * 参照 OpenResume 的评分体系，每个属性（姓名/邮箱/电话/...）有一组特征
 * 对候选 TextItem 逐项评分，总分最高者当选。
 */

import type { TextItem, FeatureSet } from "./types";

// ═══════════════════════════════════════════════
// 姓名特征（8 个特征）
// ═══════════════════════════════════════════════

export const NAME_FEATURES: FeatureSet = [
  { match: (item) => /^[a-zA-ZÀ-ÿ\s.\-']+$/.test(item.text), score: 3 },
  { match: (item) => item.bold, score: 3 },
  { match: (item) => /^[A-Z][a-z]+ [A-Z][a-z]+/.test(item.text), score: 3 },
  { match: (item) => item.text.includes("@"), score: -5 },
  { match: (item) => /\d/.test(item.text), score: -5 },
  { match: (item) => item.text.includes(","), score: -4 },
  { match: (item) => /[/\\]/.test(item.text) && !item.text.includes("//"), score: -4 },
  { match: (item) => /\b(linkedin|github|http|www)\b/i.test(item.text), score: -4 },
];

// ═══════════════════════════════════════════════
// 邮箱
// ═══════════════════════════════════════════════

export const EMAIL_FEATURES: FeatureSet = [
  { match: (item) => /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(item.text.trim()), score: 15 },
  { match: (item) => /\S+@\S+\.\S+/.test(item.text), score: 8 },
];

// ═══════════════════════════════════════════════
// 电话
// ═══════════════════════════════════════════════

export const PHONE_FEATURES: FeatureSet = [
  { match: (item) => /^[\s]*\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}[\s]*$/.test(item.text), score: 15 },
  { match: (item) => /\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}/.test(item.text), score: 8 },
  { match: (item) => /\+\d{1,3}[\s.\-]?\d{2,4}[\s.\-]?\d{6,10}/.test(item.text), score: 8 },
  { match: (item) => /^[\d\s\-().+]{10,18}$/.test(item.text.trim()), score: 2 },
];

// ═══════════════════════════════════════════════
// URL（LinkedIn / GitHub / 个人网站）
// ═══════════════════════════════════════════════

export const URL_FEATURES: FeatureSet = [
  { match: (item) => /linkedin\.com\/in\//i.test(item.text), score: 15 },
  { match: (item) => /github\.com\/[a-zA-Z0-9\-]+/i.test(item.text), score: 12 },
  { match: (item) => /^(https?:\/\/)?[\w\-]+(\.[\w\-]+)+[/#?]?.*$/.test(item.text.trim()), score: 5 },
  { match: (item) => /\.(io|dev|me|co|com|org|net)\b/i.test(item.text), score: 3 },
];

// ═══════════════════════════════════════════════
// 地点
// ═══════════════════════════════════════════════

export const LOCATION_FEATURES: FeatureSet = [
  { match: (item) => /[A-Z][a-zA-Z\s.]+,\s*(?:[A-Z]{2}|United\s+(?:States|Kingdom)|Canada|Australia)/.test(item.text), score: 12 },
  { match: (item) => /^(remote|hybrid|on[\-\s]?site)$/i.test(item.text.trim()), score: 5 },
  { match: (item) => /\b(NY|CA|TX|FL|IL|PA|OH|GA|NC|MI|NJ|VA|WA|AZ|MA|TN|IN|MO|MD|WI|CO|MN|SC|AL|LA|KY|OR|OK|CT|IA|MS|AR|KS|UT|NV|NM|NE|WV|ID|HI|NH|ME|MT|RI|DE|SD|ND|AK|VT|WY|DC)\b/.test(item.text), score: 3 },
];

// ═══════════════════════════════════════════════
// 学校 — 100+ 学校关键词
// ═══════════════════════════════════════════════

const SCHOOL_KEYWORDS = [
  // 美国
  "Massachusetts Institute of Technology", "MIT", "Stanford", "Harvard",
  "California Institute of Technology", "Caltech", "Princeton",
  "Yale", "Columbia", "Cornell", "Dartmouth", "Brown",
  "University of Pennsylvania", "UPenn", "Duke", "Northwestern",
  "Johns Hopkins", "JHU", "University of Chicago", "UChicago",
  "University of California", "UC Berkeley", "UCLA", "UCSD", "UCSB", "UCI", "UC Davis",
  "University of Michigan", "UMich", "Carnegie Mellon", "CMU",
  "New York University", "NYU", "Georgia Tech", "Georgia Institute of Technology",
  "University of Washington", "UW", "University of Texas", "UT Austin",
  "Purdue", "University of Illinois", "UIUC", "University of Wisconsin", "UW Madison",
  "Rice", "Vanderbilt", "Washington University in St. Louis", "WashU",
  "USC", "University of Southern California", "Northeastern",
  "Boston University", "BU", "Ohio State", "Penn State",
  "University of Florida", "UF", "University of Maryland", "UMD",
  "Arizona State", "ASU", "Texas A&M", "TAMU", "Virginia Tech",
  "University of Virginia", "UVA",
  // 加拿大
  "University of Toronto", "UofT", "McGill", "University of British Columbia", "UBC",
  "University of Waterloo", "McMaster", "University of Alberta",
  // 英国
  "University of Cambridge", "Cambridge", "University of Oxford", "Oxford",
  "Imperial College London", "Imperial College", "London School of Economics", "LSE",
  "University College London", "UCL", "University of Edinburgh",
  "University of Manchester", "King's College London", "King's College",
  "University of Warwick", "University of Bristol",
  // 欧洲
  "ETH Zurich", "EPFL", "TU Munich", "Technical University of Munich",
  "University of Amsterdam", "TU Delft", "KU Leuven",
  // 亚洲
  "University of Tokyo", "Tsinghua", "Peking University",
  "National University of Singapore", "NUS", "Nanyang Technological University", "NTU",
  "KAIST", "Seoul National University",
  "Indian Institute of Technology", "IIT", "IIIT",
  // 澳洲
  "University of Melbourne", "Australian National University", "ANU",
  "University of Sydney", "UNSW",
  // 通用术语
  "University", "College", "Institute of Technology", "Polytechnic",
  "School of", "Academy", "Universität", "Universidad",
];

export const SCHOOL_FEATURES: FeatureSet = [
  {
    match: (item) =>
      SCHOOL_KEYWORDS.some((kw) => {
        const regex = new RegExp(`\\b${kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
        return regex.test(item.text);
      }),
    score: 12,
  },
  { match: (item) => item.bold, score: 3 },
  { match: (item) => /^[A-Z][a-zA-Z\s&.,]+$/.test(item.text) && item.text.length > 10, score: 1 },
];

// ═══════════════════════════════════════════════
// 学位 — 50+ 学位关键词
// ═══════════════════════════════════════════════

const DEGREE_PATTERNS = [
  // 本科
  "Bachelor of Science", "B.S.", "B.Sc", "BS", "Bachelor of Arts", "B.A.", "BA",
  "Bachelor of Engineering", "B.E.", "B.Eng", "B.Tech", "B.Tech.",
  "Bachelor of Business Administration", "BBA", "B.B.A.",
  "Bachelor of Fine Arts", "BFA", "Bachelor of Architecture", "B.Arch",
  "Bachelor of Commerce", "B.Com", "Bachelor of Laws", "LL.B.",
  // 硕士
  "Master of Science", "M.S.", "M.Sc", "MS", "Master of Arts", "M.A.", "MA",
  "Master of Engineering", "M.E.", "M.Eng", "M.Tech", "M.Tech.",
  "Master of Business Administration", "MBA", "M.B.A.",
  "Master of Fine Arts", "MFA", "Master of Architecture", "M.Arch",
  "Master of Public Administration", "MPA", "Master of Public Health", "MPH",
  "Master of Laws", "LL.M.",
  // 博士
  "Doctor of Philosophy", "Ph.D.", "PhD", "Doctor of", "Doctorate",
  "Ed.D.", "J.D.", "Juris Doctor", "M.D.", "Doctor of Medicine",
  // 副学士/高中/证书
  "Associate of Science", "A.S.", "Associate of Arts", "A.A.",
  "Associate of Applied Science", "A.A.S.",
  "High School Diploma", "GED", "Certificate", "Certification",
  "Diploma", "Advanced Diploma", "Postgraduate Diploma",
  // 其他
  "B.A.Sc", "B.Eng.Sc", "M.Eng.Sc", "M.Res", "M.Phil",
  "Engineer's Degree", "Specialist",
];

export const DEGREE_FEATURES: FeatureSet = [
  {
    match: (item) =>
      DEGREE_PATTERNS.some((p) => {
        const escaped = p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        return new RegExp(`\\b${escaped}\\b`, "i").test(item.text);
      }),
    score: 12,
  },
];

// ═══════════════════════════════════════════════
// GPA
// ═══════════════════════════════════════════════

export const GPA_FEATURES: FeatureSet = [
  { match: (item) => /gpa[:\s]*([0-4]\.\d{1,2})/i.test(item.text), score: 12 },
  { match: (item) => /^([0-4]\.\d{1,2})\s*\/\s*4\.0{0,2}$/i.test(item.text.trim()), score: 8 },
  { match: (item) => /([0-4]\.\d{1,2})/.test(item.text) && item.text.length < 12, score: 3 },
];

// ═══════════════════════════════════════════════
// 日期 — 增强版
// ═══════════════════════════════════════════════

const ALL_MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Sept", "Oct", "Nov", "Dec",
];
const SEASONS = ["Spring", "Summer", "Fall", "Winter", "Autumn"];
const DATE_INDICATORS = ["Present", "Current", "Expected", "Anticipated", "Ongoing"];

function hasYear(text: string): boolean {
  return /\b(19|20)\d{2}\b/.test(text);
}

function hasMonth(text: string): boolean {
  const lower = text.toLowerCase();
  return ALL_MONTHS.some((m) => lower.includes(m.toLowerCase()));
}

function hasSeason(text: string): boolean {
  return SEASONS.some((s) => text.toLowerCase().includes(s.toLowerCase()));
}

function hasDateIndicator(text: string): boolean {
  return DATE_INDICATORS.some((d) => text.toLowerCase().includes(d.toLowerCase()));
}

function hasRangeSeparator(text: string): boolean {
  return /[-–—]/.test(text) || /\bto\b/i.test(text);
}

export const DATE_FEATURES: FeatureSet = [
  { match: (item) => hasYear(item.text) && hasMonth(item.text), score: 12 },
  { match: (item) => hasYear(item.text) && hasRangeSeparator(item.text), score: 10 },
  { match: (item) => hasDateIndicator(item.text), score: 10 },
  { match: (item) => hasYear(item.text), score: 6 },
  { match: (item) => hasMonth(item.text) && hasRangeSeparator(item.text), score: 5 },
  { match: (item) => hasSeason(item.text) && hasYear(item.text), score: 4 },
  { match: (item) => /^(19|20)\d{2}\s*[-–—]\s*(19|20)\d{2}$/.test(item.text.trim()), score: 8 },
];

// ═══════════════════════════════════════════════
// 职位名称 — 80+ 关键词
// ═══════════════════════════════════════════════

const JOB_TITLE_KEYWORDS = [
  // 软件/工程
  "Software Engineer", "Software Developer", "Senior Software Engineer",
  "Staff Software Engineer", "Principal Engineer", "Engineering Manager",
  "Full Stack Developer", "Frontend Developer", "Front End Developer",
  "Backend Developer", "Back End Developer", "Full-Stack Engineer",
  "Mobile Developer", "iOS Developer", "Android Developer",
  "DevOps Engineer", "SRE", "Site Reliability Engineer",
  "Platform Engineer", "Infrastructure Engineer",
  "Data Engineer", "Data Scientist", "Data Analyst",
  "Machine Learning Engineer", "ML Engineer", "AI Engineer",
  "NLP Engineer", "Computer Vision Engineer",
  "Security Engineer", "QA Engineer", "Test Engineer",
  "Embedded Engineer", "Firmware Engineer",
  "Systems Engineer", "Network Engineer", "Cloud Engineer",
  "Solutions Architect", "Technical Architect",
  // 产品/设计
  "Product Manager", "Senior Product Manager", "Technical Product Manager",
  "Product Designer", "UX Designer", "UI Designer", "UX/UI Designer",
  "UX Researcher", "Interaction Designer",
  "Graphic Designer", "Visual Designer",
  // 数据/分析
  "Data Scientist", "Data Analyst", "Business Analyst",
  "Business Intelligence", "BI Analyst", "Analytics Engineer",
  "Quantitative Analyst", "Quant", "Statistician",
  // 管理
  "Engineering Manager", "Tech Lead", "Technical Lead", "Team Lead",
  "CTO", "Chief Technology Officer", "VP of Engineering",
  "CEO", "Chief Executive Officer", "CFO", "COO", "CIO",
  "Director of Engineering", "Director of Product",
  "Head of Engineering", "Head of Product", "Head of Data",
  "Program Manager", "Project Manager", "Scrum Master",
  // 其他技术角色
  "Research Scientist", "Research Engineer",
  "Technical Writer", "Developer Advocate", "Developer Relations",
  "Support Engineer", "Solutions Engineer", "Sales Engineer",
  "Consultant", "Technical Consultant",
  // 非技术但常见
  "Associate", "Senior Associate", "Analyst", "Senior Analyst",
  "Specialist", "Coordinator", "Administrator", "Manager",
  "Assistant", "Representative", "Agent", "Clerk",
  "Accountant", "Auditor", "Controller",
  "Marketing Manager", "Sales Manager", "Operations Manager",
  "HR Manager", "Recruiter", "Talent Acquisition",
  "Intern", "Co-op", "Coop", "Apprentice", "Trainee",
  "Fellow", "Resident", "Postdoc",
  // 学术
  "Professor", "Assistant Professor", "Associate Professor",
  "Lecturer", "Teaching Assistant", "Research Assistant",
];

export const JOB_TITLE_FEATURES: FeatureSet = [
  {
    match: (item) =>
      JOB_TITLE_KEYWORDS.some((kw) => {
        const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        return new RegExp(`\\b${escaped}\\b`, "i").test(item.text);
      }),
    score: 12,
  },
  { match: (item) => item.bold, score: 4 },
  { match: (item) => /^[A-Z][a-z]+(\s+[A-Z][a-z]+){1,4}$/.test(item.text.trim()), score: 1 },
];

// ═══════════════════════════════════════════════
// 公司
// ═══════════════════════════════════════════════

const COMPANY_INDICATORS = [
  "Inc.", "Inc", "LLC", "L.L.C.", "Ltd.", "Ltd", "Limited",
  "Corp.", "Corp", "Corporation", "Co.", "Company",
  "GmbH", "S.A.", "S.L.", "B.V.", "N.V.",
  "Pvt.", "Pvt", "L.L.P.", "LLP", "PLC", "Pty Ltd",
  "Group", "Holdings", "Technologies", "Solutions",
  "Labs", "Studio", "Ventures", "Partners", "Associates",
  "Systems", "Networks", "Dynamics",
  // 知名科技公司
  "Google", "Microsoft", "Apple", "Amazon", "Meta", "Facebook",
  "Netflix", "Uber", "Airbnb", "Stripe", "Square", "Twitter", "X Corp",
  "LinkedIn", "Salesforce", "Oracle", "IBM", "Intel", "AMD", "NVIDIA",
  "Tesla", "SpaceX", "Palantir", "Snowflake", "Databricks",
  "Shopify", "Spotify", "Slack", "Zoom", "Atlassian",
  "Adobe", "SAP", "VMware", "Dell", "HP", "Cisco",
  "Goldman Sachs", "Morgan Stanley", "JPMorgan", "J.P. Morgan",
  "McKinsey", "BCG", "Bain", "Deloitte", "PwC", "EY", "KPMG",
  "Bloomberg", "Two Sigma", "Jane Street", "Citadel",
  "ByteDance", "TikTok", "Tencent", "Alibaba", "Baidu", "Huawei",
];

export const COMPANY_FEATURES: FeatureSet = [
  {
    match: (item) =>
      COMPANY_INDICATORS.some((ind) => {
        const escaped = ind.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        return new RegExp(`\\b${escaped}\\b`, "i").test(item.text);
      }),
    score: 10,
  },
  { match: (item) => item.bold, score: 5 },
  { match: (item) => /^[A-Z][a-zA-Z0-9\s&.\-]+$/.test(item.text) && item.text.length > 4 && !/Engineer|Manager|Developer|Designer|Analyst|Scientist/i.test(item.text), score: 2 },
];

// ═══════════════════════════════════════════════
// 技能关键词 — 150+ 常见技术技能
// ═══════════════════════════════════════════════

const TECH_SKILLS = [
  // 语言
  "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C",
  "Go", "Golang", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala",
  "R", "MATLAB", "Perl", "Lua", "Haskell", "Clojure", "Elixir", "Erlang",
  "Dart", "Objective-C", "Assembly", "Bash", "Shell", "PowerShell",
  "SQL", "T-SQL", "PL/SQL", "HTML", "CSS", "Sass", "SCSS", "Less",
  // 框架/库
  "React", "React.js", "React Native", "Vue", "Vue.js", "Angular",
  "Next.js", "Nuxt.js", "Svelte", "Gatsby", "Remix", "Astro",
  "Node.js", "Node", "Express", "Express.js", "NestJS", "Fastify",
  "Django", "Flask", "FastAPI", "Spring", "Spring Boot", "Hibernate",
  "Ruby on Rails", "Rails", "Laravel", "ASP.NET", ".NET",
  "Redux", "MobX", "Zustand", "Pinia", "NgRx",
  "jQuery", "Bootstrap", "Tailwind", "Tailwind CSS", "Material UI", "MUI",
  "GraphQL", "Apollo", "REST", "gRPC", "tRPC",
  "PyTorch", "TensorFlow", "Keras", "scikit-learn", "XGBoost",
  "Pandas", "NumPy", "SciPy", "Matplotlib", "Seaborn",
  "OpenCV", "Hugging Face", "Transformers", "spaCy", "NLTK",
  "LangChain", "LlamaIndex", "CrewAI", "LangGraph",
  // 工具/平台
  "Git", "GitHub", "GitLab", "Bitbucket",
  "Docker", "Kubernetes", "k8s", "Helm", "Terraform",
  "AWS", "Amazon Web Services", "Azure", "GCP", "Google Cloud Platform",
  "Firebase", "Vercel", "Netlify", "Heroku", "DigitalOcean",
  "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI",
  "Linux", "Unix", "Windows Server", "MacOS",
  "Nginx", "Apache", "Redis", "RabbitMQ", "Kafka",
  "PostgreSQL", "MySQL", "MongoDB", "SQLite", "DynamoDB",
  "Elasticsearch", "Solr", "Cassandra", "Neo4j", "Snowflake",
  "Jira", "Confluence", "Notion", "Figma", "Sketch",
  "Tableau", "Power BI", "Looker", "Metabase",
  "Prometheus", "Grafana", "Datadog", "Splunk",
  "Agile", "Scrum", "Kanban", "Waterfall",
];

/** 检查文本项是否为技能（匹配技能列表或满足特定格式） */
function isSkill(item: { text: string }): boolean {
  const trimmed = item.text.trim();
  if (trimmed.length < 2 || trimmed.length > 50) return false;
  // 精确匹配技能列表
  if (TECH_SKILLS.some((s) => trimmed.toLowerCase() === s.toLowerCase())) return true;
  // 常见技术栈格式: 单个词且首字母大写（如 "Python", "Docker"）
  if (/^[A-Z][a-zA-Z0-9+#.]+$/.test(trimmed) && trimmed.length >= 2 && trimmed.length <= 30) return true;
  // 组合词: 如 "C++", "Node.js", "React Native"
  if (/^[A-Z][a-zA-Z0-9+#.]{1,4}$/.test(trimmed)) return true;
  // 首字母缩写: AWS, GCP, NLP, SQL
  if (/^[A-Z]{2,6}$/.test(trimmed)) return true;
  return false;
}

export const SKILL_MATCHER = { isSkill, TECH_SKILLS };
