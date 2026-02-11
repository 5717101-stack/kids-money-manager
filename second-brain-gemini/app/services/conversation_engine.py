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

    genai.protos.FunctionDeclaration(
        name="search_meetings",
        description=(
            "Search through past meeting transcripts and recordings. "
            "Use when the user asks about past conversations, previous meetings, "
            "or wants to prepare for an upcoming meeting with someone. "
            "Can search by speaker name, topic, keywords, or date. "
            "Examples: 'When did I last talk to Yuval?', 'What did we discuss about budget?', "
            "'Prepare me for a meeting with David', 'What did Yuval say about vacation?'. "
            "Also use when user asks 'what did we talk about?' or 'summarize last meeting'."
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "query": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Search query: keywords, topic, or speaker name (Hebrew or English)"
                ),
                "speaker_name": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Optional: specific speaker to search for (e.g. 'Yuval', 'יובל')"
                ),
            },
            required=["query"]
        )
    ),

    genai.protos.FunctionDeclaration(
        name="search_notebook",
        description=(
            "Search through NotebookLM-style deep analyses of past recordings and meetings. "
            "These analyses contain executive summaries, key topics, action items, decisions, "
            "notable quotes, speaker profiles, and follow-up questions. "
            "Use when the user asks for deep insights about past meetings, wants to find "
            "specific decisions, action items, or quotes from recordings. "
            "Examples: 'מה ההחלטות שהתקבלו בפגישה האחרונה?', 'אילו משימות נקבעו?', "
            "'מה היו הנושאים המרכזיים בשיחה עם יובל?', 'תן לי את הציטוטים החשובים'. "
            "Note: This searches through the rich NotebookLM analyses (if enabled), "
            "not the raw transcripts. For raw transcript search use search_meetings."
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "query": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Search terms: keywords, speaker names, topics, or action items"
                ),
            },
            required=["query"]
        )
    ),

    genai.protos.FunctionDeclaration(
        name="search_flights",
        description=(
            "Search for round-trip DIRECT flights from Tel Aviv (TLV) to a destination. "
            "Use when the user asks about flights, travel, flying, or mentions a destination with travel intent. "
            "Examples: 'בדוק טיסות לקפריסין', 'טיסות לרומא בפסח', 'יש משהו זול ליוון?', "
            "'חפש טיסה לפראג בשבוע הבא', 'אפשר לטוס לברצלונה ב500 שקל?'. "
            "IMPORTANT: When the user mentions a date in natural language (e.g. 'בפסח', 'בקיץ', 'בחנוכה', "
            "'שבוע הבא', 'חודש הבא'), YOU must resolve it to specific dates before calling this tool. "
            "Available destinations (use the Hebrew key): "
            "קפריסין, פאפוס, לרנקה, יוון, אתונה, רודוס, כרתים, רומא, מילאנו, "
            "ברצלונה, פראג, בודפשט, וינה, קרקוב, ורשה, איסטנבול, אנטליה, "
            "תאילנד, לונדון, פריז, ברלין, אמסטרדם. "
            "If the destination is not in the list, tell the user which destinations are available."
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "destination": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Destination name in Hebrew (must be one of the available keys, e.g. 'קפריסין', 'רומא', 'פראג')"
                ),
                "max_price_eur": genai.protos.Schema(
                    type=genai.protos.Type.NUMBER,
                    description="Optional: Maximum price per person in EUR for the round-trip. If user says NIS/שקל, convert roughly (1 EUR ≈ 4 ILS)."
                ),
                "date_from": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Optional: Start of date range to search, format DD/MM/YYYY. Resolve natural language dates (e.g. 'פסח 2026' → '01/04/2026', 'שבוע הבא' → next Monday's date)."
                ),
                "date_to": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Optional: End of date range to search, format DD/MM/YYYY. (e.g. 'פסח 2026' → '09/04/2026')."
                ),
                "nights_from": genai.protos.Schema(
                    type=genai.protos.Type.NUMBER,
                    description="Optional: Minimum number of nights (default 2). If user says 'סוף שבוע' use 2, 'שבוע' use 5-7."
                ),
                "nights_to": genai.protos.Schema(
                    type=genai.protos.Type.NUMBER,
                    description="Optional: Maximum number of nights (default 7)."
                ),
            },
            required=["destination"]
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

        elif function_name == "search_meetings":
            return _tool_search_meetings(
                query=args.get("query", ""),
                speaker_name=args.get("speaker_name", ""),
            )

        elif function_name == "search_notebook":
            return _tool_search_notebook(
                query=args.get("query", ""),
            )

        elif function_name == "search_flights":
            return _tool_search_flights(
                destination=args.get("destination", ""),
                max_price_eur=args.get("max_price_eur"),
                date_from=args.get("date_from"),
                date_to=args.get("date_to"),
                nights_from=args.get("nights_from"),
                nights_to=args.get("nights_to"),
            )

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


def _tool_search_meetings(query: str, speaker_name: str = "") -> str:
    """Search past meeting transcripts for a query and/or speaker."""
    dms = conversation_engine._drive_memory_service
    if not dms:
        return json.dumps({"error": "Drive service not available. Cannot search transcripts."}, ensure_ascii=False)

    # 1. Try Transcripts folder first (dedicated files)
    search_terms = [t.strip() for t in query.split() if t.strip()]
    if speaker_name:
        search_terms.append(speaker_name)

    results = dms.search_transcripts(search_terms, limit=5) if search_terms else []

    # 2. Also search in-memory working memory for the latest session
    wm = conversation_engine._working_memory
    wm_matches = []
    for phone, mem in wm.items():
        summary = mem.get("summary", "")
        speakers = mem.get("speakers", [])
        # Check if query matches summary or speaker
        q_lower = query.lower()
        if (q_lower and q_lower in summary.lower()) or \
           any(speaker_name.lower() in s.lower() for s in speakers if speaker_name):
            wm_matches.append({
                "source": "working_memory (latest session)",
                "timestamp": mem.get("timestamp", ""),
                "speakers": speakers,
                "summary": summary,
            })

    # 3. Also search chat_history in second_brain_memory.json
    # This covers older meetings saved in the memory file
    memory_matches = []
    try:
        memory = dms.get_memory()
        chat_history = memory.get("chat_history", [])
        for entry in reversed(chat_history):
            if entry.get("type") != "audio":
                continue
            # Check against transcript, speakers, and expert analysis
            entry_speakers = entry.get("speakers", [])
            transcript = entry.get("transcript", {})
            segments = transcript.get("segments", []) if isinstance(transcript, dict) else []
            expert = entry.get("expert_analysis", {})
            raw_analysis = expert.get("raw_analysis", "") if expert else ""
            summary_text = ""
            for seg in segments:
                summary_text += seg.get("text", "") + " "
            summary_text += raw_analysis

            match_found = False
            if query:
                q_lower = query.lower()
                if q_lower in summary_text.lower():
                    match_found = True
            if speaker_name:
                for s in entry_speakers:
                    if speaker_name.lower() in s.lower():
                        match_found = True
                        break

            if match_found:
                # Extract a concise summary instead of dumping everything
                key_segments = []
                for seg in segments:
                    seg_text = seg.get("text", "")
                    if query and query.lower() in seg_text.lower():
                        key_segments.append({
                            "speaker": seg.get("speaker", ""),
                            "text": seg_text[:200],
                        })
                    elif speaker_name and speaker_name.lower() in seg.get("speaker", "").lower():
                        key_segments.append({
                            "speaker": seg.get("speaker", ""),
                            "text": seg_text[:200],
                        })

                memory_matches.append({
                    "source": "second_brain_memory (archived)",
                    "timestamp": entry.get("timestamp", ""),
                    "speakers": entry_speakers,
                    "segment_count": len(segments),
                    "key_segments": key_segments[:10],
                    "expert_summary": raw_analysis[:500] if raw_analysis else "",
                })

                if len(memory_matches) >= 5:
                    break
    except Exception as e:
        logger.error(f"[search_meetings] Error searching memory: {e}")

    total_found = len(results) + len(wm_matches) + len(memory_matches)
    if total_found == 0:
        return json.dumps({
            "found": False,
            "message": f"No meetings found matching '{query}'{f' with speaker {speaker_name}' if speaker_name else ''}.",
            "suggestion": "Try different keywords or a different speaker name."
        }, ensure_ascii=False)

    return json.dumps({
        "found": True,
        "total_matches": total_found,
        "from_transcripts_folder": results[:5],
        "from_working_memory": wm_matches,
        "from_chat_history": memory_matches[:5],
    }, ensure_ascii=False, default=str)


def _tool_search_notebook(query: str) -> str:
    """Search through NotebookLM deep analyses of past recordings."""
    from app.services.notebooklm_service import notebooklm_service

    if not notebooklm_service.is_enabled:
        return json.dumps({
            "error": "שירות NotebookLM מכובה. אפשר להפעיל אותו דרך NOTEBOOKLM_ENABLED=true.",
            "suggestion": "השתמש ב-search_meetings לחיפוש בתמלולים רגילים."
        }, ensure_ascii=False)

    dms = conversation_engine._drive_memory_service
    if not dms:
        return json.dumps({
            "error": "Drive service not available. Cannot search NotebookLM summaries."
        }, ensure_ascii=False)

    results = notebooklm_service.search_summaries(
        query=query,
        drive_memory_service=dms,
        limit=5
    )

    if not results:
        return json.dumps({
            "found": False,
            "message": f"לא נמצאו ניתוחי NotebookLM התואמים ל-'{query}'.",
            "suggestion": "נסה מילות חיפוש אחרות, או השתמש ב-search_meetings לחיפוש בתמלולים."
        }, ensure_ascii=False)

    return json.dumps({
        "found": True,
        "count": len(results),
        "analyses": results,
    }, ensure_ascii=False, default=str)


def _tool_search_flights(
    destination: str,
    max_price_eur=None,
    date_from: str = None,
    date_to: str = None,
    nights_from=None,
    nights_to=None,
) -> str:
    """Search for round-trip direct flights using the flight search service."""
    from app.services.flight_search_service import flight_search_service, DESTINATION_MAP

    if not destination:
        return json.dumps({"error": "No destination provided"}, ensure_ascii=False)

    # Lazy re-configure if needed
    if not flight_search_service.is_configured:
        flight_search_service._configure()

    if not flight_search_service.is_configured:
        return json.dumps({
            "error": "שירות חיפוש טיסות לא מוגדר. יש להגדיר מפתחות API (Amadeus, SerpAPI, או Kiwi).",
        }, ensure_ascii=False)

    # Build kwargs
    kwargs = {"destination_key": destination}
    if max_price_eur is not None:
        kwargs["max_price_eur"] = int(max_price_eur)
    if date_from:
        kwargs["date_from"] = date_from
    if date_to:
        kwargs["date_to"] = date_to
    if nights_from is not None:
        kwargs["nights_from"] = int(nights_from)
    if nights_to is not None:
        kwargs["nights_to"] = int(nights_to)

    print(f"  ✈️ [Tool] search_flights called: {kwargs}")

    try:
        results = flight_search_service.search_flights(**kwargs)

        if not results.get("success") or not results.get("flights"):
            error_msg = results.get("error", "")
            return json.dumps({
                "found": False,
                "message": f"לא נמצאו טיסות ישירות ל{destination}. {error_msg}",
                "available_destinations": list(DESTINATION_MAP.keys()),
            }, ensure_ascii=False)

        # Format results for display
        formatted = flight_search_service.format_results(
            results,
            query_text=f"{'עד €' + str(kwargs.get('max_price_eur', '')) if kwargs.get('max_price_eur') else 'כל המחירים'}"
        )

        return json.dumps({
            "found": True,
            "total_flights": len(results["flights"]),
            "formatted_message": formatted,
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"[search_flights] Error: {e}")
        return json.dumps({"error": f"שגיאה בחיפוש טיסות: {str(e)}"}, ensure_ascii=False)


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
        self._user_profile: Dict[str, Any] = {}          # Phase 1: Personal profile
        self._drive_memory_service = None                 # Phase 2B: For search_meetings
        self._working_memory: Dict[str, Dict[str, Any]] = {}  # Phase 3: Per-user latest session

    def initialize(self, user_profile: Dict[str, Any] = None, drive_memory_service=None):
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

        # Store references (safe — no circular imports)
        if user_profile:
            self._user_profile = user_profile
        if drive_memory_service:
            self._drive_memory_service = drive_memory_service

        # Use Flash for conversation — Pro is a "thinking" model that adds 5-15s
        # per API call. Flash is 3-5x faster with excellent function calling and
        # multi-turn context. Pro is reserved for complex tasks (audio analysis, etc.)
        self._model_name = MODEL_MAPPING.get("flash", "gemini-2.0-flash")

        # Build the system instruction with KB context
        kb_block = get_system_instruction_block()

        # Phase 1: Build user profile context block
        profile_block = self._build_profile_block()

        # Dynamic date for accurate day-of-week awareness
        from datetime import datetime as _dt
        _now = _dt.now()
        _day_names_he = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
        _today_he = _day_names_he[_now.weekday()]
        _date_str = _now.strftime("%d/%m/%Y")

        self._kb_system_instruction = f"""אתה עוזר אישי וארגוני חכם בשם "Second Brain".
אתה עונה בעברית אלא אם נשאלת באנגלית.
יש לך גישה לכלים (functions) שמאפשרים לך לחפש אנשים ומידע ארגוני, לשמור עובדות, לחפש בפגישות קודמות, ולחפש טיסות.

📅 התאריך של היום: {_date_str} (יום {_today_he}).
🔴 כשהמשתמש אומר "היום" — הכוונה ליום {_today_he}, {_date_str}. השתמש בתאריך הזה בלבד.

{profile_block}

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
4. לשיחה רגילה (שאלות כלליות שלא קשורות לאנשים, מידע ארגוני, פגישות או טיסות) — ענה ישירות בלי כלים.
   🔴 חשוב: אם המשתמש שואל על עצמו (ילדים, משפחה, העדפות) — קודם בדוק את הפרופיל האישי למעלה לפני שעונה.
   🔴 חשוב: אם ההודעה מזכירה טיסות, נסיעות, חופשה, טיסה ליעד — זו לא "שיחה רגילה"! השתמש בכלי search_flights.
5. הקשר שיחה וכינויים: כשהמשתמש מתייחס למישהו — בין אם דרך כינויי גוף (שלו, שלה, אליו, אותו, ממנו, איתו, בו, אצלו...), בין אם דרך ביטויים עקיפים ("מי מדווח אליו?", "מה הביצועים?"), ובין אם בכל דרך אחרת — הסתכל בהיסטוריית השיחה וברמז [הקשר אחרון:] שמופיע בתחילת ההודעה, ותבין למי הוא מתכוון. אל תשאל אלא אם באמת אי אפשר לדעת.
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
12. 📼 כשהמשתמש מבקש "הכנה לשיחה עם X", "על מה דיברנו עם X?", "מתי דיברתי עם X?" — השתמש בכלי search_meetings כדי למצוא שיחות קודמות.
   שלב את הנתונים מהפגישות עם המידע מבסיס הידע (search_person) כדי לתת הכנה מקיפה.
   דוגמה: "הכן אותי לשיחה עם יובל" → search_person("יובל") + search_meetings(query="יובל", speaker_name="Yuval") → שלב הכל לתשובה אחת.
13. ✈️ חיפוש טיסות: כשהמשתמש מזכיר טיסות, נסיעות, חופשה ליעד, או שואל על מחירי טיסה — השתמש בכלי search_flights.
   🔴 חשוב מאוד — תרגום תאריכים: אם המשתמש אומר תאריך בשפה טבעית, אתה חייב לתרגם אותו לתאריכים מדויקים לפני שקוראים לכלי:
   - "פסח" (2026) → date_from="01/04/2026", date_to="09/04/2026"
   - "סוכות" (2026) → date_from="02/10/2026", date_to="09/10/2026"
   - "חנוכה" (2026) → date_from="25/12/2026", date_to="02/01/2027"
   - "שבוע הבא" → date_from=תאריך יום ראשון הבא, date_to=תאריך שבת הבאה
   - "חודש הבא" → date_from=1 בחודש הבא, date_to=סוף החודש הבא
   - "בקיץ" → date_from="01/07/2026", date_to="31/08/2026"
   - "סוף שבוע" → nights_from=2, nights_to=3
   - "שבוע" → nights_from=5, nights_to=7
   🔴 אם המשתמש מציין מחיר בשקלים, המר ליורו (1 EUR ≈ 4 ILS). לדוגמה: "500 שקל" → max_price_eur=125.
   🔴 הצג את התוצאות כמו שמוחזרות מהכלי (formatted_message). אל תנסה לעצב מחדש.
   דוגמאות:
   - "טיסות לקפריסין בפסח" → search_flights(destination="קפריסין", date_from="01/04/2026", date_to="09/04/2026")
   - "יש משהו זול ליוון?" → search_flights(destination="יוון")
   - "בדוק טיסות לפראג עד 100 יורו" → search_flights(destination="פראג", max_price_eur=100)
   - "טיסה לרומא לסוף שבוע בחודש הבא" → search_flights(destination="רומא", date_from="01/03/2026", date_to="31/03/2026", nights_from=2, nights_to=3)

══════════════════════════════════════════════════════
כלים (Tools) — אל תקרא להם בשמם בפני המשתמש:
══════════════════════════════════════════════════════
• search_person(name) → חיפוש אדם לפי שם (עברית/אנגלית, מלא/חלקי)
• get_reports(manager_name) → כל הכפופים למנהל (ישירים + עקיפים)
• save_fact(person_name, field, value) → שמירת עובדה (עבודה או משפחה) לבסיס הידע
• list_org_stats() → סטטיסטיקות כלליות על הארגון
• search_meetings(query, speaker_name) → חיפוש בתמלולי פגישות קודמות
• search_notebook(query) → חיפוש בניתוחי NotebookLM מעמיקים (החלטות, משימות, ציטוטים, נושאים)
• search_flights(destination, max_price_eur, date_from, date_to, nights_from, nights_to) → חיפוש טיסות ישירות הלוך-חזור מת״א

══════════════════════════════════════════════════════
14. 📓 ניתוחי NotebookLM: כשהמשתמש מבקש תובנות מעמיקות, החלטות, משימות, או ציטוטים מפגישות — השתמש ב-search_notebook.
   זה מחפש בניתוחים מובנים שכוללים: תמצית מנהלים, נושאים מרכזיים, פריטי פעולה, החלטות, ציטוטים, ופרופילי דוברים.
   אם search_notebook לא מוצא — נסה search_meetings כגיבוי.
   דוגמאות: "מה ההחלטות שהתקבלו?", "אילו משימות נקבעו?", "מה היו הנושאים המרכזיים?", "תן לי ציטוטים חשובים"

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

    def _build_profile_block(self) -> str:
        """Build the user profile context block for the system instruction.
        
        Dumps the ENTIRE profile as structured JSON so Gemini can see ALL fields,
        including children names, spouse, family details, voice_map, etc.
        Nothing is skipped except chat_history (too large).
        """
        if not self._user_profile:
            return ""

        # Create a filtered copy — exclude chat_history (too large for context)
        profile_for_prompt = {
            k: v for k, v in self._user_profile.items()
            if k != "chat_history" and v  # skip empty values
        }

        if not profile_for_prompt:
            return ""

        profile_json = json.dumps(profile_for_prompt, ensure_ascii=False, indent=2)

        block = f"""══════════════════════════════════════════════════════
פרופיל אישי של המשתמש (הבעלים של המערכת):
══════════════════════════════════════════════════════
{profile_json}
══════════════════════════════════════════════════════
🔴 חשוב מאוד: כל מה שמופיע למעלה הוא מידע אישי על המשתמש.
כשהוא שואל 'מה שמות הילדים שלי?', 'איך קוראים לאשתי?', או כל שאלה אישית —
ענה אך ורק מהנתונים למעלה. אם שם ילד, בן/בת זוג, או כל פרט אחר מופיע כאן — ציין אותו.
"""
        
        print(f"📋 [Profile Block] Built profile: {len(profile_json)} chars, keys: {list(profile_for_prompt.keys())}")
        
        return block

    def inject_session_context(self, phone: str, summary: str, speakers: list,
                                segments: list = None, expert_analysis: str = ""):
        """
        Phase 3: Inject the latest audio session as Working Memory.
        
        Called after audio processing completes. The context is injected
        into the user's next chat interaction as a synthetic history entry,
        so Gemini can reference it when the user asks "what did we talk about?".
        """
        self._working_memory[phone] = {
            "summary": summary,
            "speakers": speakers,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "segment_count": len(segments) if segments else 0,
            "expert_analysis_snippet": expert_analysis[:500] if expert_analysis else "",
        }
        print(f"💾 [ConvEngine] Working memory injected for {phone[-4:]}: {len(summary)} chars, {len(speakers)} speakers")

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

            # Phase 3: Inject Working Memory if available
            # This adds the latest audio session as a synthetic history entry
            if phone in self._working_memory:
                wm = self._working_memory.pop(phone)
                wm_text = f"[סיכום הקלטה אחרונה ({wm.get('timestamp', '')})]\n"
                wm_text += f"דוברים: {', '.join(wm.get('speakers', []))}\n"
                wm_text += f"סיכום: {wm.get('summary', '')}\n"
                if wm.get('expert_analysis_snippet'):
                    wm_text += f"ניתוח: {wm['expert_analysis_snippet']}\n"

                try:
                    # Inject as a synthetic user-model exchange in history
                    chat.history.append(
                        genai.protos.Content(
                            role="user",
                            parts=[genai.protos.Part(text="[SYSTEM: הקלטה חדשה עובדה ונשמרה]")]
                        )
                    )
                    chat.history.append(
                        genai.protos.Content(
                            role="model",
                            parts=[genai.protos.Part(text=wm_text)]
                        )
                    )
                    print(f"   💾 Injected working memory ({len(wm.get('speakers', []))} speakers)")
                except Exception as wm_err:
                    print(f"   ⚠️ Working memory injection failed: {wm_err}")

            print(f"{'='*60}")

            # Inject current date/time context into every message
            # (system instruction date may be stale if server has been running for days)
            from datetime import datetime as _dt_now
            _now_msg = _dt_now.now()
            _days_he = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
            _date_context = f"[📅 היום: {_days_he[_now_msg.weekday()]}, {_now_msg.strftime('%d/%m/%Y %H:%M')}]\n"
            enriched_message = _date_context + message

            # ── Always-on entity context (replaces hardcoded pronoun detection) ──
            # Best practice: instead of trying to detect specific pronouns (brittle,
            # requires hardcoding every Hebrew suffix form like אליו, ממנו, אצלה...),
            # we ALWAYS inject the last-discussed entity as a lightweight context hint.
            # Gemini naturally resolves pronouns, implicit references, and anaphora
            # from the chat history + this hint — no regex or word lists needed.
            try:
                from app.services.identity_resolver_service import identity_resolver
                last_entity = identity_resolver.get_last_entity(phone)
                if last_entity:
                    entity_name = last_entity.get("canonical_name", "")
                    hebrew_name = last_entity.get("hebrew_name", "") or last_entity.get("name", "")
                    display = hebrew_name or entity_name
                    if entity_name:
                        enriched_message = _date_context + f"[הקשר אחרון: {display} ({entity_name})]\n{message}"
                        print(f"   🔗 Entity context: {display} ({entity_name})")
            except Exception as ctx_err:
                print(f"   ⚠️ Entity context injection failed: {ctx_err}")

            # Send message to Gemini
            response = chat.send_message(enriched_message)

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

                    # ── Track last-mentioned person for pronoun resolution ──
                    if fn_name == "search_person":
                        try:
                            from app.services.identity_resolver_service import identity_resolver
                            parsed = json.loads(result_str)
                            results = parsed.get("results", [])
                            if len(results) == 1:
                                # Exact match — track this person
                                person = results[0]
                                identity_resolver.update_context(
                                    phone=phone,
                                    department=person.get("department", ""),
                                    manager=person.get("reports_to", ""),
                                    entity=person,
                                )
                                print(f"      🎯 Tracking entity: {person.get('canonical_name', '?')}")
                            elif results:
                                # Multiple results — track the first (most likely)
                                person = results[0]
                                identity_resolver.update_context(
                                    phone=phone,
                                    entity=person,
                                )
                                print(f"      🎯 Tracking entity (first of {len(results)}): {person.get('canonical_name', '?')}")
                        except Exception:
                            pass

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
        """Reload KB context into system instruction (e.g., after KB update).
        
        IMPORTANT: Does NOT clear existing sessions. Active chat sessions
        keep their history intact. New sessions will use the updated KB data.
        Only the model template is rebuilt — existing ChatSession objects
        continue working with their accumulated context.
        """
        from app.services.model_discovery import configure_genai, MODEL_MAPPING
        from app.services.knowledge_base_service import get_system_instruction_block

        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return

        configure_genai(api_key)

        # Rebuild the system instruction with fresh KB data
        kb_block = get_system_instruction_block()
        profile_block = self._build_profile_block()

        old_len = len(self._kb_system_instruction)

        self._kb_system_instruction = f"""אתה עוזר ארגוני מקצועי בשם "Second Brain".
אתה עונה בעברית אלא אם נשאלת באנגלית.
יש לך גישה לכלים (functions) שמאפשרים לך לחפש, לעדכן ולהיזכר במידע.

{profile_block}

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
   🔴 חשוב: אם המשתמש שואל על עצמו (ילדים, משפחה, העדפות) — קודם בדוק את הפרופיל האישי למעלה לפני שעונה.
5. הקשר שיחה וכינויים: כשהמשתמש מתייחס למישהו — בין אם דרך כינויי גוף (שלו, שלה, אליו, אותו, ממנו, איתו, בו, אצלו...), בין אם דרך ביטויים עקיפים ("מי מדווח אליו?", "מה הביצועים?"), ובין אם בכל דרך אחרת — הסתכל בהיסטוריית השיחה וברמז [הקשר אחרון:] שמופיע בתחילת ההודעה, ותבין למי הוא מתכוון. אל תשאל אלא אם באמת אי אפשר לדעת.
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
12. 📼 כשהמשתמש מבקש "הכנה לשיחה עם X", "על מה דיברנו עם X?", "מתי דיברתי עם X?" — השתמש בכלי search_meetings כדי למצוא שיחות קודמות.
   שלב את הנתונים מהפגישות עם המידע מבסיס הידע (search_person) כדי לתת הכנה מקיפה.
   דוגמה: "הכן אותי לשיחה עם יובל" → search_person("יובל") + search_meetings(query="יובל", speaker_name="Yuval") → שלב הכל לתשובה אחת.

══════════════════════════════════════════════════════
כלים (Tools) — אל תקרא להם בשמם בפני המשתמש:
══════════════════════════════════════════════════════
• search_person(name) → חיפוש אדם לפי שם (עברית/אנגלית, מלא/חלקי)
• get_reports(manager_name) → כל הכפופים למנהל (ישירים + עקיפים)
• save_fact(person_name, field, value) → שמירת עובדה (עבודה או משפחה) לבסיס הידע
• list_org_stats() → סטטיסטיקות כלליות על הארגון
• search_meetings(query, speaker_name) → חיפוש בתמלולי פגישות קודמות
• search_notebook(query) → חיפוש בניתוחי NotebookLM מעמיקים (החלטות, משימות, ציטוטים, נושאים)

══════════════════════════════════════════════════════
זרימת עדכון מידע — save_fact:
══════════════════════════════════════════════════════
כשהמשתמש אומר עובדה חדשה (כמו "לבן הזוג של חן קוראים עודד"):
1. תחילה, קרא ל-search_person כדי לזהות את השם המלא באנגלית
2. אחר כך, קרא ל-save_fact עם השם המלא, השדה, והערך
3. אשר למשתמש: "שמרתי ✅ — בן הזוג של חן הוא עודד"
4. מעכשיו, כשישאלו "איך קוראים לבן הזוג של חן?" — תדע לענות "עודד"

{kb_block}"""

        # Rebuild the model with updated system instruction
        tools = genai.protos.Tool(function_declarations=_TOOL_DECLARATIONS)
        try:
            self._model = genai.GenerativeModel(
                model_name=self._model_name,
                tools=[tools],
                system_instruction=self._kb_system_instruction,
            )
            active_sessions = len(self._sessions)
            print(f"🔄 [ConvEngine] System instruction refreshed ({old_len}→{len(self._kb_system_instruction)} chars)")
            print(f"   ✅ {active_sessions} active sessions PRESERVED (not cleared)")
        except Exception as e:
            print(f"❌ [ConvEngine] Refresh failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════
conversation_engine = ConversationEngine()
