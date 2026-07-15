/**
 * Step 1: 使用 PDF.js 从 PDF 文件中提取文本项
 *
 * 在浏览器端完全本地运行，无需上传数据到服务器。
 */

import * as pdfjsLib from "pdfjs-dist";
import type { TextItem, TextItems } from "./types";

// 配置 PDF.js worker（使用本地安装的版本，与 pdfjs-dist 包版本一致）
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

/**
 * PDF.js getTextContent() 返回的原始文本项格式
 */
interface PdfJsTextItem {
  str: string;
  transform: number[];
  width: number;
  height: number;
  fontName: string;
  hasEOL: boolean;
}

/**
 * 从 PDF transform 矩阵估算字号
 * transform[0] 是水平缩放因子 ≈ 字号（pt）
 */
function extractFontSize(transform: number[], height: number): number {
  // transform[0] 是 scaleX，对于标准文本缩放 ≈ 字号(pt)
  const scale = Math.abs(transform[0]);
  // height 是渲染后的高度，除以 scale 得到原始字号
  // 优先用 transform[0]，回退到 height
  return scale > 0 ? Math.round(scale) : Math.round(height);
}

/**
 * 判断字体是否加粗（多种启发式）
 */
function isBoldByFontName(fontName: string, fontSize: number): boolean {
  const lower = fontName.toLowerCase();
  // 常见加粗字体名
  if (/bold|heavy|black|semibold|demi/i.test(lower)) return true;
  // 没有字体名信息时，大字号的标题通常是加粗的
  return false;
}

/**
 * 从 PDF 文件中提取所有文本项（含坐标和字体信息）
 */
export async function readPdf(file: File): Promise<TextItems> {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const allTextItems: TextItems = [];

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();

    const viewport = page.getViewport({ scale: 1 });
    const pageHeight = viewport.height;

    for (const item of textContent.items) {
      const raw = item as unknown as PdfJsTextItem;
      if (!raw.str || raw.str.trim() === "") continue;

      const fontSize = extractFontSize(raw.transform, raw.height);

      const textItem: TextItem = {
        text: raw.str,
        x1: raw.transform[4],
        x2: raw.transform[4] + raw.width,
        y: pageHeight - raw.transform[5],
        height: raw.height,
        width: raw.width,
        fontSize,
        fontName: raw.fontName || "",
        bold: isBoldByFontName(raw.fontName || "", fontSize),
        newLine: raw.hasEOL || false,
      };

      allTextItems.push(textItem);
    }
  }

  return allTextItems;
}
