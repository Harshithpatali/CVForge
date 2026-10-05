from app.services.llm import RESUME_JSON_SCHEMA


def test_resume_schema_requires_all_top_level_fields():
    assert RESUME_JSON_SCHEMA["additionalProperties"] is False
    assert set(RESUME_JSON_SCHEMA["required"]) == set(
        RESUME_JSON_SCHEMA["properties"]
    )


def test_resume_schema_uses_string_content_contract():
    assert RESUME_JSON_SCHEMA["properties"]["name"]["type"] == "string"
    assert RESUME_JSON_SCHEMA["properties"]["contact_line"]["type"] == "string"
