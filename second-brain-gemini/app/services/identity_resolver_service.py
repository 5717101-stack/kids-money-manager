"""
Smart Identity Resolver — Session-Based Disambiguation for KB Queries

Handles name ambiguity with minimal user friction:
1. Short-term context tracking (10-min session per phone number)
2. Contextual scoring (department/manager affinity from recent conversation)
3. Digit-only response handling (quick selection from numbered menus)
4. WhatsApp-optimized Hebrew ambiguity menus
5. Pronoun resolution — "מה השכר שלו?" → "מה השכר של Yuval Laikin?"

Usage (in main.py):
    from app.services.identity_resolver_service import identity_resolver

    # Before KB query — resolve pronouns to the last-mentioned entity
    resolved_msg = identity_resolver.resolve_pronouns(from_number, message_text)

    # Before KB query — check if message is a digit selection
    resolved = identity_resolver.try_resolve_digit(from_number, message_text)
    if resolved:
        # resolved.pending_query contains the original question
        # resolved.person contains the selected person dict

    # After name search returns multiple results — build menu
    menu = identity_resolver.handle_ambiguity(from_number, query, matches, original_question)
"""

import logging
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
SESSION_TTL_SECONDS = 600  # 10 minutes
MAX_SESSIONS = 200         # Cap to prevent unbounded memory growth


# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SessionContext:
    """Short-term memory for a single user (phone number)."""
    last_department_mentioned: str = ""
    last_manager_mentioned: str = ""
    last_mentioned_entity: Optional[Dict[str, Any]] = None  # Full person dict from last KB answer
    last_options_list: List[Dict[str, Any]] = field(default_factory=list)
    pending_query: str = ""            # The original question waiting for disambiguation
    last_activity: float = 0.0         # timestamp of last interaction

    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > SESSION_TTL_SECONDS

    def touch(self):
        self.last_activity = time.time()


@dataclass
class ResolvedSelection:
    """Result of a successful digit selection."""
    person: Dict[str, Any]      # The person dict from the identity graph
    pending_query: str           # The original question to re-execute
    display_name: str            # Formatted name for logs


# ═══════════════════════════════════════════════════════════════════════
# IDENTITY RESOLVER SERVICE
# ═══════════════════════════════════════════════════════════════════════

class IdentityResolverService:
    """
    Manages per-user session context for intelligent name disambiguation.
    Thread-safe via a single lock.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = Lock()

    # ── Session management ──────────────────────────────────────────

    def _get_session(self, phone: str) -> SessionContext:
        """Get or create a session for a phone number. Auto-evicts expired."""
        with self._lock:
            # Evict expired sessions periodically
            if len(self._sessions) > MAX_SESSIONS:
                expired = [k for k, v in self._sessions.items() if v.is_expired()]
                for k in expired:
                    del self._sessions[k]

            session = self._sessions.get(phone)
            if session is None or session.is_expired():
                session = SessionContext(last_activity=time.time())
                self._sessions[phone] = session
            return session

    def update_context(
        self, phone: str, department: str = "", manager: str = "",
        entity: Optional[Dict[str, Any]] = None
    ):
        """
        Update session context after a successful KB answer.
        Call this after every KB response so subsequent queries benefit.
        
        Args:
            entity: Full person dict (canonical_name, title, department, etc.)
                    Stored as last_mentioned_entity for pronoun resolution.
        """
        session = self._get_session(phone)
        session.touch()
        if department:
            session.last_department_mentioned = department
        if manager:
            session.last_manager_mentioned = manager
        if entity:
            session.last_mentioned_entity = entity
            name = entity.get("canonical_name", "?")
            logger.info(f"🧠 [Resolver] Entity stored for {phone}: {name}")
            print(f"🧠 [Resolver] Entity stored for {phone}: {name}")

    def get_last_entity(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get the last-mentioned entity for a phone number (if session is active)."""
        session = self._get_session(phone)
        if session.is_expired() or not session.last_mentioned_entity:
            return None
        return session.last_mentioned_entity

    # ── Pronoun resolution ───────────────────────────────────────────

    # Pronouns in Hebrew and English that refer to a previously mentioned person
    _PRONOUNS_HE = {'שלו', 'שלה', 'הוא', 'היא', 'אותו', 'אותה', 'לו', 'לה', 'ממנו', 'ממנה', 'עליו', 'עליה'}
    _PRONOUNS_EN = {'his', 'her', 'him', 'he', 'she', 'their', 'them', 'hers'}

    @classmethod
    def has_pronouns(cls, message: str) -> bool:
        """Check if the message contains pronouns that need resolution."""
        words = set(re.findall(r'[\w\u0590-\u05FF]+', message.lower()))
        return bool(words & (cls._PRONOUNS_HE | cls._PRONOUNS_EN))

    def resolve_pronouns(self, phone: str, message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        If message contains pronouns and we have a last_mentioned_entity,
        replace the pronoun with the entity's canonical name.
        
        Returns:
            (resolved_message, entity_used) — entity_used is None if no resolution happened.
        
        Examples:
            "מה השכר שלו?"      → ("מה השכר של Yuval Laikin?", {person_dict})
            "What is his rating?" → ("What is Yuval Laikin's rating?", {person_dict})
            "מי המנהל שלו?"     → ("מי המנהל של Yuval Laikin?", {person_dict})
        """
        if not self.has_pronouns(message):
            return message, None

        entity = self.get_last_entity(phone)
        if not entity:
            return message, None

        name = entity.get("canonical_name", "")
        if not name:
            return message, None

        resolved = message
        # ── Hebrew pronoun replacement ──
        # "שלו" / "שלה" → "של {name}"
        resolved = re.sub(r'\bשלו\b', f'של {name}', resolved)
        resolved = re.sub(r'\bשלה\b', f'של {name}', resolved)
        # "הוא" / "היא" at start or after space → name
        resolved = re.sub(r'\bהוא\b', name, resolved)
        resolved = re.sub(r'\bהיא\b', name, resolved)
        # "אותו" / "אותה" → name
        resolved = re.sub(r'\bאותו\b', name, resolved)
        resolved = re.sub(r'\bאותה\b', name, resolved)
        # "לו" / "לה" (careful — only when standalone)
        resolved = re.sub(r'\bממנו\b', f'מ-{name}', resolved)
        resolved = re.sub(r'\bממנה\b', f'מ-{name}', resolved)
        resolved = re.sub(r'\bעליו\b', f'על {name}', resolved)
        resolved = re.sub(r'\bעליה\b', f'על {name}', resolved)

        # ── English pronoun replacement ──
        resolved = re.sub(r'\bhis\b', f"{name}'s", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\bher\b', f"{name}'s", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\bhers\b', f"{name}'s", resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\bhe\b', name, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\bshe\b', name, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\bhim\b', name, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\bthem\b', name, resolved, flags=re.IGNORECASE)
        resolved = re.sub(r'\btheir\b', f"{name}'s", resolved, flags=re.IGNORECASE)

        if resolved != message:
            logger.info(f"🔗 [Resolver] Pronoun resolved: '{message}' → '{resolved}'")
            print(f"🔗 [Resolver] Pronoun resolved: '{message}' → '{resolved}'")
            return resolved, entity

        return message, None

    # ── Digit response handling ─────────────────────────────────────

    def is_digit_selection(self, message: str) -> bool:
        """Check if a message is a single digit (1-9) — potential menu selection."""
        return bool(re.match(r'^[1-9]$', message.strip()))

    def try_resolve_digit(self, phone: str, message: str) -> Optional[ResolvedSelection]:
        """
        If the user sent a single digit AND there's a pending options list,
        resolve it to the selected person and the original query.
        
        Returns ResolvedSelection or None.
        """
        if not self.is_digit_selection(message):
            return None

        session = self._get_session(phone)
        if session.is_expired() or not session.last_options_list:
            return None

        digit = int(message.strip())
        if digit < 1 or digit > len(session.last_options_list):
            return None

        person = session.last_options_list[digit - 1]
        pending = session.pending_query
        display_name = person.get("canonical_name", "Unknown")

        # Clear the options list after selection (one-shot)
        session.last_options_list = []
        session.pending_query = ""
        session.touch()

        # Update context with the selected person's info
        dept = person.get("department", "")
        mgr = person.get("reports_to", "")
        if dept:
            session.last_department_mentioned = dept
        if mgr:
            session.last_manager_mentioned = mgr

        logger.info(f"🎯 [Resolver] Digit {digit} → {display_name} for query: {pending[:50]}")
        print(f"🎯 [Resolver] Digit {digit} → {display_name} for query: {pending[:50]}")

        return ResolvedSelection(
            person=person,
            pending_query=pending,
            display_name=display_name,
        )

    # ── Contextual scoring ──────────────────────────────────────────

    def _score_matches(
        self,
        matches: List[Dict[str, Any]],
        session: SessionContext,
    ) -> List[Tuple[Dict[str, Any], int]]:
        """
        Score each match based on session context.
        +2 points: person belongs to last_department_mentioned
        +3 points: person reports to last_manager_mentioned
        """
        scored = []
        for person in matches:
            score = 0
            dept = (person.get("department") or "").lower()
            mgr = (person.get("reports_to") or "").lower()

            if session.last_department_mentioned and dept:
                if session.last_department_mentioned.lower() in dept or dept in session.last_department_mentioned.lower():
                    score += 2

            if session.last_manager_mentioned and mgr:
                if session.last_manager_mentioned.lower() in mgr or mgr in session.last_manager_mentioned.lower():
                    score += 3

            scored.append((person, score))

        # Sort by score descending, then by canonical name for stability
        scored.sort(key=lambda x: (-x[1], x[0].get("canonical_name", "")))
        return scored

    # ── Ambiguity menu builder ──────────────────────────────────────

    def handle_ambiguity(
        self,
        phone: str,
        name_query: str,
        matches: List[Dict[str, Any]],
        original_question: str,
    ) -> str:
        """
        Build a WhatsApp-friendly disambiguation menu.
        Saves state so subsequent digit responses resolve correctly.

        Returns the formatted Hebrew message string to send to the user.
        """
        session = self._get_session(phone)
        session.touch()

        scored = self._score_matches(matches, session)
        top_person, top_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else 0

        # Store options for digit-based selection (ordered by score)
        ordered_people = [p for p, _ in scored]
        session.last_options_list = ordered_people
        session.pending_query = original_question

        # ── Smart suggestion: top candidate significantly higher ──
        if top_score > 0 and (top_score - second_score) >= 2 and len(scored) > 1:
            top_name = top_person.get("canonical_name", "")
            top_dept = top_person.get("department", "")
            top_title = top_person.get("title", "")
            label = f"{top_name}"
            if top_dept:
                label += f" ({top_dept})"
            elif top_title:
                label += f" ({top_title})"

            lines = [f"💡 התכוונת ל-*{label}*?"]
            lines.append("(השב *1* לאישור, או בחר מהרשימה)")
            lines.append("")
            for i, (person, _) in enumerate(scored, 1):
                pname = person.get("canonical_name", "?")
                pdept = person.get("department", "")
                ptitle = person.get("title", "")
                suffix = f" ({pdept})" if pdept else (f" ({ptitle})" if ptitle else "")
                lines.append(f"{i}. {pname}{suffix}")

            msg = "\n".join(lines)
            logger.info(f"🔀 [Resolver] Smart suggestion: {top_name} (score {top_score}) for '{name_query}'")
            print(f"🔀 [Resolver] Smart suggestion: {top_name} (score {top_score}) for '{name_query}'")
            return msg

        # ── Standard numbered list (equal scores) ──
        lines = [
            f"מצאתי מספר אנשים בשם זה. למי התכוונת? (השב במספר):",
            "",
        ]
        for i, (person, _) in enumerate(scored, 1):
            pname = person.get("canonical_name", "?")
            pdept = person.get("department", "")
            ptitle = person.get("title", "")
            suffix = f" ({pdept})" if pdept else (f" ({ptitle})" if ptitle else "")
            lines.append(f"{i}. {pname}{suffix}")

        msg = "\n".join(lines)
        logger.info(f"🔀 [Resolver] Ambiguity menu ({len(scored)} options) for '{name_query}'")
        print(f"🔀 [Resolver] Ambiguity menu ({len(scored)} options) for '{name_query}'")
        return msg

    # ── Name extraction helper ──────────────────────────────────────

    @staticmethod
    def extract_person_name(message: str) -> Optional[str]:
        """
        Extract the person name from a KB query.
        
        Examples:
            "מי מדווח ליובל?"      → "יובל"
            "מה התפקיד של דנה?"    → "דנה"
            "מי המנהל של שי?"      → "שי"
            "מה השכר של Guy Klein?" → "Guy Klein"
        """
        # Hebrew patterns with prepositions — covers many natural variations
        patterns = [
            r'מי מדווח ל(.+?)[\?؟\s]*$',
            r'מה התפקיד של (.+?)[\?؟\s]*$',
            r'מי בצוות של (.+?)[\?؟\s]*$',
            r'מי עובד תחת (.+?)[\?؟\s]*$',
            r'מי כפוף ל(.+?)[\?؟\s]*$',
            r'למי מדווח (.+?)[\?؟\s]*$',
            r'מי המנהל של (.+?)[\?؟\s]*$',
            r'מי האחראי על (.+?)[\?؟\s]*$',
            r'מה השכר של (.+?)[\?؟\s]*$',
            r'מה המשכורת של (.+?)[\?؟\s]*$',
            r'כמה מרוויח (.+?)[\?؟\s]*$',
            r'כמה מרוויחה (.+?)[\?؟\s]*$',
            r'מה הדירוג של (.+?)[\?؟\s]*$',
            r'מה הציון של (.+?)[\?؟\s]*$',
            r'מה ה-rating של (.+?)[\?؟\s]*$',
            r'ספר לי על (.+?)[\?؟\s]*$',
            # Natural variations with "וכמה", "כמה", "ומה" prefixes
            r'(?:ו?)כמה (?:ה?)משכורת(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'(?:ו?)כמה (?:ה?)שכר(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'(?:ו?)מה (?:ה?)משכורת(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'(?:ו?)מה (?:ה?)שכר(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'(?:ו?)מה (?:ה?)דירוג(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'(?:ו?)מה (?:ה?)ציון(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            # "תן לי" patterns
            r'תן לי (?:את )?(?:ה?)דירוג(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'תן לי (?:את )?(?:ה?)שכר(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'תן לי (?:את )?(?:ה?)משכורת(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'תן לי (?:את )?(?:ה?)תפקיד(?:\s+\S+)* של (.+?)[\?؟\s]*$',
            r'תן לי מידע על (.+?)[\?؟\s]*$',
            r'הראה לי (?:את )?(?:ה?).+\s+של (.+?)[\?؟\s]*$',
            # Generic "של NAME" — last resort (catches any "... של NAME?")
            r'\s+של\s+(.+?)[\?؟\s]*$',
        ]
        
        text = message.strip()
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                name = m.group(1).strip().rstrip('?؟ ')
                if name:
                    return name
        
        return None


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
identity_resolver = IdentityResolverService()
