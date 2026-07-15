/**
 * Step 2: 将碎片化文本项合并为行
 *
 * 算法：
 *   1. 按 Y 坐标分组（Y 容差内视为同一行）
 *   2. 组内按 X 坐标排序
 *   3. 水平合并：相邻文本项间隙 < 平均字符宽度 → 合并
 *   4. 按 Y 降序排列（从上到下）
 */

import type { TextItem, TextItems, Line, Lines } from "./types";

/**
 * 计算文本项中字符的平均宽度
 */
function estimateAverageCharWidth(items: TextItems): number {
  let totalWidth = 0;
  let totalChars = 0;
  for (const item of items) {
    const charCount = item.text.length;
    if (charCount > 0) {
      totalWidth += item.width;
      totalChars += charCount;
    }
  }
  return totalChars > 0 ? totalWidth / totalChars : 5; // 默认 5px
}

/**
 * 合并同一行内相邻的文本项（消除 PDF 碎片化）
 */
function mergeAdjacentInLine(line: Line, avgCharWidth: number): Line {
  if (line.length <= 1) return line;

  // 按 X 坐标排序
  const sorted = [...line].sort((a, b) => a.x1 - b.x1);

  const merged: Line = [sorted[0]];

  for (let i = 1; i < sorted.length; i++) {
    const prev = merged[merged.length - 1];
    const curr = sorted[i];
    const gap = curr.x1 - prev.x2;

    if (gap < avgCharWidth * 0.8) {
      // 合并：更新 x2 和文本
      prev.text += curr.text;
      prev.x2 = curr.x2;
      prev.width = prev.x2 - prev.x1;
    } else if (gap < avgCharWidth * 3) {
      // 添加空格后合并（正常词间距）
      prev.text += " " + curr.text;
      prev.x2 = curr.x2;
      prev.width = prev.x2 - prev.x1;
    } else {
      // 间距过大，不合并
      merged.push(curr);
    }
  }

  return merged;
}

/**
 * 将文本项按行分组
 */
export function groupTextItemsIntoLines(textItems: TextItems): Lines {
  if (textItems.length === 0) return [];

  const avgCharWidth = estimateAverageCharWidth(textItems);

  // 1. 按 Y 坐标分组（Y 容差 = 平均字符高度的 1/3）
  const avgHeight =
    textItems.reduce((sum, item) => sum + item.height, 0) / textItems.length;
  const yTolerance = avgHeight * 0.4;

  // 按 Y 坐标降序排序（页面从上到下）
  const sorted = [...textItems].sort((a, b) => a.y - b.y);

  // 分组
  const groups: TextItems[] = [];
  for (const item of sorted) {
    let placed = false;
    for (const group of groups) {
      const groupY = group[0].y;
      if (Math.abs(item.y - groupY) <= yTolerance) {
        group.push(item);
        placed = true;
        break;
      }
    }
    if (!placed) {
      groups.push([item]);
    }
  }

  // 2. 每组内按 X 排序并合并
  const lines: Lines = [];
  for (const group of groups) {
    const mergedLine = mergeAdjacentInLine(group, avgCharWidth);
    lines.push(mergedLine);
  }

  // 3. 按 Y 降序排列（页面从上到下）
  lines.sort((a, b) => a[0].y - b[0].y);

  return lines;
}
