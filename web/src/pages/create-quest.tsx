import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createQuest } from "../api/quests";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/button";
import { Card, CardHeading } from "../components/card";
import { Input, Select, TextArea } from "../components/input";
import { useI18n } from "../i18n/i18n-context";

type OutputLanguage = "zh" | "en" | "both";

type QuestIntakeState = {
  dataAssets: string;
  direction: string;
  expectedOutput: string;
  knownWork: string;
  metric: string;
  outputLanguage: OutputLanguage;
  painPoint: string;
  scenario: string;
  target: string;
  title: string;
};

const emptyIntake: QuestIntakeState = {
  dataAssets: "",
  direction: "",
  expectedOutput: "",
  knownWork: "",
  metric: "",
  outputLanguage: "both",
  painPoint: "",
  scenario: "",
  target: "",
  title: "",
};

const examples: Record<"zh" | "en", Record<"erasure" | "badminton", QuestIntakeState>> = {
  en: {
    badminton: {
      dataAssets: "Court videos from training sessions; annotation plan is not fixed yet.",
      direction: "Use computer vision to recognize badminton shuttle trajectory or player actions from match/training videos.",
      expectedOutput: "Validate whether the task has enough value, list datasets/baselines, and propose the first feasible experiment.",
      knownWork: "Sports pose estimation, shuttle tracking, action recognition, temporal modeling.",
      metric: "Trajectory localization error, action classification accuracy, frame-level consistency, and coach usability feedback.",
      outputLanguage: "both",
      painPoint: "Fast shuttle motion, occlusion, motion blur, and limited annotated badminton-specific data.",
      scenario: "AI + sports training: coaches want objective feedback on shuttle trajectory and athlete actions.",
      target: "Input: badminton video. Output: shuttle trajectory, action labels, and structured analysis for training review.",
      title: "Badminton trajectory and action recognition",
    },
    erasure: {
      dataAssets: "Enterprise exam-sheet scans may be available; public paired data is uncertain.",
      direction: "Erase handwritten answers from scanned exam sheets and recover a clean worksheet for reuse.",
      expectedOutput: "Demand validation brief, related-work map, candidate improvement idea, and experiment plan.",
      knownWork: "Document inpainting, scene text removal, OCR-guided masks, diffusion/inpainting baselines.",
      metric: "Printed-content preservation, OCR recovery, human preference, and PSNR/SSIM if paired clean sheets exist.",
      outputLanguage: "both",
      painPoint: "Existing inpainting may damage printed text, table borders, and thin worksheet lines.",
      scenario: "Education company reuses completed exam sheets and needs to remove students' handwriting.",
      target: "Input: filled scanned worksheet. Output: clean worksheet with printed content preserved.",
      title: "Handwritten text erasure for reusable exam sheets",
    },
  },
  zh: {
    badminton: {
      dataAssets: "训练或比赛视频可能可采集；标注方案暂未固定。",
      direction: "使用机器视觉识别羽毛球轨迹或运动员动作，用于训练复盘和动作分析。",
      expectedOutput: "验证任务价值，梳理数据集和 baseline，并提出第一步可行实验。",
      knownWork: "体育姿态估计、羽毛球检测/跟踪、动作识别、时序建模。",
      metric: "轨迹定位误差、动作分类准确率、帧间一致性，以及教练使用反馈。",
      outputLanguage: "both",
      painPoint: "羽毛球速度快、遮挡多、运动模糊明显，并且专门标注数据有限。",
      scenario: "AI + 体育训练场景：教练希望获得客观的羽毛球轨迹和动作反馈。",
      target: "输入：羽毛球训练或比赛视频。输出：球轨迹、动作标签和训练复盘分析。",
      title: "羽毛球轨迹与动作识别",
    },
    erasure: {
      dataAssets: "可能有企业试卷扫描样本；公开成对数据集暂不确定。",
      direction: "擦除扫描试卷中的手写答案，并恢复成干净试卷，便于再次使用。",
      expectedOutput: "需求验证简报、相关工作地图、候选改进 idea 和实验计划。",
      knownWork: "文档修复、场景文本移除、OCR 引导 mask、扩散/修复类 baseline。",
      metric: "印刷内容保留、OCR 恢复准确率、人工偏好；如果有成对干净试卷再评估 PSNR/SSIM。",
      outputLanguage: "both",
      painPoint: "现有 inpainting 可能破坏印刷文字、表格边框和试卷细线。",
      scenario: "教培企业想复用已填写试卷，需要擦除学生手写内容。",
      target: "输入：已填写的扫描试卷。输出：保留印刷内容的干净试卷。",
      title: "面向试卷复用的手写文本擦除",
    },
  },
};

function optionalLine(label: string, value: string, emptyLabel: string) {
  const trimmedValue = value.trim();
  return trimmedValue ? `- ${label}: ${trimmedValue}` : `- ${label}: ${emptyLabel}`;
}

function buildInitialDirection(formState: QuestIntakeState, language: "zh" | "en") {
  const labels =
    language === "zh"
      ? {
          dataAssets: "已有数据、代码或资源",
          direction: "研究方向",
          empty: "未提供",
          expectedOutput: "期望科研产出",
          knownWork: "已知论文、方法或 baseline",
          metric: "评价指标或成功信号",
          note: "说明：由 NoviScope 结构化采集表创建。进入实验前应先人工复核需求真实性。",
          outputLanguage: "期望产出语言",
          outputLanguageValues: {
            both: "中文 + 英文",
            en: "英文",
            zh: "中文",
          },
          painPoint: "当前痛点或可能 gap",
          scenario: "真实应用场景或需求来源",
          target: "输入与期望输出",
          title: "# NoviScope Quest 采集表",
        }
      : {
          dataAssets: "Data, code, or resources",
          direction: "Research direction",
          empty: "Not provided",
          expectedOutput: "Expected research output",
          knownWork: "Known papers / methods / baselines",
          metric: "Evaluation metric or success signal",
          note: "Note: Created from structured NoviScope intake. Demand reality should be reviewed before experiment execution.",
          outputLanguage: "Preferred output language",
          outputLanguageValues: {
            both: "Chinese + English",
            en: "English",
            zh: "Chinese",
          },
          painPoint: "Current pain point or suspected gap",
          scenario: "Real-world scenario / demand source",
          target: "Input and desired output",
          title: "# NoviScope Quest Intake",
        };

  return [
    labels.title,
    optionalLine(labels.direction, formState.direction, labels.empty),
    optionalLine(labels.scenario, formState.scenario, labels.empty),
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

export function CreateQuestPage() {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const { language, t } = useI18n();
  const [formState, setFormState] = useState<QuestIntakeState>(emptyIntake);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const preview = useMemo(() => buildInitialDirection(formState, language), [formState, language]);

  function updateField<Key extends keyof QuestIntakeState>(key: Key, value: QuestIntakeState[Key]) {
    setFormState((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const quest = await createQuest({
        initial_direction: preview,
        title: formState.title,
      });
      navigate(`/?quest=${quest.id}`, { replace: true });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <Card>
        <CardHeading description={t("questFormDescription")} title={t("navNewQuest")} />
        {!currentUser ? (
          <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {t("signInFirstQuest")}
          </p>
        ) : null}

        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => setFormState(examples[language].erasure)} size="sm" type="button" variant="secondary">
            {t("questExampleErasure")}
          </Button>
          <Button onClick={() => setFormState(examples[language].badminton)} size="sm" type="button" variant="secondary">
            {t("questExampleBadminton")}
          </Button>
        </div>

        <form className="mt-6 space-y-6" onSubmit={(event) => void handleSubmit(event)}>
          <section className="grid gap-4 lg:grid-cols-2">
            <Input
              label={t("questTitle")}
              onChange={(event) => updateField("title", event.target.value)}
              placeholder={t("questTitlePlaceholder")}
              required
              value={formState.title}
            />
            <Select
              label={t("questOutputLanguage")}
              onChange={(event) => updateField("outputLanguage", event.target.value as OutputLanguage)}
              value={formState.outputLanguage}
            >
              <option value="both">{t("questOutputLanguageBoth")}</option>
              <option value="zh">{t("questOutputLanguageZh")}</option>
              <option value="en">{t("questOutputLanguageEn")}</option>
            </Select>
            <TextArea
              hint={t("questDirectionHint")}
              label={t("questDirection")}
              onChange={(event) => updateField("direction", event.target.value)}
              placeholder={t("questDirectionPlaceholder")}
              required
              rows={5}
              value={formState.direction}
            />
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{t("questRealitySection")}</h3>
              <p className="mt-1 text-sm text-slate-600">{t("questRealitySectionDescription")}</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <TextArea
                hint={t("questScenarioHint")}
                label={t("questScenario")}
                onChange={(event) => updateField("scenario", event.target.value)}
                placeholder={t("questScenarioPlaceholder")}
                rows={4}
                value={formState.scenario}
              />
              <TextArea
                label={t("questTarget")}
                onChange={(event) => updateField("target", event.target.value)}
                placeholder={t("questTargetPlaceholder")}
                rows={4}
                value={formState.target}
              />
              <TextArea
                label={t("questPainPoint")}
                onChange={(event) => updateField("painPoint", event.target.value)}
                placeholder={t("questPainPointPlaceholder")}
                rows={4}
                value={formState.painPoint}
              />
              <TextArea
                hint={t("questKnownWorkHint")}
                label={t("questKnownWork")}
                onChange={(event) => updateField("knownWork", event.target.value)}
                placeholder={t("questKnownWorkPlaceholder")}
                rows={4}
                value={formState.knownWork}
              />
            </div>
          </section>

          <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{t("questExperimentSection")}</h3>
              <p className="mt-1 text-sm text-slate-600">{t("questExperimentSectionDescription")}</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <TextArea
                hint={t("questDataAssetsHint")}
                label={t("questDataAssets")}
                onChange={(event) => updateField("dataAssets", event.target.value)}
                placeholder={t("questDataAssetsPlaceholder")}
                rows={4}
                value={formState.dataAssets}
              />
              <TextArea
                label={t("questMetric")}
                onChange={(event) => updateField("metric", event.target.value)}
                placeholder={t("questMetricPlaceholder")}
                rows={4}
                value={formState.metric}
              />
              <TextArea
                label={t("questExpectedOutput")}
                onChange={(event) => updateField("expectedOutput", event.target.value)}
                placeholder={t("questExpectedOutputPlaceholder")}
                rows={4}
                value={formState.expectedOutput}
              />
            </div>
          </section>

          {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">{t("questSubmitHint")}</p>
            <Button loading={submitting} type="submit">
              {t("questCreate")}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeading description={t("questSubmitHint")} title={t("initialDirectionPreview")} />
        <pre className="mt-4 max-h-[760px] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {preview}
        </pre>
      </Card>
    </div>
  );
}
