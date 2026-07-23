export const INVALID_QUERY_MESSAGE = "输入内容不合法，请修改后重试";

const PROHIBITED_TERM_GROUPS = [
  {
    category: "涉黄",
    terms: [
      "色情",
      "成人视频",
      "成人影片",
      "无码影片",
      "裸露影像",
      "露骨内容",
      "黄色网站",
      "裸聊",
      "淫秽",
      "约炮",
      "性服务",
      "卖淫",
      "嫖娼",
    ],
  },
  {
    category: "涉赌",
    terms: [
      "赌博",
      "博彩",
      "赌场",
      "赌钱",
      "赌局",
      "下注",
      "赌资",
      "洗码",
      "百家乐",
      "轮盘",
      "老虎机",
      "牌九",
      "德州扑克",
      "casino",
      "gambling",
      "betting",
    ],
  },
  {
    category: "涉毒",
    terms: [
      "毒品",
      "制毒",
      "贩毒",
      "吸毒",
      "冰毒",
      "海洛因",
      "摇头丸",
      "麻古",
      "可卡因",
      "k粉",
      "违禁粉末",
      "cocaine",
      "heroin",
      "methamphetamine",
      "芬太尼滥用",
    ],
  },
] as const;

export type UnsafeQueryCategory =
  (typeof PROHIBITED_TERM_GROUPS)[number]["category"];

const normalizeQuery = (value: string): string =>
  value
    .normalize("NFKC")
    .toLocaleLowerCase("zh-CN")
    .replace(/[^\p{L}\p{N}]+/gu, "");

export const classifyUnsafeQuery = (
  value: string,
): UnsafeQueryCategory | undefined => {
  const normalized = normalizeQuery(value);
  return PROHIBITED_TERM_GROUPS.find((group) =>
    group.terms.some((term) => normalized.includes(normalizeQuery(term))),
  )?.category;
};

export const getQuerySafetyMessage = (value: string): string | undefined =>
  classifyUnsafeQuery(value) === undefined ? undefined : INVALID_QUERY_MESSAGE;
