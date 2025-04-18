import pytest

from web.models import Profile


def test_default_preferred_role_is_both():
    profile = Profile()
    # By default, no explicit role is set, so preferred_role should be "both"
    assert profile.preferred_role == "both"


def test_preferred_role_can_be_set_and_updated():
    profile = Profile(preferred_role="teacher")
    assert profile.preferred_role == "teacher"

    profile.preferred_role = "student"
    assert profile.preferred_role == "student"

    profile.preferred_role = "both"
    assert profile.preferred_role == "both"


@pytest.mark.parametrize(
    "account_id,status,expected",
    [
        ("acct_123", "verified", True),
        ("acct_456", "pending", False),
        ("acct_789", "disabled", False),
        (None, "verified", False),
        ("acct_000", None, False),
    ],
)
def test_can_receive_payments_various_states(account_id, status, expected):
    profile = Profile()
    profile.stripe_account_id = account_id
    profile.stripe_account_status = status
    assert profile.can_receive_payments is expected
