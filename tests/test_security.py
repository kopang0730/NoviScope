from noviscope.core.security import OutboundDataClass, assert_external_upload_allowed, redact_secret


def test_redact_secret_keeps_short_marker():
    assert redact_secret("sk-1234567890abcdef") == "sk-...def"


def test_redact_secret_handles_short_values():
    assert redact_secret("abc") == "***"


def test_redact_secret_masks_eight_character_values():
    assert redact_secret("12345678") == "***"


def test_redact_secret_limits_visible_characters_for_nine_character_values():
    assert redact_secret("123456789") == "123...789"


def test_public_upload_allowed_without_consent():
    assert_external_upload_allowed(OutboundDataClass.PUBLIC_METADATA, user_approved=False)


def test_private_dataset_upload_requires_consent():
    try:
        assert_external_upload_allowed(OutboundDataClass.PRIVATE_DATASET, user_approved=False)
    except PermissionError as exc:
        assert "PRIVATE_DATASET requires explicit user approval" in str(exc)
    else:
        raise AssertionError("private dataset upload should require approval")
