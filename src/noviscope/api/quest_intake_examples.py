from typing import Final

from noviscope.api.quest_intake_template_models import (
    LocalizedTextResponse,
    QuestIntakeExampleResponse,
)

QUEST_INTAKE_EXAMPLES: Final[tuple[QuestIntakeExampleResponse, ...]] = (
    QuestIntakeExampleResponse(
        initial_direction=LocalizedTextResponse(
            en=(
                "Research direction: badminton shuttle trajectory and action recognition.\n"
                "Scenario: coaches need objective training feedback from match or drill videos.\n"
                "Input/output: input monocular videos; output shuttle trajectories, action labels, "
                "and training review signals.\n"
                "Known baselines: pose estimation, shuttle tracking, temporal action recognition."
            ),
            zh=(
                "研究方向：羽毛球轨迹与动作识别。\n"
                "真实场景：教练希望从训练或比赛视频中获得客观反馈。\n"
                "输入输出：输入单目视频；输出球轨迹、动作标签和训练复盘信号。\n"
                "已知 baseline：姿态估计、羽毛球跟踪、时序动作识别。"
            ),
        ),
        key="badminton_action_recognition",
        title=LocalizedTextResponse(
            en="Badminton trajectory and action recognition",
            zh="羽毛球轨迹与动作识别",
        ),
    ),
    QuestIntakeExampleResponse(
        initial_direction=LocalizedTextResponse(
            en=(
                "Research direction: handwritten text erasure for filled exam sheets.\n"
                "Scenario: education hardware vendors need to restore a clean exam sheet "
                "from scanned or photographed student-filled pages.\n"
                "Input/output: input used exam-sheet images; output clean reusable sheet images.\n"
                "Metrics: text removal quality, printed-content preservation, OCR consistency."
            ),
            zh=(
                "研究方向：已填写试卷中的手写文本擦除。\n"
                "真实场景：教培硬件厂商需要把学生填写过的试卷还原成干净试卷。\n"
                "输入输出：输入已填写试卷图像；输出可复用的干净试卷图像。\n"
                "评价指标：手写内容去除质量、印刷内容保真度、OCR 一致性。"
            ),
        ),
        key="handwritten_text_erasure",
        title=LocalizedTextResponse(
            en="Handwritten text erasure for exam sheets",
            zh="试卷手写文本擦除",
        ),
    ),
)
