import json

from noviscope.agents.paper_meeting_writer import NO_RESULTS_NOTICE


def model_output_without_result_guardrails() -> str:
    return json.dumps(
        {
            "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 实验结果\n- 待整理。",
            "confidence": "high",
            "english_research_brief_markdown": "# Research Brief\n\n## Results\n- TBD.",
            "experiment_results_not_available": [NO_RESULTS_NOTICE],
            "human_review_required": [],
            "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nTBD.",
            "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
            "model_generated_hypotheses": ["Temporal consistency may improve action labels."],
            "summary": "Generated draft artifacts.",
            "verified_facts": [],
            "warnings": [],
        }
    )


def model_output_with_hallucinated_verified_result() -> str:
    return json.dumps(
        {
            "chinese_research_brief_markdown": "# 中文研究 Brief\n\n## 实验结果\n- 已完成。",
            "confidence": "high",
            "english_research_brief_markdown": "# Research Brief\n\n## Results\n- Done.",
            "experiment_results_not_available": [],
            "human_review_required": [],
            "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton\n\n## Results\nDone.",
            "meeting_outline_markdown": "# Group Meeting Outline\n\n1. Motivation",
            "model_generated_hypotheses": [],
            "summary": "Generated draft artifacts.",
            "verified_facts": [
                "The demand scenario is coach feedback.",
                "Verified experiment result: accuracy = 99% on private data.",
            ],
            "warnings": [],
        }
    )


def model_output_with_untrusted_result_sentinel() -> str:
    sentinel = "UNTRUSTED_RESULT_99_7_F1"
    return json.dumps(
        {
            "chinese_research_brief_markdown": f"# 中文研究 Brief\n\n{sentinel}",
            "confidence": "high",
            "english_research_brief_markdown": f"# Research Brief\n\n{sentinel}",
            "experiment_results_not_available": [],
            "human_review_required": [],
            "ieee_paper_skeleton_markdown": f"# IEEE Paper Skeleton\n\n{sentinel}",
            "meeting_outline_markdown": f"# Group Meeting Outline\n\n{sentinel}",
            "model_generated_hypotheses": [],
            "summary": "Generated draft artifacts.",
            "verified_facts": [sentinel],
            "warnings": [],
        }
    )
