from fastapi.testclient import TestClient

from noviscope.main import create_app

EXPECTED_FIELD_KEYS = [
    "research_direction",
    "real_world_scenario",
    "target_user_or_customer",
    "inputs_and_outputs",
    "existing_data",
    "known_baselines",
    "evaluation_metrics",
    "expected_languages",
]


def test_quest_intake_template_endpoint_exposes_bilingual_research_form_contract(
    tmp_path,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-intake-template.db'}")

    with TestClient(app) as client:
        # Given

        # When
        response = client.get("/quest-intake/template")

    # Then
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "2026-07-quest-intake-v1"
    assert body["supported_languages"] == ["zh", "en"]
    assert body["title_field_key"] == "research_direction"
    assert body["initial_direction_field_order"] == EXPECTED_FIELD_KEYS
    assert [field["key"] for field in body["fields"]] == EXPECTED_FIELD_KEYS
    direction_field = body["fields"][0]
    assert direction_field["required"] is True
    assert direction_field["maps_to"] == ["title", "initial_direction"]
    assert direction_field["label"] == {
        "en": "Research direction",
        "zh": "研究方向",
    }
    language_field = body["fields"][-1]
    assert language_field["input_kind"] == "single_select"
    assert [option["value"] for option in language_field["options"]] == [
        "zh",
        "en",
        "zh_en",
    ]


def test_quest_intake_template_includes_concrete_cv_examples(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'quest-intake-examples.db'}")

    with TestClient(app) as client:
        # Given

        # When
        response = client.get("/quest-intake/template")

    # Then
    assert response.status_code == 200
    body = response.json()
    examples_by_key = {example["key"]: example for example in body["examples"]}
    assert set(examples_by_key) == {
        "badminton_action_recognition",
        "handwritten_text_erasure",
    }
    assert "羽毛球" in examples_by_key["badminton_action_recognition"]["title"]["zh"]
    assert (
        "restore a clean exam sheet"
        in examples_by_key["handwritten_text_erasure"]["initial_direction"]["en"]
    )
