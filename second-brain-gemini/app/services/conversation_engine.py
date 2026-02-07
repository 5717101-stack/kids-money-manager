"""
Conversation Engine — LLM-First Architecture with Gemini Function Calling

╔══════════════════════════════════════════════════════════════════════╗
║  This engine replaces ALL regex-based routing with Gemini's native  ║
║  Chat Session + Function Calling. The LLM decides intent, extracts  ║
║  entities, resolves pronouns, and calls tools — automatically.      ║
║                                                                      ║
║  What this eliminates:                                               ║
║  ❌ is_kb_query() regex patterns                                     ║
║  ❌ extract_person_name() regex patterns                             ║
║  ❌ resolve_pronouns() manual pronoun tracking                       ║
║  ❌ has_pronouns() keyword lists                                     ║
║  ❌ pre-flight entity detection                                      ║
║  ❌ Manual last_mentioned_entity tracking                            ║
║                                                                      ║
║  How it works:                                                       ║
║  1. User message → Gemini Chat Session (with tools + history)       ║
║  2. Gemini DECIDES if a tool is needed → calls it                    ║
║  3. Tool results → fed back to Gemini → generates final answer       ║
║  4. Chat history maintained per-user (auto pronoun resolution)       ║
╚══════════════════════════════════════════════════════════════════════╝

Usage:
    from app.services.conversation_engine import conversation_engine

    # Process any text message (KB query, pronoun, chat, etc.)
    answer = conversation_engine.process_message(
        phone="972501234567",
        message="מה הדירוג של אלעד שחר?"
    )
    # → "הדירוג של אלעד שחר הוא Successful."

    answer = conversation_engine.process_message(
        phone="972501234567",
        message="ומה המשכורת שלו?"
    )
    # → Gemini auto-resolves "שלו" = Elad Shachar from chat history
    # → "המשכורת של אלעד שחר היא $XXX."
"""

import json
import logging
import os
import time
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

import google.generativeai as genai
from google.generativeai.types import content_types

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
SESSION_TTL_SECONDS = 1800  # 30 minutes — chat sessions expire after inactivity
MAX_SESSIONS = 200          # Cap to prevent unbounded memory growth
MAX_HISTORY_TURNS = 20      # Keep last 20 turns (40 messages) per session
TOOL_CALL_MAX_RETRIES = 3   # Max tool-call round-trips per message


# ═══════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS — These are the ONLY things "code" handles.
# Gemini decides WHEN and HOW to call them.
# ═══════════════════════════════════════════════════════════════════════

_TOOL_DECLARATIONS = [
    genai.protos.FunctionDeclaration(
        name="search_person",
        description=(
            "Search for a person by name (Hebrew or English, full or partial, nickname) "
            "in the organizational structure and family tree. "
            "Returns matching person records with all available data."
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "name": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Person name to search for (Hebrew or English, can be partial)"
                ),
            },
            required=["name"]
        )
    ),

    genai.protos.FunctionDeclaration(
        name="get_reports",
        description=(
            "Get all people who report to a given manager. "
            "Returns both direct reports and indirect reports (recursive). "
            "Use this for questions like 'Who reports to X?', 'Who is in X's team?'"
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "manager_name": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="The manager's canonical English name (e.g. 'Yuval Laikin')"
                ),
            },
            required=["manager_name"]
        )
    ),

    genai.protos.FunctionDeclaration(
        name="save_fact",
        description=(
            "Save a new fact about a person to the Knowledge Base. "
            "Works for BOTH work-related facts (title, salary, manager, rating) AND "
            "personal/family facts (spouse, children, parent, sibling, nickname, birthday). "
            "Examples of when to use: "
            "'Chen's partner is Oded' → person_name='Chen', field='spouse', value='Oded'. "
            "'Yuval got promoted to VP' → person_name='Yuval Laikin', field='title', value='VP'. "
            "'Shay has a new baby named Noa' → person_name='Shay Hovan', field='children', value='Noa'. "
            "'David's salary is 200K' → person_name='David Kotin', field='salary', value='200000'. "
            "IMPORTANT: First use search_person to resolve the Hebrew name to the canonical English name, "
            "then call save_fact with the English name. "
            "After saving, confirm to the user what was saved."
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "person_name": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="The person's canonical English full name (from search_person results)"
                ),
                "field": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description=(
                        "The field to save. "
                        "Work fields: 'title', 'salary', 'reports_to', 'department', 'rating', 'individual_factor', 'bonus', 'level', 'start_date'. "
                        "Family/personal fields: 'spouse', 'children', 'parent', 'sibling', 'family_role', 'nickname', 'birthday', 'notes'."
                    )
                ),
                "value": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="The value to save (name, number, date, or text)"
                ),
            },
            required=["person_name", "field", "value"]
        )
    ),

    genai.protos.FunctionDeclaration(
        name="list_org_stats",
        description=(
            "Get general organizational statistics: total employees, departments, "
            "hierarchy depth, etc. Use for questions like 'How many employees?', "
            "'Show me the org structure', 'What departments exist?'"
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={},
        )
    ),
]


# ═══════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS — Execute the actual data operations
# ═══════════════════════════════════════════════════════════════════════

def _execute_tool(function_name: str, args: Dict[str, Any]) -> str:
    """Execute a tool function and return the result as a string."""
    try:
        if function_name == "search_person":
            return _tool_search_person(args.get("name", ""))

        elif function_name == "get_reports":
            return _tool_get_reports(args.get("manager_name", ""))

        elif function_name == "save_fact":
            return _tool_save_fact(
                person_name=args.get("person_name", ""),
                field=args.get("field", ""),
                value=args.get("value", ""),
            )

        elif function_name == "list_org_stats":
            return _tool_list_org_stats()

        else:
            return json.dumps({"error": f"Unknown tool: {function_name}"}, ensure_ascii=False)

    except Exception as e:
        logger.error(f"[ConvEngine] Tool execution error ({function_name}): {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _tool_search_person(name: str) -> str:
    """Search for a person across org structure and family tree."""
    from app.services.knowledge_base_service import search_people, get_all_reports_under

    if not name:
        return json.dumps({"error": "No name provided"}, ensure_ascii=False)

    matches = search_people(name)

    if not matches:
        return json.dumps({
            "found": False,
            "message": f"No person found matching '{name}' in the knowledge base.",
            "suggestion": "Try a different spelling, or use the full English name."
        }, ensure_ascii=False)

    # Enrich each match with report count and clear summary
    results = []
    for person in matches:
        entry = dict(person)
        # Convert sets to lists for JSON
        if isinstance(entry.get("aliases"), set):
            entry["aliases"] = list(entry["aliases"])
        # Add report names for context
        canonical = entry.get("canonical_name", "")
        if canonical:
            reports = get_all_reports_under(canonical)
            entry["all_reports_count"] = len(reports)
            entry["all_reports_names"] = reports[:20]  # Cap for payload size
        # Add a human-readable summary line for quick disambiguation
        title = entry.get("title", "")
        dept = entry.get("department", "")
        mgr = entry.get("reports_to", "")
        summary_parts = [canonical]
        if title:
            summary_parts.append(f"({title})")
        if dept:
            summary_parts.append(f"[{dept}]")
        if mgr:
            summary_parts.append(f"reports to: {mgr}")
        entry["_summary"] = " — ".join(summary_parts) if len(summary_parts) > 1 else canonical
        results.append(entry)

    disambiguation_hint = ""
    if len(results) > 1:
        disambiguation_hint = (
            "MULTIPLE MATCHES: Use conversation history to pick the most relevant person. "
            "Check who 'reports_to' someone recently discussed, or shares their department. "
            "Show that person's data first, and offer alternatives at the end."
        )

    return json.dumps({
        "found": True,
        "count": len(results),
        "disambiguation_hint": disambiguation_hint,
        "people": results
    }, ensure_ascii=False, default=str)


def _tool_get_reports(manager_name: str) -> str:
    """Get all reports under a manager (direct + indirect)."""
    from app.services.knowledge_base_service import (
        search_people, get_all_reports_under, get_identity_graph
    )

    if not manager_name:
        return json.dumps({"error": "No manager name provided"}, ensure_ascii=False)

    # First resolve the name
    matches = search_people(manager_name)
    if not matches:
        return json.dumps({
            "found": False,
            "message": f"Manager '{manager_name}' not found in org structure."
        }, ensure_ascii=False)

    # Use the first/best match
    manager = matches[0]
    canonical = manager.get("canonical_name", manager_name)

    # Get ALL reports (recursive)
    all_reports = get_all_reports_under(canonical)

    # Get direct reports from the identity graph
    graph = get_identity_graph()
    people = graph.get("people", {}) if graph else {}
    direct_reports = manager.get("direct_reports", [])

    # Build detailed report list
    report_details = []
    for report_name in all_reports:
        person_info = people.get(report_name, {})
        report_details.append({
            "name": report_name,
            "title": person_info.get("title", ""),
            "department": person_info.get("department", ""),
            "is_direct": report_name in direct_reports,
            "reports_to": person_info.get("reports_to", ""),
        })

    return json.dumps({
        "found": True,
        "manager": {
            "name": canonical,
            "title": manager.get("title", ""),
            "department": manager.get("department", ""),
        },
        "direct_reports": [r for r in report_details if r["is_direct"]],
        "indirect_reports": [r for r in report_details if not r["is_direct"]],
        "total_reports": len(all_reports),
    }, ensure_ascii=False, default=str)


def _tool_save_fact(person_name: str, field: str, value: str) -> str:
    """Save a fact about a person (work or family) to the Knowledge Base."""
    if not person_name or not field or not value:
        return json.dumps({"error": "person_name, field, and value are all required"}, ensure_ascii=False)

    try:
        from app.services.context_writer_service import context_writer, ExtractedFact

        fact = ExtractedFact(
            person_name=person_name,
            field=field,
            old_value=None,
            new_value=value,
            source_quote="User direct input via chat",
            confidence="high",
        )

        success, errors = context_writer.apply_facts([fact])

        if success > 0:
            # Also refresh the conversation engine's system instruction
            # so the next query already has the updated data
            try:
                conversation_engine.refresh_system_instruction()
            except Exception:
                pass

            return json.dumps({
                "success": True,
                "message": f"Saved: {person_name}'s {field} = {value}",
                "person": person_name,
                "field": field,
                "value": value,
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "message": f"Failed to save: {'; '.join(errors)}",
            }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _tool_list_org_stats() -> str:
    """Get general organizational statistics."""
    from app.services.knowledge_base_service import get_identity_graph

    graph = get_identity_graph()
    if not graph:
        return json.dumps({"error": "Identity graph not loaded"}, ensure_ascii=False)

    people = graph.get("people", {})
    departments = set()
    work_count = 0
    family_count = 0
    managers = set()

    for name, info in people.items():
        dept = info.get("department", "")
        if dept:
            departments.add(dept)
        contexts = info.get("contexts", [])
        if "work" in contexts:
            work_count += 1
        if "family" in contexts:
            family_count += 1
        if info.get("direct_reports"):
            managers.add(name)

    return json.dumps({
        "total_people": len(people),
        "employees": work_count,
        "family_members": family_count,
        "departments": sorted(departments),
        "department_count": len(departments),
        "managers_count": len(managers),
    }, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════
# CHAT SESSION MANAGEMENT — Per-user sessions with TTL
# ═══════════════════════════════════════════════════════════════════════

class UserSession:
    """Holds a Gemini ChatSession + metadata for a single user."""

    def __init__(self, chat: Any, model_name: str):
        self.chat = chat
        self.model_name = model_name
        self.last_activity: float = time.time()
        self.message_count: int = 0

    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > SESSION_TTL_SECONDS

    def touch(self):
        self.last_activity = time.time()
        self.message_count += 1


# ═══════════════════════════════════════════════════════════════════════
# CONVERSATION ENGINE — The main class
# ═══════════════════════════════════════════════════════════════════════

class ConversationEngine:
    """
    LLM-First Conversation Engine.

    Every message goes through Gemini Chat Session with tools.
    Gemini decides intent, extracts entities, resolves pronouns,
    and calls tools — all natively, no regex needed.
    """

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}
        self._lock = Lock()
        self._model = None
        self._model_name: str = ""
        self._kb_system_instruction: str = ""
        self._initialized = False

    def initialize(self):
        """Initialize the engine (called once on startup after KB is loaded)."""
        if self._initialized:
            return

        from app.services.model_discovery import configure_genai, MODEL_MAPPING
        from app.services.knowledge_base_service import get_system_instruction_block

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            print("⚠️ [ConvEngine] No API key — engine disabled")
            return

        configure_genai(api_key)

        self._model_name = MODEL_MAPPING.get("pro", "gemini-2.5-pro")

        # Build the system instruction with KB context
        kb_block = get_system_instruction_block()

        self._kb_system_instruction = f"""אתה עוזר ארגוני מקצועי בשם "Second Brain".
אתה עונה בעברית אלא אם נשאלת באנגלית.
יש לך גישה לכלים (functions) שמאפשרים לך לחפש ולעדכן מידע ארגוני.

══════════════════════════════════════════════════════
כללי התנהגות:
══════════════════════════════════════════════════════
1. לשאלות על אנשים, תפקידים, שכר, דירוגים, היררכיה — תמיד השתמש בכלי search_person או get_reports.
2. אם המשתמש מבקש לעדכן או לשמור מידע — השתמש בכלי save_fact. זה עובד גם למידע ארגוני (שכר, תפקיד, מנהל) וגם למידע אישי/משפחתי (בן זוג, ילדים, כינוי).
   דוגמאות:
   - "לבן הזוג של חן קוראים עודד" → search_person("חן"), ואז save_fact(person_name="Chen ...", field="spouse", value="עודד")
   - "היובל קיבל העלאה ל-60K" → save_fact(person_name="Yuval Laikin", field="salary", value="60000")
   - "לשי יש ילד חדש שקוראים לו נועם" → save_fact(person_name="Shay Hovan", field="children", value="נועם")
3. לשאלות כלליות על הארגון (כמה עובדים, מחלקות) — השתמש בכלי list_org_stats.
4. לשיחה רגילה (שאלות כלליות, הודעות אישיות) — ענה ישירות בלי כלים.
5. כינויי גוף: אם המשתמש אומר "שלו", "שלה", "הוא", "היא" — הסתכל בהיסטוריית השיחה ותבין למי הוא מתכוון. אל תשאל אלא אם באמת אי אפשר לדעת.
6. שמות בעברית: כשהמשתמש מזכיר שם בעברית, השתמש ב-search_person כדי למצוא את השם המלא באנגלית.
7. 🔴 חיזוי חכם כשיש כמה תוצאות (SMART DISAMBIGUATION):
   אם search_person מחזיר יותר מתוצאה אחת, אל תציג רשימה סתמית!
   במקום זה, בצע ניתוח הקשרי:
   א. בדוק מי מבין התוצאות קשור להקשר השיחה האחרונה:
      - האם מישהו מהם מדווח למנהל שדיברנו עליו זה עתה?
      - האם מישהו מהם באותה מחלקה שהוזכרה?
      - האם מישהו מהם נזכר קודם בשיחה?
   ב. אם יש מועמד מועדף לפי ההקשר — הנח שהמשתמש מתכוון אליו, הצג את הנתונים שלו, ואז הוסף בסוף:
      "אם התכוונת ל-[שם2] שלח 2, ל-[שם3] שלח 3"
   ג. רק אם אין שום הקשר שעוזר להבחין — הצג רשימה ממוספרת ושאל "למי התכוונת?".
   דוגמה:
      - המשתמש שאל על "יובל" (Yuval Laikin, מנהל), ואז שאל על "שי"
      - search_person("שי") מחזיר 3 תוצאות: שי הובן (מדווח ליובל), שי פינקלשטיין, שי אמיר
      - ← הנח ששי הובן הוא הכוונה (כי מדווח ליובל שדיברנו עליו), הצג את הנתונים שלו, ובסוף:
        "אם התכוונת לשי פינקלשטיין שלח 2, לשי אמיר שלח 3"
8. לעולם אל תמציא מידע. אם לא מצאת — אמור "לא מצאתי מידע על X בבסיס הידע".
9. כשמציג מידע פיננסי (שכר, בונוס) — ציין את המספר המדויק, אל תעגל.
10. כשמציג היררכיה — הבחן בין כפופים ישירים לעקיפים.
11. אם המשתמש משיב ספרה בודדת (1-9), הבן שהוא בוחר מהרשימה האחרונה שהצגת. הצג את הנתונים של האדם שנבחר.

══════════════════════════════════════════════════════
כלים (Tools) — אל תקרא להם בשמם בפני המשתמש:
══════════════════════════════════════════════════════
• search_person(name) → חיפוש אדם לפי שם (עברית/אנגלית, מלא/חלקי)
• get_reports(manager_name) → כל הכפופים למנהל (ישירים + עקיפים)
• save_fact(person_name, field, value) → שמירת עובדה (עבודה או משפחה) לבסיס הידע
• list_org_stats() → סטטיסטיקות כלליות על הארגון

══════════════════════════════════════════════════════
זרימת עדכון מידע — save_fact:
══════════════════════════════════════════════════════
כשהמשתמש אומר עובדה חדשה (כמו "לבן הזוג של חן קוראים עודד"):
1. תחילה, קרא ל-search_person כדי לזהות את השם המלא באנגלית
2. אחר כך, קרא ל-save_fact עם השם המלא, השדה, והערך
3. אשר למשתמש: "שמרתי ✅ — בן הזוג של חן הוא עודד"
4. מעכשיו, כשישאלו "איך קוראים לבן הזוג של חן?" — תדע לענות "עודד"

{kb_block}"""

        # Create the model with tools
        tools = genai.protos.Tool(function_declarations=_TOOL_DECLARATIONS)

        try:
            self._model = genai.GenerativeModel(
                model_name=self._model_name,
                tools=[tools],
                system_instruction=self._kb_system_instruction,
            )
            self._initialized = True
            print(f"✅ [ConvEngine] Initialized with model: {self._model_name}")
            print(f"   System instruction: {len(self._kb_system_instruction)} chars")
            print(f"   Tools: {[d.name for d in _TOOL_DECLARATIONS]}")
        except Exception as e:
            logger.error(f"[ConvEngine] Init failed: {e}")
            print(f"❌ [ConvEngine] Init failed: {e}")

    def _get_or_create_session(self, phone: str) -> UserSession:
        """Get existing session or create a new one for this phone number."""
        with self._lock:
            # Cleanup expired sessions
            expired = [p for p, s in self._sessions.items() if s.is_expired()]
            for p in expired:
                del self._sessions[p]
                print(f"🗑️ [ConvEngine] Expired session for {p[-4:]}")

            # Cap sessions
            if len(self._sessions) >= MAX_SESSIONS:
                oldest = min(self._sessions, key=lambda p: self._sessions[p].last_activity)
                del self._sessions[oldest]
                print(f"🗑️ [ConvEngine] Evicted oldest session for {oldest[-4:]}")

            # Return existing or create new
            if phone in self._sessions and not self._sessions[phone].is_expired():
                session = self._sessions[phone]
                session.touch()
                return session

            # Create a new chat session
            chat = self._model.start_chat(history=[])
            session = UserSession(chat=chat, model_name=self._model_name)
            self._sessions[phone] = session
            print(f"🆕 [ConvEngine] New chat session for {phone[-4:]}")
            return session

    def process_message(self, phone: str, message: str) -> str:
        """
        Process a user message through the Gemini Chat Session.

        This is the SINGLE entry point for all text messages.
        Gemini decides everything: intent, entity extraction, tool calling.

        Args:
            phone: User's phone number (session key)
            message: The user's text message

        Returns:
            The AI's response text
        """
        if not self._initialized or self._model is None:
            return "⚠️ המערכת עדיין בטעינה, נסה שוב בעוד כמה שניות."

        session = self._get_or_create_session(phone)
        chat = session.chat

        try:
            print(f"\n{'='*60}")
            print(f"🧠 [ConvEngine] Processing message for {phone[-4:]}")
            print(f"   Message: {message[:100]}{'...' if len(message) > 100 else ''}")
            print(f"   Session: {session.message_count} prior messages")
            print(f"   History turns: {len(chat.history) // 2}")
            print(f"{'='*60}")

            # Send message to Gemini
            response = chat.send_message(message)

            # Handle tool calls (iterative — Gemini may call multiple tools)
            round_count = 0
            while response.candidates and round_count < TOOL_CALL_MAX_RETRIES:
                candidate = response.candidates[0]
                content = candidate.content

                # Check if there are function calls in the response
                function_calls = [
                    part.function_call
                    for part in content.parts
                    if hasattr(part, 'function_call') and part.function_call.name
                ]

                if not function_calls:
                    break  # No more tool calls — we have a text response

                round_count += 1
                print(f"   🔧 [ConvEngine] Tool call round {round_count}:")

                # Execute all function calls and collect responses
                tool_responses = []
                for fc in function_calls:
                    fn_name = fc.name
                    fn_args = dict(fc.args) if fc.args else {}
                    print(f"      → {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:80]})")

                    result_str = _execute_tool(fn_name, fn_args)
                    print(f"      ← {result_str[:100]}{'...' if len(result_str) > 100 else ''}")

                    tool_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fn_name,
                                response={"result": result_str}
                            )
                        )
                    )

                # Send tool results back to Gemini for interpretation
                response = chat.send_message(
                    genai.protos.Content(parts=tool_responses)
                )

            # Extract final text response
            final_text = ""
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        final_text += part.text

            if not final_text:
                final_text = "⚠️ לא הצלחתי לייצר תשובה. נסה לנסח אחרת."

            # Trim history if too long
            self._trim_history(chat)

            print(f"   ✅ [ConvEngine] Response: {final_text[:120]}{'...' if len(final_text) > 120 else ''}")
            print(f"{'='*60}\n")

            return final_text

        except Exception as e:
            logger.error(f"[ConvEngine] Error processing message: {e}")
            import traceback
            traceback.print_exc()

            # On error, try to reset the session and fall back
            try:
                fallback_answer = self._fallback_generate(message)
                if fallback_answer:
                    return fallback_answer
            except Exception:
                pass

            return f"❌ שגיאה בעיבוד ההודעה. נסה שוב. ({str(e)[:50]})"

    def _fallback_generate(self, message: str) -> Optional[str]:
        """Fallback: single-shot generate without chat session (no history)."""
        from app.services.model_discovery import gemini_v1_generate, MODEL_MAPPING
        from app.services.knowledge_base_service import get_kb_query_context

        kb_context = get_kb_query_context()
        prompt = f"""אתה עוזר ארגוני. ענה בעברית.

{f'בסיס ידע:{chr(10)}{kb_context[:8000]}' if kb_context else ''}

שאלה: {message}

תשובה:"""

        try:
            answer = gemini_v1_generate(
                prompt=prompt,
                model_name=MODEL_MAPPING.get("flash"),
                temperature=0.3,
                max_output_tokens=1000,
                timeout=60,
            )
            if answer:
                print(f"   ⚠️ [ConvEngine] Used fallback (no chat session)")
                return answer
        except Exception as e:
            logger.error(f"[ConvEngine] Fallback also failed: {e}")

        return None

    def _trim_history(self, chat):
        """Trim chat history to prevent token overflow."""
        try:
            if len(chat.history) > MAX_HISTORY_TURNS * 2:
                # Keep only the last N turns
                chat.history[:] = chat.history[-(MAX_HISTORY_TURNS * 2):]
                print(f"   ✂️ [ConvEngine] Trimmed history to {len(chat.history)} entries")
        except Exception:
            pass

    def clear_session(self, phone: str):
        """Clear a user's chat session."""
        with self._lock:
            if phone in self._sessions:
                del self._sessions[phone]
                print(f"🗑️ [ConvEngine] Cleared session for {phone[-4:]}")

    def get_session_info(self, phone: str) -> Dict[str, Any]:
        """Get info about a user's current session."""
        with self._lock:
            if phone not in self._sessions:
                return {"active": False}
            session = self._sessions[phone]
            return {
                "active": not session.is_expired(),
                "message_count": session.message_count,
                "model": session.model_name,
                "history_turns": len(session.chat.history) // 2,
                "age_seconds": int(time.time() - session.last_activity),
            }

    def refresh_system_instruction(self):
        """Reload KB context into system instruction (e.g., after KB update)."""
        self._initialized = False
        self._sessions.clear()
        self.initialize()
        print(f"🔄 [ConvEngine] System instruction refreshed, all sessions cleared")


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
conversation_engine = ConversationEngine()
