import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Language = "zh" | "en";

const languageStorageKey = "noviscope-language";

const en = {
  authFeatureInviteDescription: "Registration requires an invite code issued by a lab administrator.",
  authFeatureInviteTitle: "Invite access",
  authFeatureProviderDescription: "Configure personal or shared model endpoints through the same API.",
  authFeatureProviderTitle: "Provider setup",
  authFeatureQuestDescription: "Manage research directions, workflow stages, and review notes.",
  authFeatureQuestTitle: "Quest tracking",
  authWorkspaceSubtitle: "Authenticated research workspace",
  backendConnectionIssue: "Backend connection issue",
  checkingSession: "Checking session",
  createAccount: "Create Account",
  created: "Created",
  displayName: "Display Name",
  email: "Email",
  guest: "Guest",
  initialDirectionPreview: "Initial Research Direction Preview",
  inviteCode: "Invite Code",
  labAlphaDescription: "Shared providers and quest workflows are available through the current API.",
  labAlphaTitle: "Lab alpha",
  languageLabel: "Language",
  languageChinese: "中文",
  languageEnglish: "English",
  loadingProviderData: "Loading providers...",
  loadingQuestDetail: "Loading quest detail...",
  loadingQuests: "Loading quests...",
  login: "Login",
  loginDescription: "Sign in with your lab account to access quests and provider settings.",
  logout: "Logout",
  navNewQuest: "New Quest",
  navProviders: "Providers",
  navQuests: "Quests",
  noProvidersAvailable: "No providers available yet.",
  noQuestsAvailable: "No quests available yet.",
  noQuestsMatch: "No quests match the current filter.",
  noStagesFound: "No stages found for this quest.",
  noSummaryYet: "No summary yet.",
  open: "Open",
  password: "Password",
  passwordHint: "Use at least eight characters.",
  providerAddDescription: "Create a new provider using the current backend contract.",
  providerAddTitle: "Add Provider",
  providerApiKey: "API Key",
  providerBaseUrl: "Base URL",
  providerDefaultModel: "Default Model",
  providerKind: "Provider Kind",
  providerListDescription: "List the providers visible to the current user. Shared providers are admin-managed.",
  providerName: "Name",
  providerScope: "Scope",
  providerScopeSharedHint: "Admins may create personal or shared providers.",
  providerScopePersonalHint: "Members can create personal providers only.",
  providerSave: "Save Provider",
  providerSignInPrompt: "Sign in to load provider data. The table and form still render so the UI can be reviewed without API data.",
  protectedSessionDescription: "Confirming access to the NoviScope workspace.",
  questCreate: "Create Quest",
  questCreatedFromForm: "Created from structured NoviScope intake.",
  questDataAssets: "Data, code, or resources already available",
  questDataAssetsHint: "Optional. Note datasets, company samples, repos, annotation status, or GPU limits.",
  questDataAssetsPlaceholder: "Unfilled exam images from enterprise partner; no public paired dataset yet.",
  questDirection: "Research direction",
  questDirectionHint: "Required. Two or three sentences are enough; the system will refine it later.",
  questDirectionPlaceholder: "Erase handwritten answers from scanned exam sheets and recover the clean original worksheet.",
  questExampleBadminton: "Use badminton example",
  questExampleErasure: "Use erasure example",
  questExpectedOutput: "Expected research output",
  questExpectedOutputPlaceholder: "A demand validation brief, baseline map, improvement idea, and feasible experiment plan.",
  questExperimentSection: "Experiment Readiness",
  questExperimentSectionDescription: "Enough context for the system to judge data, baseline, metric, and first experiment feasibility.",
  questFormDescription: "Turn a rough direction into a traceable research brief for demand validation, literature scouting, and experiment planning.",
  questKnownWork: "Known papers, methods, or baselines",
  questKnownWorkHint: "Optional. It is fine to write unknown; Literature Scout can fill this later.",
  questKnownWorkPlaceholder: "Document inpainting, text removal, OCR-guided mask generation; exact baselines unknown.",
  questListDescription: "Manage research quests and inspect their current workflow stages.",
  questMetric: "Evaluation metric or success signal",
  questMetricPlaceholder: "OCR accuracy recovery, background fidelity, human preference, PSNR/SSIM if paired data exists.",
  questOutputLanguage: "Output language",
  questOutputLanguageBoth: "Chinese + English",
  questOutputLanguageEn: "English",
  questOutputLanguageZh: "Chinese",
  questPainPoint: "Current pain point or suspected gap",
  questPainPointPlaceholder: "Existing inpainting models may damage printed text, tables, and thin worksheet lines.",
  questRealitySection: "Demand Reality",
  questRealitySectionDescription: "These fields help avoid pseudo-problems before experiments start.",
  questScenario: "Real-world scenario or demand source",
  questScenarioHint: "Important. Name the user, company, lab scenario, or observable demand when possible.",
  questScenarioPlaceholder: "Education company reuses completed exam sheets and needs to remove student handwriting.",
  questSearch: "Search",
  questSearchPlaceholder: "Search quests...",
  questSignInPrompt: "Sign in to load quest data from the API.",
  questStatus: "Status",
  questSubmitHint: "The structured answers will be saved into Initial Research Direction for the first agent stage.",
  questTarget: "Input and desired output",
  questTargetPlaceholder: "Input: filled scanned worksheet. Output: clean worksheet with printed content preserved.",
  questTitle: "Quest title",
  questTitlePlaceholder: "Handwritten text erasure for exam sheets",
  questUnknownOption: "Not sure yet",
  register: "Register",
  registerDescription: "Use an invite code created by an administrator to create your account.",
  reviewNotes: "Review notes",
  runDemandValidation: "Run demand validation",
  runStage: "Run",
  scopePersonal: "Personal",
  scopeShared: "Shared",
  selectQuestForStages: "Select a quest to inspect its stages.",
  signIn: "Sign In",
  signInFirstQuest: "Sign in first to create a quest. The form stays available here so the route can still be validated during UI smoke tests.",
  signInPrompt: "Sign in to access lab data",
  stageRunBlocked: "Stage run was blocked. Review the reason before continuing.",
  stageRunComplete: "Stage run completed and wrote results back.",
  statusAll: "All statuses",
  tableDirection: "Direction",
  tableKind: "Kind",
  tableModel: "Model",
  tableName: "Name",
  tableScope: "Scope",
  tableStatus: "Status",
  tableTitle: "Title",
  updated: "Updated",
  workflowDescription: "Workflow stages for the selected quest.",
  workflowTitle: "Workflow",
  workspaceSubtitle: "Lab workspace",
} as const;

const zh: Record<keyof typeof en, string> = {
  authFeatureInviteDescription: "注册需要使用实验室管理员创建的邀请码。",
  authFeatureInviteTitle: "邀请码准入",
  authFeatureProviderDescription: "通过同一套 API 配置个人或课题组共享模型端点。",
  authFeatureProviderTitle: "模型配置",
  authFeatureQuestDescription: "管理科研方向、工作流阶段和复核记录。",
  authFeatureQuestTitle: "课题追踪",
  authWorkspaceSubtitle: "需要登录的科研工作台",
  backendConnectionIssue: "后端连接异常",
  checkingSession: "正在检查会话",
  createAccount: "创建账号",
  created: "创建时间",
  displayName: "显示名称",
  email: "邮箱",
  guest: "访客",
  initialDirectionPreview: "Initial Research Direction 预览",
  inviteCode: "邀请码",
  labAlphaDescription: "当前 API 已支持共享 provider 和 quest 工作流。",
  labAlphaTitle: "Lab Alpha",
  languageLabel: "语言",
  languageChinese: "中文",
  languageEnglish: "English",
  loadingProviderData: "正在加载模型配置...",
  loadingQuestDetail: "正在加载 Quest 详情...",
  loadingQuests: "正在加载 Quest...",
  login: "登录",
  loginDescription: "使用课题组账号登录后访问 Quest 和模型配置。",
  logout: "退出登录",
  navNewQuest: "新建 Quest",
  navProviders: "模型配置",
  navQuests: "Quest 列表",
  noProvidersAvailable: "还没有可用的模型配置。",
  noQuestsAvailable: "还没有创建 Quest。",
  noQuestsMatch: "没有 Quest 匹配当前筛选条件。",
  noStagesFound: "当前 Quest 还没有工作流阶段。",
  noSummaryYet: "暂无摘要。",
  open: "打开",
  password: "密码",
  passwordHint: "至少使用 8 个字符。",
  providerAddDescription: "按照当前后端协议创建一个新的模型 provider。",
  providerAddTitle: "添加 Provider",
  providerApiKey: "API Key",
  providerBaseUrl: "Base URL",
  providerDefaultModel: "默认模型",
  providerKind: "Provider 类型",
  providerListDescription: "查看当前用户可用的模型 provider。共享 provider 由管理员维护。",
  providerName: "名称",
  providerScope: "作用范围",
  providerScopeSharedHint: "管理员可以创建个人或课题组共享 provider。",
  providerScopePersonalHint: "普通成员只能创建个人 provider。",
  providerSave: "保存 Provider",
  providerSignInPrompt: "登录后加载模型配置数据。当前表格和表单仍会渲染，便于无 API 数据时检查界面。",
  protectedSessionDescription: "正在确认是否可以访问 NoviScope 工作台。",
  questCreate: "创建 Quest",
  questCreatedFromForm: "由 NoviScope 结构化采集表创建。",
  questDataAssets: "已有数据、代码或资源",
  questDataAssetsHint: "选填。可以写数据集、企业样本、代码仓库、标注状态或 GPU 限制。",
  questDataAssetsPlaceholder: "企业提供的已填写试卷图片；暂时没有公开成对数据集。",
  questDirection: "研究方向",
  questDirectionHint: "必填。两三句话就够，后续系统会继续细化。",
  questDirectionPlaceholder: "擦除扫描试卷中的手写答案，并恢复成干净的原始试卷。",
  questExampleBadminton: "填入羽毛球示例",
  questExampleErasure: "填入手写擦除示例",
  questExpectedOutput: "期望科研产出",
  questExpectedOutputPlaceholder: "需求验证简报、baseline 地图、改进 idea 和可行实验计划。",
  questExperimentSection: "实验准备度",
  questExperimentSectionDescription: "帮助系统判断数据、baseline、指标和第一步实验是否可行。",
  questFormDescription: "把粗略方向转化为可追踪的科研 brief，用于需求验证、文献检索和实验规划。",
  questKnownWork: "已知论文、方法或 baseline",
  questKnownWorkHint: "选填。不知道可以写 unknown，Literature Scout 后续会补。",
  questKnownWorkPlaceholder: "文档修复、文本移除、OCR 引导 mask 生成；具体 baseline 还不确定。",
  questListDescription: "管理科研 Quest，并查看当前工作流阶段。",
  questMetric: "评价指标或成功信号",
  questMetricPlaceholder: "OCR 恢复准确率、背景保真度、人工偏好；如果有成对数据再用 PSNR/SSIM。",
  questOutputLanguage: "产出语言",
  questOutputLanguageBoth: "中文 + 英文",
  questOutputLanguageEn: "英文",
  questOutputLanguageZh: "中文",
  questPainPoint: "当前痛点或可能 gap",
  questPainPointPlaceholder: "现有 inpainting 模型可能破坏印刷文字、表格和试卷细线。",
  questRealitySection: "需求真实性",
  questRealitySectionDescription: "这些字段用于在实验前避免伪需求。",
  questScenario: "真实应用场景或需求来源",
  questScenarioHint: "重要。尽量写清用户、企业、实验室场景或可观察需求。",
  questScenarioPlaceholder: "教培企业想复用已填写试卷，需要擦除学生手写内容。",
  questSearch: "搜索",
  questSearchPlaceholder: "搜索 Quest...",
  questSignInPrompt: "登录后从 API 加载 Quest 数据。",
  questStatus: "状态",
  questSubmitHint: "这些结构化回答会汇总保存到 Initial Research Direction，供第一个 agent 阶段使用。",
  questTarget: "输入与期望输出",
  questTargetPlaceholder: "输入：已填写扫描试卷。输出：保留印刷内容的干净试卷。",
  questTitle: "Quest 标题",
  questTitlePlaceholder: "面向试卷复用的手写文本擦除",
  questUnknownOption: "暂不确定",
  register: "注册",
  registerDescription: "使用管理员创建的邀请码注册实验室账号。",
  reviewNotes: "复核备注",
  runDemandValidation: "运行需求验证",
  runStage: "运行",
  scopePersonal: "个人",
  scopeShared: "共享",
  selectQuestForStages: "选择一个 Quest 查看它的工作流阶段。",
  signIn: "登录",
  signInFirstQuest: "请先登录再创建 Quest。当前表单仍会显示，便于在 UI smoke test 中验证路由。",
  signInPrompt: "登录后访问课题组数据",
  stageRunBlocked: "阶段运行被阻断，请先查看原因再继续。",
  stageRunComplete: "阶段运行完成，结果已写回。",
  statusAll: "全部状态",
  tableDirection: "方向",
  tableKind: "类型",
  tableModel: "模型",
  tableName: "名称",
  tableScope: "作用范围",
  tableStatus: "状态",
  tableTitle: "标题",
  updated: "更新时间",
  workflowDescription: "所选 Quest 的工作流阶段。",
  workflowTitle: "工作流",
  workspaceSubtitle: "课题组工作台",
};

const translations: Record<Language, Record<keyof typeof en, string>> = { en, zh };

type TranslationKey = keyof typeof en;

type I18nContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function readInitialLanguage(): Language {
  if (typeof window === "undefined") {
    return "zh";
  }

  try {
    return window.localStorage.getItem(languageStorageKey) === "en" ? "en" : "zh";
  } catch {
    return "zh";
  }
}

function persistLanguagePreference(language: Language) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(languageStorageKey, language);
  } catch {
    return;
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readInitialLanguage);

  const setLanguage = (nextLanguage: Language) => {
    setLanguageState(nextLanguage);
  };

  useEffect(() => {
    persistLanguagePreference(language);
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key) => translations[language][key],
    }),
    [language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}
