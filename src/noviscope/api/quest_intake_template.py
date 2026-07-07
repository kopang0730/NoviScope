from typing import Final

from fastapi import APIRouter

from noviscope.api.quest_intake_examples import QUEST_INTAKE_EXAMPLES
from noviscope.api.quest_intake_template_models import (
    LocalizedTextResponse,
    QuestIntakeFieldResponse,
    QuestIntakeOptionResponse,
    QuestIntakeTemplateResponse,
)

router = APIRouter()


FIELDS: Final[tuple[QuestIntakeFieldResponse, ...]] = (
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en="Badminton shuttle trajectory and action recognition",
            zh="羽毛球轨迹与动作识别",
        ),
        helper=LocalizedTextResponse(
            en="Use one focused task, not a broad field name.",
            zh="写一个聚焦任务，不要只写很宽泛的大方向。",
        ),
        input_kind="short_text",
        key="research_direction",
        label=LocalizedTextResponse(en="Research direction", zh="研究方向"),
        maps_to=("title", "initial_direction"),
        placeholder=LocalizedTextResponse(
            en="e.g. Handwritten text erasure for filled exam sheets",
            zh="例如：已填写试卷中的手写文本擦除",
        ),
        prompt=LocalizedTextResponse(
            en="What research direction or task should NoviScope explore?",
            zh="希望 NoviScope 探索什么科研方向或任务？",
        ),
        required=True,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en="Training venues need objective feedback from match or drill videos.",
            zh="体育训练场景需要从训练或比赛视频中得到客观反馈。",
        ),
        helper=LocalizedTextResponse(
            en="Prefer a real user, customer, workflow, or deployment context.",
            zh="优先写真实用户、客户、业务流程或部署场景。",
        ),
        input_kind="long_text",
        key="real_world_scenario",
        label=LocalizedTextResponse(en="Real-world scenario", zh="真实应用场景"),
        maps_to=("initial_direction",),
        placeholder=LocalizedTextResponse(
            en="Who needs it, where it appears, and why it matters.",
            zh="谁需要、出现在哪里、为什么有价值。",
        ),
        prompt=LocalizedTextResponse(
            en="What concrete real-world demand makes this topic worth studying?",
            zh="这个题目背后有什么具体真实需求？",
        ),
        required=True,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en="Badminton coaches, training institutions, and athletes.",
            zh="羽毛球教练、训练机构和运动员。",
        ),
        helper=LocalizedTextResponse(
            en="This helps the demand validator avoid self-invented needs.",
            zh="这能帮助需求验证阶段避免自嗨式伪需求。",
        ),
        input_kind="short_text",
        key="target_user_or_customer",
        label=LocalizedTextResponse(en="Target user or customer", zh="目标用户或客户"),
        maps_to=("initial_direction",),
        placeholder=LocalizedTextResponse(
            en="e.g. education hardware vendors, coaches, annotators",
            zh="例如：教培硬件厂商、教练、标注人员",
        ),
        prompt=LocalizedTextResponse(
            en="Who would benefit from this research outcome?",
            zh="谁会从这个科研结果中获益？",
        ),
        required=True,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en="Input: monocular training video. Output: shuttle trajectory and action labels.",
            zh="输入：单目训练视频。输出：球轨迹和动作标签。",
        ),
        helper=LocalizedTextResponse(
            en="Clear I/O makes literature search and metrics less ambiguous.",
            zh="明确输入输出能减少文献检索和指标设计的歧义。",
        ),
        input_kind="long_text",
        key="inputs_and_outputs",
        label=LocalizedTextResponse(en="Inputs and expected outputs", zh="输入与期望输出"),
        maps_to=("initial_direction",),
        placeholder=LocalizedTextResponse(
            en="Input data, output prediction, and downstream use.",
            zh="输入数据、输出预测结果以及下游用途。",
        ),
        prompt=LocalizedTextResponse(
            en="What should the system receive and produce?",
            zh="系统应该接收什么，并产出什么？",
        ),
        required=True,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en="Possible training videos exist, but labels are not confirmed.",
            zh="可能有训练视频，但标签情况还不确定。",
        ),
        helper=LocalizedTextResponse(
            en="Use unknown when data access still needs manual confirmation.",
            zh="如果数据访问还没确认，就如实写未知。",
        ),
        input_kind="long_text",
        key="existing_data",
        label=LocalizedTextResponse(en="Existing data", zh="已有数据"),
        maps_to=("initial_direction",),
        placeholder=LocalizedTextResponse(
            en="Dataset name, local path, source, or unknown.",
            zh="数据集名称、本地路径、来源，或写未知。",
        ),
        prompt=LocalizedTextResponse(
            en="What data is already available or likely obtainable?",
            zh="目前已有或可能获得什么数据？",
        ),
        required=False,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en="Pose estimation, shuttle detection/tracking, temporal action recognition.",
            zh="姿态估计、羽毛球检测/跟踪、时序动作识别。",
        ),
        helper=LocalizedTextResponse(
            en="Known baselines anchor novelty claims to existing work.",
            zh="已知 baseline 能把创新点约束在现有工作的基础上。",
        ),
        input_kind="long_text",
        key="known_baselines",
        label=LocalizedTextResponse(en="Known baselines", zh="已知 baseline"),
        maps_to=("initial_direction",),
        placeholder=LocalizedTextResponse(
            en="Papers, methods, repositories, or 'unknown'.",
            zh="论文、方法、代码仓库，或写未知。",
        ),
        prompt=LocalizedTextResponse(
            en="Which papers, methods, or repositories should be treated as baselines?",
            zh="有哪些论文、方法或代码仓库可以作为 baseline？",
        ),
        required=False,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(
            en=(
                "Trajectory localization error, action classification accuracy, "
                "temporal consistency."
            ),
            zh="轨迹定位误差、动作分类准确率、时序一致性。",
        ),
        helper=LocalizedTextResponse(
            en="Metrics help separate real experimental validation from narrative claims.",
            zh="指标能区分真实实验验证和单纯文字论证。",
        ),
        input_kind="long_text",
        key="evaluation_metrics",
        label=LocalizedTextResponse(en="Evaluation metrics", zh="评价指标"),
        maps_to=("initial_direction",),
        placeholder=LocalizedTextResponse(
            en="Accuracy, F1, mIoU, edit distance, user feedback, etc.",
            zh="Accuracy、F1、mIoU、编辑距离、用户反馈等。",
        ),
        prompt=LocalizedTextResponse(
            en="How should success be measured?",
            zh="应该如何衡量这个方向是否成功？",
        ),
        required=False,
    ),
    QuestIntakeFieldResponse(
        example=LocalizedTextResponse(en="Chinese and English", zh="中文和英文"),
        helper=LocalizedTextResponse(
            en="This controls draft and report language expectations.",
            zh="这会影响论文草稿和汇报材料的语言预期。",
        ),
        input_kind="single_select",
        key="expected_languages",
        label=LocalizedTextResponse(en="Expected output language", zh="期望产出语言"),
        maps_to=("initial_direction",),
        options=(
            QuestIntakeOptionResponse(
                label=LocalizedTextResponse(en="Chinese", zh="中文"),
                value="zh",
            ),
            QuestIntakeOptionResponse(
                label=LocalizedTextResponse(en="English", zh="英文"),
                value="en",
            ),
            QuestIntakeOptionResponse(
                label=LocalizedTextResponse(en="Chinese and English", zh="中文和英文"),
                value="zh_en",
            ),
        ),
        placeholder=LocalizedTextResponse(en="Chinese and English", zh="中文和英文"),
        prompt=LocalizedTextResponse(
            en="Which language should generated academic artifacts use?",
            zh="生成的学术内容应该使用什么语言？",
        ),
        required=False,
    ),
)

@router.get("/quest-intake/template", response_model=QuestIntakeTemplateResponse)
def get_quest_intake_template() -> QuestIntakeTemplateResponse:
    return QuestIntakeTemplateResponse(
        examples=QUEST_INTAKE_EXAMPLES,
        fields=FIELDS,
        initial_direction_field_order=tuple(field.key for field in FIELDS),
        supported_languages=("zh", "en"),
        title_field_key="research_direction",
        version="2026-07-quest-intake-v1",
    )
