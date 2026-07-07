import json

from noviscope.agents.paper_meeting_contracts import PaperMeetingWriterRequest
from noviscope.agents.paper_meeting_payloads import (
    MAX_PAPERS_FOR_PROMPT,
    compact_payload,
)
from noviscope.agents.provider_chat import ChatCompletionPayload


def build_chat_completion_payload(request: PaperMeetingWriterRequest) -> ChatCompletionPayload:
    prompt_payload = {
        "demand_validation": compact_payload(request.demand_validation),
        "experiment_plan": compact_payload(request.experiment_plan),
        "papers": request.papers[:MAX_PAPERS_FOR_PROMPT],
        "quest": {
            "initial_direction": request.initial_direction,
            "title": request.quest_title,
        },
        "selected_ideas": request.selected_ideas,
        "source_stage_ids": request.source_stage_ids,
    }
    return {
        "messages": [
            {
                "content": (
                    "You are NoviScope's Paper & Meeting Writer. Return only valid JSON with "
                    "keys summary, confidence, chinese_research_brief_markdown, "
                    "english_research_brief_markdown, meeting_outline_markdown, "
                    "ieee_paper_skeleton_markdown, verified_facts, "
                    "model_generated_hypotheses, experiment_results_not_available, "
                    "human_review_required, warnings. Use Markdown strings for the four "
                    "artifacts. Clearly separate verified facts from generated hypotheses. "
                    "Do not invent citations, metric values, benchmark scores, or completed "
                    "experiments. The IEEE skeleton must keep Results and Conclusion sections "
                    "as placeholders because experiments have not run. Every claim that needs "
                    "review must appear in human_review_required."
                ),
                "role": "system",
            },
            {
                "content": json.dumps(prompt_payload, ensure_ascii=False),
                "role": "user",
            },
        ],
        "model": request.model,
        "temperature": 0.25,
    }
