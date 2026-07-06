export type OutputLanguage = "zh" | "en" | "both";

export type QuestIntakeState = {
  readonly dataAssets: string;
  readonly demandEvidenceSources: string;
  readonly direction: string;
  readonly expectedOutput: string;
  readonly knownWork: string;
  readonly metric: string;
  readonly outputLanguage: OutputLanguage;
  readonly painPoint: string;
  readonly scenario: string;
  readonly target: string;
  readonly targetUser: string;
  readonly title: string;
};

type IntakeLabels = {
  readonly dataAssets: string;
  readonly demandEvidenceSources: string;
  readonly direction: string;
  readonly empty: string;
  readonly expectedOutput: string;
  readonly knownWork: string;
  readonly metric: string;
  readonly note: string;
  readonly outputLanguage: string;
  readonly outputLanguageValues: Record<OutputLanguage, string>;
  readonly painPoint: string;
  readonly scenario: string;
  readonly target: string;
  readonly targetUser: string;
  readonly title: string;
};

export const emptyIntake: QuestIntakeState = {
  dataAssets: "",
  demandEvidenceSources: "",
  direction: "",
  expectedOutput: "",
  knownWork: "",
  metric: "",
  outputLanguage: "both",
  painPoint: "",
  scenario: "",
  target: "",
  targetUser: "",
  title: "",
};

export const questIntakeExamples: Record<"zh" | "en", Record<"erasure" | "badminton", QuestIntakeState>> = {
  en: {
    badminton: {
      dataAssets: "Court videos from training sessions; annotation plan is not fixed yet.",
      demandEvidenceSources:
        "Coach or training analyst interview notes to verify; available training video samples to inspect.",
      direction: "Use computer vision to recognize badminton shuttle trajectory or player actions from match/training videos.",
      expectedOutput: "Validate whether the task has enough value, list datasets/baselines, and propose the first feasible experiment.",
      knownWork: "Sports pose estimation, shuttle tracking, action recognition, temporal modeling.",
      metric: "Trajectory localization error, action classification accuracy, frame-level consistency, and coach usability feedback.",
      outputLanguage: "both",
      painPoint: "Fast shuttle motion, occlusion, motion blur, and limited annotated badminton-specific data.",
      scenario: "AI + sports training: coaches want objective feedback on shuttle trajectory and athlete actions.",
      target: "Input: badminton video. Output: shuttle trajectory, action labels, and structured analysis for training review.",
      targetUser: "Badminton coaches, athletes, and training analysts who review practice or match videos.",
      title: "Badminton trajectory and action recognition",
    },
    erasure: {
      dataAssets: "Enterprise exam-sheet scans may be available; public paired data is uncertain.",
      demandEvidenceSources:
        "Education-company worksheet reuse request to verify with contact; sample filled/clean exam-sheet scans if available.",
      direction: "Erase handwritten answers from scanned exam sheets and recover a clean worksheet for reuse.",
      expectedOutput: "Demand validation brief, related-work map, candidate improvement idea, and experiment plan.",
      knownWork: "Document inpainting, scene text removal, OCR-guided masks, diffusion/inpainting baselines.",
      metric: "Printed-content preservation, OCR recovery, human preference, and PSNR/SSIM if paired clean sheets exist.",
      outputLanguage: "both",
      painPoint: "Existing inpainting may damage printed text, table borders, and thin worksheet lines.",
      scenario: "Education company reuses completed exam sheets and needs to remove students' handwriting.",
      target: "Input: filled scanned worksheet. Output: clean worksheet with printed content preserved.",
      targetUser: "Education companies, teachers, and content teams that need reusable clean worksheets.",
      title: "Handwritten text erasure for reusable exam sheets",
    },
  },
  zh: {
    badminton: {
      dataAssets: "训练或比赛视频可能可采集；标注方案暂未固定。",
      demandEvidenceSources: "待核验的教练或训练分析人员访谈记录；可检查的训练视频样本。",
      direction: "使用机器视觉识别羽毛球轨迹或运动员动作，用于训练复盘和动作分析。",
      expectedOutput: "验证任务价值，梳理数据集和 baseline，并提出第一步可行实验。",
      knownWork: "体育姿态估计、羽毛球检测/跟踪、动作识别、时序建模。",
      metric: "轨迹定位误差、动作分类准确率、帧间一致性，以及教练使用反馈。",
      outputLanguage: "both",
      painPoint: "羽毛球速度快、遮挡多、运动模糊明显，并且专门标注数据有限。",
      scenario: "AI + 体育训练场景：教练希望获得客观的羽毛球轨迹和动作反馈。",
      target: "输入：羽毛球训练或比赛视频。输出：球轨迹、动作标签和训练复盘分析。",
      targetUser: "羽毛球教练、运动员，以及负责训练复盘的视频分析人员。",
      title: "羽毛球轨迹与动作识别",
    },
    erasure: {
      dataAssets: "可能有企业试卷扫描样本；公开成对数据集暂不确定。",
      demandEvidenceSources: "待核验的教培企业试卷复用需求记录；如可获取，检查已填写/干净试卷样本。",
      direction: "擦除扫描试卷中的手写答案，并恢复成干净试卷，便于再次使用。",
      expectedOutput: "需求验证简报、相关工作地图、候选改进 idea 和实验计划。",
      knownWork: "文档修复、场景文本移除、OCR 引导 mask、扩散/修复类 baseline。",
      metric: "印刷内容保留、OCR 恢复准确率、人工偏好；如果有成对干净试卷再评估 PSNR/SSIM。",
      outputLanguage: "both",
      painPoint: "现有 inpainting 可能破坏印刷文字、表格边框和试卷细线。",
      scenario: "教培企业想复用已填写试卷，需要擦除学生手写内容。",
      target: "输入：已填写的扫描试卷。输出：保留印刷内容的干净试卷。",
      targetUser: "教培企业、老师，以及需要复用干净试卷的内容生产团队。",
      title: "面向试卷复用的手写文本擦除",
    },
  },
} as const;

const labelsByLanguage: Record<"zh" | "en", IntakeLabels> = {
  en: {
    dataAssets: "Data, code, or resources",
    demandEvidenceSources: "Demand evidence sources to verify",
    direction: "Research direction",
    empty: "Not provided",
    expectedOutput: "Expected research output",
    knownWork: "Known papers / methods / baselines",
    metric: "Evaluation metric or success signal",
    note: "Note: Created from structured NoviScope intake. Demand reality and evidence sources should be reviewed before experiment execution.",
    outputLanguage: "Preferred output language",
    outputLanguageValues: {
      both: "Chinese + English",
      en: "English",
      zh: "Chinese",
    },
    painPoint: "Current pain point or suspected gap",
    scenario: "Real-world scenario / demand source",
    target: "Input and desired output",
    targetUser: "Target user or customer",
    title: "# NoviScope Quest Intake",
  },
  zh: {
    dataAssets: "已有数据、代码或资源",
    demandEvidenceSources: "待核验需求证据来源",
    direction: "研究方向",
    empty: "未提供",
    expectedOutput: "期望科研产出",
    knownWork: "已知论文、方法或 baseline",
    metric: "评价指标或成功信号",
    note: "说明：由 NoviScope 结构化采集表创建。进入实验前应先人工复核需求真实性和证据来源。",
    outputLanguage: "期望产出语言",
    outputLanguageValues: {
      both: "中文 + 英文",
      en: "英文",
      zh: "中文",
    },
    painPoint: "当前痛点或可能 gap",
    scenario: "真实应用场景或需求来源",
    target: "输入与期望输出",
    targetUser: "目标用户或客户",
    title: "# NoviScope Quest 采集表",
  },
};

function lineValue(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .join("; ");
}

function optionalLine(label: string, value: string, emptyLabel: string) {
  const trimmedValue = lineValue(value);
  return trimmedValue ? `- ${label}: ${trimmedValue}` : `- ${label}: ${emptyLabel}`;
}

export function isOutputLanguage(value: string): value is OutputLanguage {
  return value === "both" || value === "zh" || value === "en";
}

export function buildInitialDirection(formState: QuestIntakeState, language: "zh" | "en") {
  const labels = labelsByLanguage[language];

  return [
    labels.title,
    optionalLine(labels.direction, formState.direction, labels.empty),
    optionalLine(labels.scenario, formState.scenario, labels.empty),
    optionalLine(labels.demandEvidenceSources, formState.demandEvidenceSources, labels.empty),
    optionalLine(labels.targetUser, formState.targetUser, labels.empty),
    optionalLine(labels.target, formState.target, labels.empty),
    optionalLine(labels.painPoint, formState.painPoint, labels.empty),
    optionalLine(labels.knownWork, formState.knownWork, labels.empty),
    optionalLine(labels.dataAssets, formState.dataAssets, labels.empty),
    optionalLine(labels.metric, formState.metric, labels.empty),
    optionalLine(labels.expectedOutput, formState.expectedOutput, labels.empty),
    optionalLine(labels.outputLanguage, labels.outputLanguageValues[formState.outputLanguage], labels.empty),
    "",
    labels.note,
  ].join("\n");
}
