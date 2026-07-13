"""Tests for email outreach verification and settings."""

import pytest

from app.services.email_outreach.verification import (
    can_send_to_email,
    verify_outreach_email,
)


def test_verify_invalid_syntax():
    result = verify_outreach_email("not-an-email")
    assert result.is_valid is False
    assert result.is_verified is False
    assert can_send_to_email(result) is False


def test_verify_disposable_email():
    result = verify_outreach_email("test@mailinator.com")
    assert result.is_disposable is True
    assert can_send_to_email(result) is False


def test_verify_missing_email():
    result = verify_outreach_email(None)
    assert result.is_valid is False
    assert "missing_email" in result.reasons


def test_verify_valid_format():
    result = verify_outreach_email("contact@business.co.uk", "https://business.co.uk")
    assert result.syntax_valid is True
    assert result.domain_valid is True
