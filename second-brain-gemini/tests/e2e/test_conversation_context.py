"""
E2E tests for conversation context preservation.

Tests the critical flow:
1. User asks about a person ("מי זה יובל?")
2. User asks follow-up without mentioning the name ("מי מדווח אליו?")
3. System should connect the follow-up to "יובל"

Also tests:
- Entity context injection into messages
- Last mentioned entity tracking across turns
"""
import pytest
from app.services.identity_resolver_service import IdentityResolverService

PHONE = "972501234567"


class TestConversationContextPreservation:
    """Test that the system maintains conversation context across turns."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.resolver = IdentityResolverService()

    def _make_entity(self, name: str, role: str = "Employee") -> dict:
        return {"canonical_name": name, "title": role, "department": "Engineering"}

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

    def test_entity_persists_across_turns(self):
        """After mentioning 'Yuval', follow-up should reference Yuval."""
        # Turn 1: System answers about Yuval → stores entity
        self.resolver.update_context(PHONE, entity=self._make_entity("Yuval Laikin"))

        # Turn 2: User asks follow-up with pronoun
        last_entity = self.resolver.get_last_entity(PHONE)
        assert last_entity is not None
        assert last_entity["canonical_name"] == "Yuval Laikin"

    def test_context_switches_on_new_entity(self):
        """When user asks about a new person, context should switch."""
        self.resolver.update_context(PHONE, entity=self._make_entity("Yuval Laikin"))
        assert self.resolver.get_last_entity(PHONE)["canonical_name"] == "Yuval Laikin"

        self.resolver.update_context(PHONE, entity=self._make_entity("Chen Katz"))
        assert self.resolver.get_last_entity(PHONE)["canonical_name"] == "Chen Katz"

    def test_different_phones_have_separate_contexts(self):
        """Each phone number should have its own session context."""
        phone_a = "972501111111"
        phone_b = "972502222222"

        self.resolver.update_context(phone_a, entity=self._make_entity("Yuval"))
        self.resolver.update_context(phone_b, entity=self._make_entity("Chen"))

        assert self.resolver.get_last_entity(phone_a)["canonical_name"] == "Yuval"
        assert self.resolver.get_last_entity(phone_b)["canonical_name"] == "Chen"

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


class TestMultiTurnScenarios:
    """Test realistic multi-turn conversation scenarios."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.resolver = IdentityResolverService()

    def _make_entity(self, name: str) -> dict:
        return {"canonical_name": name, "title": "Employee"}

    def test_scenario_person_then_reports(self):
        """
        Scenario: Ask about Yuval → Ask who reports to him
        Expected: System understands "him" = Yuval
        """
        # Turn 1: System responds about Yuval
        self.resolver.update_context(PHONE, entity=self._make_entity("Yuval Laikin"))

        # Turn 2: User asks follow-up
        msg = "מי מדווח אליו?"
        assert self.resolver.has_pronouns(msg)
        entity = self.resolver.get_last_entity(PHONE)
        assert entity["canonical_name"] == "Yuval Laikin"

    def test_scenario_switch_context_then_follow_up(self):
        """
        Scenario: Ask about Yuval → Ask about Chen → Ask follow-up
        Expected: Follow-up refers to Chen (last mentioned)
        """
        self.resolver.update_context(PHONE, entity=self._make_entity("Yuval Laikin"))
        self.resolver.update_context(PHONE, entity=self._make_entity("Chen Katz"))

        msg = "מה הביצועים שלו?"
        assert self.resolver.has_pronouns(msg)
        entity = self.resolver.get_last_entity(PHONE)
        assert entity["canonical_name"] == "Chen Katz"

    def test_scenario_no_context_pronoun(self):
        """
        Scenario: User sends pronoun without prior context
        Expected: System detects pronoun but has no entity to reference
        """
        msg = "מי מדווח אליו?"
        assert self.resolver.has_pronouns(msg)
        assert self.resolver.get_last_entity(PHONE) is None

    def test_pronoun_in_follow_up_detected(self):
        """Various Hebrew follow-up patterns should be detected as pronouns."""
        follow_ups = [
            "מי מדווח אליו?",
            "מה הביצועים שלו?",
            "ספר לי עליה",
            "מי עובד איתו?",
            "כמה אנשים יש בצוות שלו?",
            "מה התפקיד שלה?",
        ]
        for msg in follow_ups:
            assert self.resolver.has_pronouns(msg), \
                f"Should detect pronouns in: '{msg}'"

    def test_direct_questions_not_pronoun(self):
        """Direct questions should NOT be flagged as pronouns."""
        direct_questions = [
            "מי זה יובל?",
            "ספר לי על חן כץ",
            "מה התפקיד של נועם?",
            "חפש טיסות לפריז",
        ]
        for msg in direct_questions:
            assert not self.resolver.has_pronouns(msg), \
                f"Should NOT detect pronouns in: '{msg}'"
