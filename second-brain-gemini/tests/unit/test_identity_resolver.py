"""
Unit tests for IdentityResolverService — pronoun resolution & context tracking.
"""
import pytest
from app.services.identity_resolver_service import IdentityResolverService

PHONE = "972501234567"


class TestIdentityResolverService:
    """Test pronoun detection and entity tracking."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.resolver = IdentityResolverService()

    def _make_entity(self, name: str) -> dict:
        return {"canonical_name": name, "title": "Employee"}

    # ── Pronoun detection ────────────────────────────────────────

    def test_has_pronouns_basic_hebrew(self):
        """Should detect basic Hebrew pronouns."""
        assert self.resolver.has_pronouns("מה הביצועים שלו?")
        assert self.resolver.has_pronouns("ספר לי על שלה")
        assert self.resolver.has_pronouns("מי מדווח אליו?")

    def test_has_pronouns_extended(self):
        """Should detect extended pronoun forms."""
        for pronoun_phrase in ["אליו", "אליה", "איתו", "איתה", "בו", "בה",
                               "אצלו", "אצלה", "ידו", "ידה", "ממנו", "ממנה"]:
            assert self.resolver.has_pronouns(f"מה קורה {pronoun_phrase}?"), \
                f"Should detect pronoun: {pronoun_phrase}"

    def test_no_pronouns(self):
        """Should not flag messages without pronouns."""
        assert not self.resolver.has_pronouns("מי זה יובל?")
        assert not self.resolver.has_pronouns("שלום, מה שלומך?")
        assert not self.resolver.has_pronouns("חפש טיסות לפריז")

    # ── Entity tracking ──────────────────────────────────────────

    def test_update_context_stores_entity(self):
        """Should store the last mentioned entity."""
        self.resolver.update_context(PHONE, entity=self._make_entity("Yuval Laikin"))
        entity = self.resolver.get_last_entity(PHONE)
        assert entity is not None
        assert entity["canonical_name"] == "Yuval Laikin"

    def test_update_context_overwrites(self):
        """Should overwrite previous entity."""
        self.resolver.update_context(PHONE, entity=self._make_entity("Yuval Laikin"))
        self.resolver.update_context(PHONE, entity=self._make_entity("Chen Katz"))
        entity = self.resolver.get_last_entity(PHONE)
        assert entity["canonical_name"] == "Chen Katz"

    def test_no_entity_initially(self):
        """Should return None when no entity has been stored."""
        assert self.resolver.get_last_entity(PHONE) is None

    # ── Digit selection ──────────────────────────────────────────

    def test_is_digit_selection(self):
        """Should recognize single-digit messages as selections."""
        assert self.resolver.is_digit_selection("1")
        assert self.resolver.is_digit_selection("3")
        assert self.resolver.is_digit_selection("9")

    def test_is_not_digit_selection(self):
        """Should not flag non-digit messages."""
        assert not self.resolver.is_digit_selection("hello")
        assert not self.resolver.is_digit_selection("10")
        assert not self.resolver.is_digit_selection("")
        assert not self.resolver.is_digit_selection("1 2")
