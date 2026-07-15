/**
 * Step 4 核心：特征评分系统
 *
 * 对一组文本项按特征集进行评分，返回总分最高的文本项。
 * 这是整个解析器最关键的智能组件。
 */

import type { TextItems, FeatureSet, TextScores } from "./types";

/**
 * 对一组文本项按特征集评分
 */
export function computeFeatureScores(
  textItems: TextItems,
  featureSet: FeatureSet
): TextScores {
  return textItems.map((item) => {
    let score = 0;
    for (const feature of featureSet) {
      if (feature.match(item)) {
        score += feature.score;
      }
    }
    return { text: item.text, score };
  });
}

/**
 * 获取评分最高的文本项
 *
 * @param textItems       - 候选文本项
 * @param featureSet      - 特征集（一组 Feature）
 * @param returnEmptyIfNotPositive - 如果最高分 <= 0，返回空
 * @param concatenateSameScore      - 多个同分项是否拼接
 */
export function getTextWithHighestFeatureScore(
  textItems: TextItems,
  featureSet: FeatureSet,
  returnEmptyIfNotPositive = true,
  concatenateSameScore = false
): { text: string; scores: TextScores } {
  const scores = computeFeatureScores(textItems, featureSet);

  // 找到最高分
  let highestScore = -Infinity;
  const textsWithHighestScore: string[] = [];

  for (const { text, score } of scores) {
    const trimmed = text.trim();
    if (score > highestScore) {
      textsWithHighestScore.length = 0;
      textsWithHighestScore.push(trimmed);
      highestScore = score;
    } else if (score === highestScore && score > 0) {
      textsWithHighestScore.push(trimmed);
    }
  }

  if (returnEmptyIfNotPositive && highestScore <= 0) {
    return { text: "", scores };
  }

  const text = concatenateSameScore
    ? textsWithHighestScore.map((s) => s.trim()).join(" ")
    : textsWithHighestScore[0] || "";

  return { text, scores };
}

/**
 * 获取整行文本（将一行中所有文本项拼接）
 */
export function getLineText(line: TextItems): string {
  return line.map((item) => item.text).join(" ").trim();
}

/**
 * 获取章节中所有行的文本列表
 */
export function getSectionLines(lines: TextItems[]): string[] {
  return lines.map((line) => getLineText(line)).filter((t) => t.length > 0);
}
