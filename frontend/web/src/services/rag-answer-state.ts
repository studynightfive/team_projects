const NO_DOCUMENT_EVIDENCE_MARKERS = [
  "未在文档中找到相关信息",
  "未在文档中找到相关引用",
  "未在文档找到相关信息",
  "未在文档找到相关引用",
  "未能在文档中找到相关信息",
  "文档中未找到相关信息",
  "提供的资料不足以回答",
  "现有资料不足以回答",
  "文档内容不足以回答",
] as const;

const DYNAMIC_NO_DOCUMENT_EVIDENCE_PATTERN =
  /未(?:能)?在文档(?:中)?找到.{0,40}相关(?:信息|引用)/u;
const NO_DOCUMENT_EVIDENCE_SECTION_PATTERN =
  /\n+(?:#{1,6}\s*)?(?:\*\*|__)?(?:关键依据|结论依据|引用来源|参考依据)\s*[:：]?(?:\*\*|__)?/u;

/** 只检查回答开头，避免正文讨论局部资料缺失时误删其他有效引用。 */
export const isNoDocumentEvidenceAnswer = (answer: string): boolean => {
  const normalized = answer
    .replace(/\s+/gu, "")
    .replace(/^[#>*`_\-:：，,。.!！]+/u, "")
    .slice(0, 100);
  return (
    NO_DOCUMENT_EVIDENCE_MARKERS.some((marker) =>
      normalized.includes(marker),
    ) || DYNAMIC_NO_DOCUMENT_EVIDENCE_PATTERN.test(normalized)
  );
};

export const sanitizeNoDocumentEvidenceAnswer = (answer: string): string => {
  if (!isNoDocumentEvidenceAnswer(answer)) return answer;
  return answer.split(NO_DOCUMENT_EVIDENCE_SECTION_PATTERN, 1)[0]?.trimEnd() ?? "";
};
