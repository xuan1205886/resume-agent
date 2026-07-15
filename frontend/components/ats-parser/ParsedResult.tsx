"use client";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import type { ParsedResume } from "@/lib/ats-parser";

interface ParsedResultProps {
  resume: ParsedResume;
}

export function ParsedResult({ resume }: ParsedResultProps) {
  const { profile, workExperiences, educations, projects, skills } = resume;

  return (
    <div>
      <h3 className="font-bold text-gray-900 mb-3">📋 结构化解析结果</h3>
      <p className="text-xs text-gray-500 mb-3">
        以下展示了 ATS 系统（如 Greenhouse、Lever）从你简历中读取到的内容
      </p>

      <Accordion multiple defaultValue={["profile"]} className="space-y-2">
        {/* 个人信息 */}
        <AccordionItem value="profile" className="border rounded-lg px-3">
          <AccordionTrigger className="hover:no-underline py-2">
            <span className="text-sm font-semibold">👤 个人信息</span>
          </AccordionTrigger>
          <AccordionContent className="text-sm pb-3 space-y-1">
            <InfoRow label="姓名" value={profile.name} />
            <InfoRow label="邮箱" value={profile.email} />
            <InfoRow label="电话" value={profile.phone} />
            <InfoRow label="网址" value={profile.url} />
            <InfoRow label="地点" value={profile.location} />
            {profile.summary && (
              <div className="mt-2">
                <span className="text-gray-500 text-xs">简介:</span>
                <p className="text-gray-600 text-xs mt-0.5 whitespace-pre-wrap">
                  {profile.summary.slice(0, 300)}
                </p>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        {/* 工作经历 */}
        <AccordionItem value="experience" className="border rounded-lg px-3">
          <AccordionTrigger className="hover:no-underline py-2">
            <span className="text-sm font-semibold">
              💼 工作经历
              <Badge variant="secondary" className="ml-2 text-xs">
                {workExperiences.length}
              </Badge>
            </span>
          </AccordionTrigger>
          <AccordionContent className="text-sm pb-3 space-y-3">
            {workExperiences.length === 0 ? (
              <p className="text-gray-400 text-xs">未提取到工作经历</p>
            ) : (
              workExperiences.map((exp, i) => (
                <div key={i} className="border-l-2 border-blue-300 pl-3">
                  <p className="font-semibold text-gray-800">
                    {exp.jobTitle || "未知职位"}
                  </p>
                  <p className="text-gray-600 text-xs">
                    {exp.company}
                    {exp.date ? ` | ${exp.date}` : ""}
                  </p>
                  {exp.descriptions.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {exp.descriptions.slice(0, 5).map((d, j) => (
                        <li key={j} className="text-xs text-gray-500">
                          • {d.slice(0, 150)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))
            )}
          </AccordionContent>
        </AccordionItem>

        {/* 教育背景 */}
        <AccordionItem value="education" className="border rounded-lg px-3">
          <AccordionTrigger className="hover:no-underline py-2">
            <span className="text-sm font-semibold">
              🎓 教育背景
              <Badge variant="secondary" className="ml-2 text-xs">
                {educations.length}
              </Badge>
            </span>
          </AccordionTrigger>
          <AccordionContent className="text-sm pb-3 space-y-2">
            {educations.length === 0 ? (
              <p className="text-gray-400 text-xs">未提取到教育背景</p>
            ) : (
              educations.map((edu, i) => (
                <div key={i} className="border-l-2 border-green-300 pl-3">
                  <p className="font-semibold text-gray-800">
                    {edu.school || "未知学校"}
                  </p>
                  <p className="text-gray-600 text-xs">
                    {edu.degree}
                    {edu.date ? ` | ${edu.date}` : ""}
                    {edu.gpa ? ` | GPA: ${edu.gpa}` : ""}
                  </p>
                </div>
              ))
            )}
          </AccordionContent>
        </AccordionItem>

        {/* 项目 */}
        {projects.length > 0 && (
          <AccordionItem value="projects" className="border rounded-lg px-3">
            <AccordionTrigger className="hover:no-underline py-2">
              <span className="text-sm font-semibold">
                🚀 项目
                <Badge variant="secondary" className="ml-2 text-xs">
                  {projects.length}
                </Badge>
              </span>
            </AccordionTrigger>
            <AccordionContent className="text-sm pb-3 space-y-2">
              {projects.map((proj, i) => (
                <div key={i} className="border-l-2 border-purple-300 pl-3">
                  <p className="font-semibold text-gray-800">
                    {proj.project}
                    {proj.date ? ` (${proj.date})` : ""}
                  </p>
                  {proj.descriptions.slice(0, 3).map((d, j) => (
                    <p key={j} className="text-xs text-gray-500">
                      • {d.slice(0, 150)}
                    </p>
                  ))}
                </div>
              ))}
            </AccordionContent>
          </AccordionItem>
        )}

        {/* 技能 */}
        <AccordionItem value="skills" className="border rounded-lg px-3">
          <AccordionTrigger className="hover:no-underline py-2">
            <span className="text-sm font-semibold">
              🔧 技能
              <Badge variant="secondary" className="ml-2 text-xs">
                {skills.featuredSkills.length}
              </Badge>
            </span>
          </AccordionTrigger>
          <AccordionContent className="text-sm pb-3">
            {skills.featuredSkills.length === 0 ? (
              <p className="text-gray-400 text-xs">未提取到技能列表</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {skills.featuredSkills.map((s, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {s.skill}
                  </Badge>
                ))}
              </div>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-8">{label}:</span>
      <span className={value ? "text-gray-800 font-medium" : "text-red-400"}>
        {value || "❌ 未识别"}
      </span>
    </div>
  );
}
