from app_util.log_util import mask_email, redact


def test_mask_email_keeps_first_letter_and_domain():
    assert mask_email("person@example.com") == "p***@example.com"
    assert mask_email("") == ""


def test_redact_masks_emails_and_secret_values_in_client_text():
    text = 'Email "a.b@x.io" bad | someday:?code=abc-123&state=1 #access_token=eyJ.x.y&refresh_token=r1 nonce=n0'
    out = redact(text)
    assert "a.b@x.io" not in out and "a***@x.io" in out
    for secret in ("abc-123", "eyJ.x.y", "r1", "n0"):
        assert secret not in out
    assert "state=1" in out


def test_redact_keeps_error_codes_readable():
    assert redact("error=access_denied&error_code=otp_expired") == "error=access_denied&error_code=otp_expired"
