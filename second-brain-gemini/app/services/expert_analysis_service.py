"""
Expert Analysis Service - Council of Experts for Meeting Analysis

This service applies expert personas to analyze transcribed conversations:
- Michal Dalyot / Adler Institute (Parenting/Boundaries)
- Esther Perel (Relationships/Communication)
- McKinsey & Co. / Israeli Tech (Business/Strategy)
- Simon Sinek (Leadership/The Why)

Flow:
1. Context Detection - Gemini categorizes the conversation
2. Expert Assignment - 1-2 most relevant personas assigned
3. Deep Analysis - Who said what, sentiment, insights
4. Mandatory Kaizen - Preserve/Improve feedback

Each persona provides:
- Sentiment analysis
- Executive summary (deep attribution)
- Expert insights from assigned persona(s)
- Action items (assigned to specific speakers)
- Mandatory Kaizen Feedback (לשימור / לשיפור)
"""

# ============================================================================
# DIRECT AUDIO ANALYSIS PROMPT
# This is the proven prompt from process_meetings.py that works reliably
# for Drive Inbox uploads. We use it for WhatsApp audio as well.
# ============================================================================
DIRECT_AUDIO_SYSTEM_INSTRUCTION = """You are an expert AI assistant with access to multiple expert personas. Listen to the attached audio meeting and generate a Hebrew summary using a sophisticated Multi-Agent System.

Step 1: CONTEXT & SPEAKER IDENTIFICATION

First, identify the speakers. Specifically look for:
- Itzik (Me)
- Eran (Husband/Partner)

Then, classify the conversation context:

If the conversation is between Itzik and Eran about their relationship, feelings, or shared life -> Flag as COUPLE_DYNAMICS (unless they explicitly talk about kids only).

If the conversation is about raising children/home logistics -> Flag as PARENTING.

If the conversation is about team culture/leadership/mentoring -> Flag as LEADERSHIP.

If the conversation is about business strategy, product decisions, or roadmap -> Flag as STRATEGY.

Step 2: SELECT THE EXPERT PERSONA

Based on the flag, adopt a specific mental framework for the analysis:

RELATIONSHIP (Esther Perel Mode):
- Trigger: Discussions between Itzik & Eran about their relationship, feelings, or shared life.
- Focus: Emotional intelligence, balance between security and freedom, listening to the "unsaid", reconciling desire with domestic life.
- Tone: Empathetic, insightful, deep.

STRATEGY (McKinsey + Tech Innovation Mode):
- Trigger: Business decisions, product roadmap, tech strategy.
- Focus: "MECE" (Mutually Exclusive, Collectively Exhaustive) structure, data-driven insights, scalability, combined with Agile/Lean Startup thinking (MVP, iteration, speed).
- Tone: Sharp, professional, action-oriented, cutting through the noise.

LEADERSHIP (Simon Sinek Mode):
- Trigger: Team management, hiring, mentoring, culture.
- Focus: "Start with Why", The Infinite Game, creating a Circle of Safety, leaders eat last.
- Tone: Inspiring, human-centric, visionary.

PARENTING (Adler Institute Mode):
- Trigger: Kids, education, home rules.
- Focus: Encouragement, natural consequences, cooperation, avoiding power struggles.
- Tone: Supportive, practical, educational.

Step 3: GENERATE THE HEBREW OUTPUT

Structure the response strictly as follows (add relevant emojis):

🧠 הכובע שנבחר: [Name of the Expert/Mode used - e.g., "אסתר פרל (יחסים)", "מקינזי + Tech Innovation (אסטרטגיה)", "סיימון סינק (מנהיגות)", "מכון אדלר (הורות)"]

📌 נושא השיחה: [Concise Subject - 3-5 words]

🕵️ הסאב-טקסט (ניתוח עומק): [2-3 sentences analyzing NOT just what was said, but the underlying dynamics/principles based on the chosen expert persona. Go deep into what's really happening beneath the surface.]

💡 תובנה מרכזית (The Insight): [The single most valuable takeaway using the expert's specific terminology and framework. This should be the "aha moment" that the expert would highlight.]

⚖️ מדד הבהירות / טיב היחסים: 
[If Strategy: Rate clarity of decision 1-10 with brief explanation]
[If Relationship: Rate quality of communication 1-10 with brief explanation]
[If Leadership: Rate effectiveness of leadership approach 1-10 with brief explanation]
[If Parenting: Rate quality of parenting approach 1-10 with brief explanation]

✅ אקשן אייטמס (תכלס):
[Task 1 - specific and actionable]
[Task 2 - specific and actionable]
(Or "אין משימות להמשך" if no action items)

📈 קאיזן - פידבק לצמיחה:
✓ לשימור: [One specific positive behavior/decision to preserve]
→ לשיפור: [One MANDATORY area for growth - always find something]

❓ שאלה למחשבה (Reflection): [One provocative/hard question that the expert would ask to help grow. This should challenge assumptions and encourage deeper thinking.]

CRITICAL: The entire output must be in Hebrew. Use the expert's specific terminology and framework throughout. Be insightful, not just descriptive. Keep the total response under 1500 characters for WhatsApp compatibility.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

import google.generativeai as genai

from app.core.config import settings
from app.services.knowledge_base_service import get_system_instruction_block as get_kb_context

logger = logging.getLogger(__name__)

# Israel timezone offset (UTC+2 winter, UTC+3 summer)
ISRAEL_TZ_OFFSET = timedelta(hours=2)


def get_israel_time() -> datetime:
    """Get current time in Israel timezone."""
    utc_now = datetime.now(timezone.utc)
    return utc_now + ISRAEL_TZ_OFFSET


# Council of Experts - Persona Definitions
EXPERT_PERSONAS = {
    "parenting": {
        "name": "מיכל דליות / מכון אדלר (הורות וגבולות)",
        "short_name": "מכון אדלר",
        "category": "Parenting",
        "trigger_keywords": [
            "ילדים", "בנים", "בנות", "בית", "חינוך", "מטלות", "שיעורי בית",
            "kids", "children", "הורים", "משפחה", "גבולות", "כללים",
            "ילד", "ילדה", "בן", "בת", "התנהגות", "משמעת", "הורות",
            "גן", "בית ספר", "מורה", "טיפול", "חומה", "לילה", "שינה",
            "אוכל", "סלולר", "מסכים", "יחד", "אחים", "אחיות"
        ],
        "focus": """
גישת אדלר להורות דמוקרטית:
- עידוד במקום שבח (Encouragement vs Praise)
- תוצאות טבעיות והגיוניות (Natural & Logical Consequences)
- שיתוף פעולה ואחריות משותפת
- הימנעות ממאבקי כוח
- כבוד הדדי וגבולות ברורים
- מתן בחירות במסגרת גבולות
- זיהוי "מטרות מוטעות" בהתנהגות
""",
        "tone": "תומך, פרקטי, חינוכי, ללא שיפוטיות",
        "key_questions": [
            "האם השיחה משתמשת בשפה מעודדת או בביקורת?",
            "האם יש מאבקי כוח נסתרים?",
            "האם הגבולות שהוגדרו ברורים וטבעיים?"
        ]
    },
    "relationship": {
        "name": "אסתר פרל (יחסים ותקשורת)",
        "short_name": "אסתר פרל",
        "category": "Relationship",
        "trigger_keywords": [
            "בעל", "אישה", "זוגיות", "רגשות", "אהבה", "relationship", "partner",
            "ערן", "זוג", "כעס", "תסכול", "אינטימיות", "קשר", "חיבור",
            "ריב", "ויכוח", "לא מבין", "לא מבינה", "מרחק", "קרבה",
            "חופשה", "זוגי", "ביחד", "נישואין", "שותפות", "תמיכה"
        ],
        "focus": """
גישת אסתר פרל לזוגיות:
- אינטליגנציה רגשית עמוקה
- איזון בין ביטחון (Security) לחופש (Freedom)
- הקשבה ל"לא נאמר" - מה בין השורות
- הבנת דינמיקות כוח נסתרות
- פישור בין תשוקה לחיי יום-יום
- זיהוי דפוסים חוזרים בתקשורת
- הערכת "סגנונות התקשרות" (Attachment Styles)
""",
        "tone": "אמפתי, עמוק, תובנתי, ללא שיפוט",
        "key_questions": [
            "מה לא נאמר בשיחה?",
            "איזה רגש נסתר מתחת לפני השטח?",
            "האם יש דפוס חוזר שראוי לשים לב אליו?"
        ]
    },
    "strategy": {
        "name": "מקינזי וטק ישראלי (אסטרטגיה ועסקים)",
        "short_name": "מקינזי + Tech",
        "category": "Business",
        "trigger_keywords": [
            "עסק", "מוצר", "לקוחות", "אסטרטגיה", "roadmap", "MVP", "startup",
            "product", "כסף", "תקציב", "הכנסות", "מכירות", "שוק", "מתחרים",
            "פיצ'ר", "פיתוח", "tech", "קוד", "משקיעים", "גיוס", "חברה",
            "עסקים", "פרויקט", "דדליין", "יעדים", "KPI", "OKR", "ביצועים",
            "תכנון", "אפליקציה", "אתר", "שירות", "B2B", "B2C", "SaaS"
        ],
        "focus": """
גישת מקינזי + High-Tech ישראלי:
- מבנה MECE (Mutually Exclusive, Collectively Exhaustive)
- ניתוח מבוסס נתונים (Data-Driven)
- סקיילביליות ויעילות
- חשיבת Agile/Lean Startup
- MVP ואיטרציות מהירות
- הגדרת KPIs ברורים
- תעדוף אכזרי (Ruthless Prioritization)
- "First Principles Thinking"
""",
        "tone": "חד, מקצועי, ממוקד פעולה, חותך לעניין",
        "key_questions": [
            "מה ה-ROI הצפוי?",
            "מה הצעד הבא הקטן ביותר שמביא ערך?",
            "מה ה-bottleneck האמיתי?"
        ]
    },
    "leadership": {
        "name": "סיימון סינק (מנהיגות והשראה)",
        "short_name": "סיימון סינק",
        "category": "Leadership",
        "trigger_keywords": [
            "צוות", "עובדים", "מנהל", "חברה", "תרבות", "hiring", "mentoring",
            "culture", "מנהיגות", "השראה", "ערכים", "חזון", "משמעות",
            "מוטיבציה", "גיוס", "פיטורים", "ביצועים", "משוב", "feedback",
            "1on1", "אחד על אחד", "צמיחה", "קריירה", "פוטנציאל"
        ],
        "focus": """
גישת סיימון סינק למנהיגות:
- Start with Why - תתחיל מה"למה"
- The Infinite Game - משחק אינסופי, לא ניצחון חד פעמי
- Circle of Safety - יצירת מעגל ביטחון לצוות
- Leaders Eat Last - מנהיג דואג קודם לאחרים
- מנהיגות משרתת (Servant Leadership)
- בניית אמון לטווח ארוך
- "Optimism fueled by reality"
""",
        "tone": "מעורר השראה, ממוקד באנשים, חזוני, אנושי",
        "key_questions": [
            "מה ה'למה' מאחורי ההחלטה?",
            "האם זה בונה אמון לטווח ארוך?",
            "האם המנהיגות כאן משרתת או שולטת?"
        ]
    },
    "general": {
        "name": "עוזר אישי חכם",
        "short_name": "עוזר אישי",
        "category": "General",
        "trigger_keywords": [],
        "focus": "סיכום ברור ותמציתי עם תובנות פרקטיות ואקשן אייטמס",
        "tone": "ישיר, שימושי, פרקטי",
        "key_questions": ["מה הנקודות העיקריות?", "מה הצעד הבא?"]
    }
}


class ExpertAnalysisService:
    """
    Council of Experts Analysis System for meeting transcripts.
    
    Flow:
    1. Context Detection - Ask Gemini to categorize the transcript
    2. Expert Assignment - Select 1-2 relevant personas
    3. Deep Analysis - Full analysis with attribution
    4. Mandatory Kaizen - Preserve/Improve feedback
    """
    
    def __init__(self):
        self.api_key = settings.google_api_key
        self.model = None
        self.model_name = None
        
        if self.api_key:
            from app.services.model_discovery import configure_genai, get_best_model, MODEL_MAPPING
            configure_genai(self.api_key)
            
            model_name = get_best_model(MODEL_MAPPING["pro"], category="general")
            if model_name:
                self.model = genai.GenerativeModel(model_name)
                self.model_name = model_name
                logger.info(f"✅ שירות ניתוח המומחים אותחל עם {model_name}")
                print(f"✅ [Expert Analysis] Model initialized: {model_name}")
            else:
                logger.error("❌ No model found for Expert Analysis service")
                print("❌ [Expert Analysis] No model found via discovery")
            
            if not self.model:
                logger.error("❌ לא הצלחתי לאתחל אף מודל")
                print("❌ [Expert Analysis] All models failed to initialize!")
        else:
            logger.warning("⚠️  מפתח Google API לא מוגדר - ניתוח מומחים מושבת")
        
        self.is_configured = bool(self.api_key and self.model)
    
    def _build_transcript_text(self, segments: List[Dict], voice_map: Dict) -> Tuple[str, List[str]]:
        """
        Build readable transcript with speaker names resolved.
        Returns (transcript_text, list_of_speakers).
        """
        transcript_lines = []
        speakers_set = set()
        
        for seg in segments:
            speaker_id = seg.get("speaker", "דובר לא מזוהה")
            # Replace speaker ID with name if known
            speaker_name = voice_map.get(speaker_id.lower(), speaker_id)
            if speaker_name == speaker_id:
                # Try without case sensitivity
                for key, value in voice_map.items():
                    if key.lower() == speaker_id.lower():
                        speaker_name = value
                        break
            
            speakers_set.add(speaker_name)
            text = seg.get("text", "")
            transcript_lines.append(f"**{speaker_name}**: {text}")
        
        return "\n".join(transcript_lines), list(speakers_set)
    
    async def detect_context(self, transcript_text: str) -> Dict[str, Any]:
        """
        Step 1: Use Gemini to categorize the conversation.
        
        Returns:
            {
                "primary_category": "Business|Parenting|Relationship|Leadership|General",
                "secondary_category": "..." (optional),
                "confidence": 0.0-1.0,
                "reasoning": "..."
            }
        """
        if not self.is_configured:
            return {"primary_category": "General", "confidence": 0.5, "reasoning": "Model not configured"}
        
        detection_prompt = f"""אתה מומחה לניתוח שיחות. קטגר את השיחה הבאה לאחת מהקטגוריות:

1. **Parenting** - שיחות על ילדים, חינוך, משפחה, גבולות בבית
2. **Relationship** - שיחות על זוגיות, יחסים, רגשות בין בני זוג
3. **Business** - שיחות על עסקים, טכנולוגיה, פרויקטים, כסף, סטארטאפ
4. **Leadership** - שיחות על ניהול צוות, תרבות ארגונית, מנטורינג
5. **General** - שיחות כלליות שלא מתאימות לאף קטגוריה ספציפית

**תמליל השיחה:**
{transcript_text[:3000]}

**החזר תשובה בפורמט JSON בלבד:**
{{
    "primary_category": "קטגוריה ראשית",
    "secondary_category": "קטגוריה משנית או null",
    "confidence": 0.8,
    "reasoning": "הסבר קצר"
}}
"""
        
        try:
            print(f"🔍 [Context Detection] Calling Gemini model: {self.model_name}")
            response = self.model.generate_content(
                detection_prompt,
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 500
                }
            )
            
            # Safe extraction of response.text
            try:
                response_text = response.text.strip() if response.text else ""
            except (ValueError, AttributeError) as text_err:
                print(f"   ⚠️ response.text access failed: {text_err}")
                return self._fallback_context_detection(transcript_text)
            
            print(f"🔍 [Context Detection] Response received: {len(response_text)} chars")
            # Extract JSON from possible markdown code block
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            print(f"🎯 [Context Detection] Primary: {result.get('primary_category')}, Secondary: {result.get('secondary_category')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Context detection failed: {e}")
            # Fallback to keyword-based detection
            return self._fallback_context_detection(transcript_text)
    
    def _fallback_context_detection(self, transcript_text: str) -> Dict[str, Any]:
        """Fallback to keyword-based detection if Gemini fails."""
        text_lower = transcript_text.lower()
        
        scores = {}
        for persona_key, persona in EXPERT_PERSONAS.items():
            if persona_key == "general":
                continue
            score = sum(1 for kw in persona["trigger_keywords"] if kw in text_lower)
            scores[persona_key] = score
        
        if not scores or max(scores.values()) == 0:
            return {"primary_category": "General", "confidence": 0.3, "reasoning": "No keywords matched"}
        
        # Map persona keys to categories
        category_map = {
            "parenting": "Parenting",
            "relationship": "Relationship",
            "strategy": "Business",
            "leadership": "Leadership"
        }
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_scores[0]
        secondary = sorted_scores[1] if len(sorted_scores) > 1 and sorted_scores[1][1] > 0 else None
        
        return {
            "primary_category": category_map.get(primary[0], "General"),
            "secondary_category": category_map.get(secondary[0], None) if secondary else None,
            "confidence": min(1.0, primary[1] / 10),
            "reasoning": f"Keyword match: {primary[1]} for {primary[0]}"
        }
    
    def _get_personas_for_context(self, context: Dict[str, Any]) -> List[str]:
        """
        Map context categories to 1-2 persona keys.
        
        Routing:
        - Business/Tech → McKinsey + Sinek (if leadership)
        - Parenting → Adler
        - Relationship → Esther Perel
        """
        category_to_persona = {
            "Parenting": "parenting",
            "Relationship": "relationship",
            "Business": "strategy",
            "Leadership": "leadership",
            "General": "general"
        }
        
        personas = []
        
        primary = context.get("primary_category", "General")
        if primary in category_to_persona:
            personas.append(category_to_persona[primary])
        
        # Add secondary persona if relevant and different
        secondary = context.get("secondary_category")
        if secondary and secondary in category_to_persona:
            secondary_persona = category_to_persona[secondary]
            if secondary_persona not in personas:
                # Only allow related combinations
                allowed_combos = [
                    ("strategy", "leadership"),
                    ("leadership", "strategy"),
                    ("parenting", "relationship"),
                    ("relationship", "parenting"),
                ]
                if (personas[0] if personas else None, secondary_persona) in allowed_combos:
                    personas.append(secondary_persona)
        
        # Ensure at least one persona
        if not personas:
            personas.append("general")
        
        print(f"🎯 [Persona Routing] Category '{primary}' -> Personas: {personas}")
        
        return personas[:2]  # Max 2 personas
    
    def build_expert_prompt(
        self, 
        persona_keys: List[str], 
        transcript_text: str, 
        speakers: List[str],
        context: Dict[str, Any]
    ) -> str:
        """
        Build deep analysis prompt with Expert Council structure.
        Balanced between depth and WhatsApp length limits.
        """
        # Get persona details
        personas = [EXPERT_PERSONAS.get(pk, EXPERT_PERSONAS["general"]) for pk in persona_keys]
        israel_time = get_israel_time()
        speakers_str = ", ".join(speakers) if speakers else "לא זוהו דוברים"
        
        # Truncate transcript for prompt efficiency
        if len(transcript_text) > 3500:
            transcript_text = transcript_text[:3500] + "\n...(קוצר)"
        
        # Build persona section
        if len(personas) == 1:
            persona_section = f"**הפרסונה שלך:** {personas[0]['name']}\n**גישה:** {personas[0]['tone']}"
        else:
            persona_section = f"**הפרסונות שלך:** {personas[0]['name']} + {personas[1]['name']}"
        
        # Inject knowledge base context if available
        kb_block = ""
        try:
            kb_context = get_kb_context()
            if kb_context:
                kb_block = f"\n{kb_context}\n"
        except Exception:
            pass
        
        prompt = f"""אתה חבר במועצת המומחים של "המוח השני".
{kb_block}
{persona_section}

**משתתפים:** {speakers_str}
**זמן:** {israel_time.strftime('%d/%m/%Y %H:%M')} (שעון ישראל)
**קטגוריה:** {context.get('primary_category', 'כללי')}

**תמליל:**
{transcript_text}

---

**הנחיות:**
1. כתוב בעברית בלבד
2. השתמש בשמות הדוברים (לא "דובר 1")
3. כשיש מילים באנגלית, התחל את המשפט בעברית
4. **מגבלת אורך: סה"כ עד 800 תווים!**

---

**פורמט (תמציתי!):**

🎭 **סנטימנט:** [חיובי/מעורב/מתוח] - [משפט קצר]

📋 **תמצית:**
• [מי אמר מה - נקודה 1]
• [מי אמר מה - נקודה 2]
• [החלטה/מסקנה]

🔍 **תובנת {personas[0]['short_name']}:**
[2 משפטים עם תובנה עמוקה - מה קורה מתחת לפני השטח?]

✅ **משימות:**
• *[שם]*: [משימה]
(אם אין: "לא זוהו משימות")

📈 **קאיזן:**
✓ לשימור: [התנהגות חיובית ספציפית]
→ לשיפור: [הזדמנות לצמיחה + המלצה]
"""
        return prompt
    
    async def analyze_transcript(
        self,
        segments: List[Dict],
        voice_map: Optional[Dict] = None,
        force_persona: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform full expert analysis on a transcript with Kaizen feedback.
        
        Flow:
        1. Build transcript text with resolved speaker names
        2. Detect context (category) using Gemini
        3. Assign 1-2 expert personas
        4. Run comprehensive analysis
        
        Args:
            segments: List of transcript segments
            voice_map: Optional mapping of speaker IDs to names
            force_persona: Optional - force a specific persona
            
        Returns:
            Dict with analysis results including Kaizen feedback
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "שירות ניתוח המומחים לא מוגדר"
            }
        
        if not segments:
            return {
                "success": False,
                "error": "אין קטעי תמלול לניתוח"
            }
        
        voice_map = voice_map or {}
        
        # Step 1: Build transcript text
        transcript_text, speakers = self._build_transcript_text(segments, voice_map)
        print(f"📝 [Expert Analysis] Transcript: {len(transcript_text)} chars, {len(speakers)} speakers")
        
        # Step 2: Detect context
        print("🔍 [Expert Analysis] Step 1/3: Detecting context...")
        context = await self.detect_context(transcript_text)
        
        # Step 3: Assign personas
        if force_persona and force_persona in EXPERT_PERSONAS:
            persona_keys = [force_persona]
            print(f"🎭 [Expert Analysis] Forced persona: {force_persona}")
        else:
            persona_keys = self._get_personas_for_context(context)
            print(f"🎭 [Expert Analysis] Step 2/3: Assigned personas: {persona_keys}")
        
        personas = [EXPERT_PERSONAS[pk] for pk in persona_keys]
        persona_names = [p["name"] for p in personas]
        
        # Step 4: Build and run analysis with RETRY logic
        print(f"🧠 [Expert Analysis] Step 3/3: Running deep analysis with model: {self.model_name}")
        prompt = self.build_expert_prompt(persona_keys, transcript_text, speakers, context)
        print(f"📝 [Expert Analysis] Prompt length: {len(prompt)} chars")
        
        analysis_text = ""
        max_retries = 3  # Increased to 3 attempts
        
        for attempt in range(max_retries):
            try:
                print(f"\n   {'='*40}")
                print(f"   🔄 ATTEMPT {attempt + 1}/{max_retries}")
                print(f"   {'='*40}")
                
                # Use progressively simpler prompts
                if attempt == 0:
                    current_prompt = prompt
                    print(f"   📋 Using: FULL expert prompt")
                elif attempt == 1:
                    current_prompt = self._build_fallback_prompt(transcript_text, speakers)
                    print(f"   📋 Using: FALLBACK prompt")
                else:
                    # Ultra-simple prompt for third attempt
                    current_prompt = self._build_minimal_prompt(transcript_text, speakers)
                    print(f"   📋 Using: MINIMAL prompt")
                
                print(f"   📊 Model: {self.model_name}")
                print(f"   📊 Prompt length: {len(current_prompt)} chars")
                print(f"   📊 Prompt preview: {current_prompt[:200]}...")
                
                # Add safety settings to allow more content
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                response = self.model.generate_content(
                    current_prompt,
                    generation_config={
                        'temperature': 0.3 if attempt > 0 else 0.4,
                        'max_output_tokens': 1000
                    },
                    safety_settings=safety_settings
                )
                
                # Debug: Check response structure
                print(f"   📊 Response received")
                if hasattr(response, 'candidates') and response.candidates:
                    print(f"   📊 Candidates: {len(response.candidates)}")
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        print(f"   📊 Finish reason: {candidate.finish_reason}")
                    if candidate.content and candidate.content.parts:
                        print(f"   📊 Parts: {len(candidate.content.parts)}")
                else:
                    print(f"   ⚠️ No candidates!")
                    if hasattr(response, 'prompt_feedback'):
                        print(f"   📊 Prompt feedback: {response.prompt_feedback}")
                
                # Safe extraction of response.text
                try:
                    analysis_text = response.text.strip() if response.text else ""
                    print(f"   ✅ Got text: {len(analysis_text)} chars")
                except (ValueError, AttributeError) as text_err:
                    print(f"   ⚠️ response.text failed: {text_err}")
                    # Try to extract from candidates directly
                    if hasattr(response, 'candidates') and response.candidates:
                        try:
                            parts = response.candidates[0].content.parts
                            analysis_text = "".join(p.text for p in parts if hasattr(p, 'text'))
                            print(f"   ✅ Extracted from candidates: {len(analysis_text)} chars")
                        except Exception as extract_err:
                            print(f"   ⚠️ Candidates extraction failed: {extract_err}")
                            analysis_text = ""
                    else:
                        analysis_text = ""
                
                print(f"   📝 Final text: {len(analysis_text)} chars")
                
                # Check for empty response
                if len(analysis_text.strip()) < 50:
                    print(f"   ⚠️  Response too short ({len(analysis_text)} chars)")
                    print(f"   ⚠️  Content: '{analysis_text[:100]}'" if analysis_text else "   ⚠️  Content: EMPTY")
                    print(f"   🔄 Retrying with simpler prompt...")
                    continue
                
                # SUCCESS - break out of retry loop
                print(f"   ✅ SUCCESS! Got {len(analysis_text)} chars")
                break
                
            except Exception as e:
                print(f"   ❌ EXCEPTION in attempt {attempt + 1}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                if attempt == max_retries - 1:
                    error_msg = f"Exception: {type(e).__name__}: {str(e)[:50]}"
                    logger.error(f"❌ [CRITICAL] ניתוח מומחה נכשל לאחר {max_retries} נסיונות: {e}")
                    # Record error for system health reporting
                    try:
                        from app.services.architecture_audit_service import architecture_audit_service
                        architecture_audit_service.record_expert_error(error_msg)
                    except:
                        pass
        
        # Final validation
        if not analysis_text or len(analysis_text.strip()) < 50:
            print("❌ [CRITICAL] Analysis returned EMPTY after all retries!")
            logger.error("❌ [CRITICAL] Expert analysis returned empty text")
            error_msg = "ניתוח חזר ריק - בדוק את המודל"
            
            # Record error for system health reporting
            try:
                from app.services.architecture_audit_service import architecture_audit_service
                architecture_audit_service.record_expert_error(error_msg)
            except:
                pass
            
            return {
                "success": False,
                "error": error_msg,
                "persona": " + ".join(persona_names),
                "model_used": self.model_name
            }
        
        print(f"✅ [Expert Analysis] SUCCESS - {len(analysis_text)} chars")
        israel_time = get_israel_time()
        
        # Clear any recorded errors on success
        try:
            from app.services.architecture_audit_service import architecture_audit_service
            architecture_audit_service.clear_expert_error()
        except:
            pass
        
        return {
            "success": True,
            "persona": " + ".join(persona_names),
            "persona_keys": persona_keys,
            "context": context,
            "speakers": speakers,
            "raw_analysis": analysis_text,
            "timestamp": israel_time.isoformat(),
            "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M')
        }
    
    def _build_fallback_prompt(self, transcript_text: str, speakers: List[str]) -> str:
        """Simple fallback prompt when main prompt fails."""
        speakers_str = ", ".join(speakers) if speakers else "דוברים לא ידועים"
        
        return f"""סכם את השיחה הבאה בעברית.

**משתתפים:** {speakers_str}

**תמליל:**
{transcript_text[:3000]}

**תשובה בפורמט הבא:**

🎯 סנטימנט: [חיובי/שלילי/מעורב]

📋 תמצית:
• [מי אמר מה - נקודה 1]
• [מי אמר מה - נקודה 2]

✅ משימות:
• [שם]: [משימה]

📈 קאיזן:
✓ לשימור: [נקודה חיובית]
→ לשיפור: [הזדמנות לצמיחה]
"""
    
    def _build_minimal_prompt(self, transcript_text: str, speakers: List[str]) -> str:
        """Ultra-simple prompt for last resort attempt."""
        speakers_str = ", ".join(speakers) if speakers else "דוברים"
        
        # Very short transcript sample
        short_transcript = transcript_text[:1500] if len(transcript_text) > 1500 else transcript_text
        
        return f"""סכם בקצרה את השיחה הזאת בעברית:

{short_transcript}

משתתפים: {speakers_str}

כתוב 3-4 משפטים קצרים שמסכמים את עיקר השיחה.
"""
    
    def analyze_audio_direct(self, audio_path: str) -> Dict[str, Any]:
        """
        Direct audio analysis using the proven SYSTEM_INSTRUCTION prompt.
        
        This bypasses the multi-step transcript analysis and sends audio
        directly to Gemini with a comprehensive expert prompt.
        This is the same approach used in process_meetings.py which works reliably.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dict with success status and analysis text
        """
        import time
        from pathlib import Path
        
        if not self.is_configured:
            return {
                "success": False,
                "error": "שירות הניתוח לא מוגדר",
                "source": "direct"
            }
        
        audio_file = Path(audio_path)
        if not audio_file.exists():
            return {
                "success": False,
                "error": f"קובץ האודיו לא נמצא: {audio_path}",
                "source": "direct"
            }
        
        print(f"🎙️ [Direct Analysis] Starting direct audio analysis...")
        print(f"   📁 File: {audio_file.name}")
        print(f"   📏 Size: {audio_file.stat().st_size / 1024:.1f} KB")
        
        try:
            # Determine MIME type from file extension
            mime_type_map = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.wave': 'audio/wav',
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                '.ogg': 'audio/ogg',
                '.flac': 'audio/flac',
                '.mp4': 'audio/mp4',
                '.opus': 'audio/opus',
            }
            
            file_ext = audio_file.suffix.lower()
            mime_type = mime_type_map.get(file_ext, 'audio/mpeg')
            print(f"   📋 MIME type: {mime_type}")
            
            # Upload file to Gemini
            print(f"   📤 Uploading to Gemini...")
            file_ref = genai.upload_file(
                path=str(audio_path),
                display_name=audio_file.name,
                mime_type=mime_type
            )
            
            # Wait for file to be processed
            print(f"   ⏳ Waiting for Gemini processing...")
            max_wait = 120  # 2 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                file_ref = genai.get_file(file_ref.name)
                state = file_ref.state.name if hasattr(file_ref.state, 'name') else str(file_ref.state)
                
                if state == "ACTIVE":
                    print(f"   ✅ File processing complete")
                    break
                elif state == "FAILED":
                    return {
                        "success": False,
                        "error": f"Gemini failed to process file: {file_ref.name}",
                        "source": "direct"
                    }
                
                time.sleep(2)
            else:
                return {
                    "success": False,
                    "error": "Timeout waiting for Gemini to process audio",
                    "source": "direct"
                }
            
            # Generate content with expert prompt + Knowledge Base
            print(f"   🧠 Running expert analysis...")
            
            # Inject personal knowledge base into system instruction
            system_instruction = DIRECT_AUDIO_SYSTEM_INSTRUCTION
            kb_context = get_kb_context()
            if kb_context:
                system_instruction += "\n" + kb_context
                print(f"   📚 Knowledge Base injected ({len(kb_context)} chars)")
            
            contents = [
                system_instruction,
                file_ref
            ]
            
            # Use safety settings to prevent blocking
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = self.model.generate_content(
                contents,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 2000,
                },
                safety_settings=safety_settings
            )
            
            # Extract text safely
            analysis_text = ""
            try:
                analysis_text = response.text.strip() if response.text else ""
            except (ValueError, AttributeError):
                # Try direct extraction from candidates
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                analysis_text += part.text
            
            # Clean up uploaded file
            try:
                genai.delete_file(file_ref.name)
                print(f"   🗑️ Deleted temp file from Gemini")
            except Exception as del_err:
                print(f"   ⚠️ Could not delete Gemini file: {del_err}")
            
            if not analysis_text or len(analysis_text.strip()) < 50:
                return {
                    "success": False,
                    "error": "Gemini returned empty analysis",
                    "source": "direct"
                }
            
            israel_time = get_israel_time()
            print(f"   ✅ Direct analysis complete: {len(analysis_text)} chars")
            
            return {
                "success": True,
                "raw_analysis": analysis_text,
                "source": "direct",
                "timestamp": israel_time.isoformat(),
                "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M')
            }
            
        except Exception as e:
            print(f"   ❌ Direct analysis error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            
            # Record error for health reporting
            try:
                from app.services.architecture_audit_service import architecture_audit_service
                architecture_audit_service.record_expert_error(f"Direct: {str(e)[:50]}")
            except:
                pass
            
            return {
                "success": False,
                "error": f"{type(e).__name__}: {str(e)[:100]}",
                "source": "direct"
            }
    
    def format_for_whatsapp(self, analysis_result: Dict, include_header: bool = True) -> str:
        """
        Format the expert analysis for WhatsApp message.
        
        STRICT: Total message must be under 1600 characters.
        
        Args:
            analysis_result: Result from analyze_transcript
            include_header: Whether to include the decorative header
            
        Returns:
            Formatted WhatsApp message string (max 1600 chars)
        """
        if not analysis_result.get("success"):
            error = analysis_result.get('error', 'שגיאה לא ידועה')
            return f"⚠️ לא הצלחתי לבצע ניתוח מומחה: {error}"
        
        raw = analysis_result.get("raw_analysis", "")
        source = analysis_result.get("source", "transcript")
        
        # Debug logging
        print(f"📊 [format_for_whatsapp] Source: {source}, Raw analysis: {len(raw)} chars")
        if not raw:
            print("   ⚠️  WARNING: raw_analysis is EMPTY!")
        
        # Build message - Direct/Combined analysis already has full formatting
        message = ""
        
        if source in ("direct", "combined"):
            # Direct audio analysis or Combined prompt already includes expert header (🧠 הכובע שנבחר)
            # No need to add extra header - use raw content as-is
            message = raw
        else:
            # Transcript-based analysis - add minimal header
            persona = analysis_result.get("persona", "עוזר אישי")
            context = analysis_result.get("context", {})
            
            if include_header:
                category = context.get('primary_category', 'כללי')
                message += f"🧠 *{persona}* | {category}\n\n"
            
            message += raw
        
        # STRICT: Enforce 1200 char limit to prevent truncation
        MAX_LENGTH = 1200
        if len(message) > MAX_LENGTH:
            print(f"   ⚠️ Message too long ({len(message)} chars), trimming to {MAX_LENGTH}")
            
            # Try to include Kaizen at the end
            kaizen_start = message.find("📈 קאיזן")
            
            if kaizen_start > 0 and kaizen_start < MAX_LENGTH - 200:
                # Kaizen fits within limit - keep from Kaizen onwards
                before_kaizen = message[:kaizen_start].strip()
                kaizen_section = message[kaizen_start:]
                
                # Trim before_kaizen to fit
                available = MAX_LENGTH - len(kaizen_section) - 50
                if len(before_kaizen) > available:
                    # Find last complete line
                    before_kaizen = before_kaizen[:available]
                    last_newline = before_kaizen.rfind('\n')
                    if last_newline > available * 0.5:
                        before_kaizen = before_kaizen[:last_newline]
                
                message = before_kaizen + "\n\n" + kaizen_section
            else:
                # Kaizen too far or not found - just truncate
                message = message[:MAX_LENGTH - 30]
                last_newline = message.rfind('\n')
                if last_newline > MAX_LENGTH * 0.7:
                    message = message[:last_newline]
                message += "\n\n_(קוצר)_"
        
        print(f"📊 [format_for_whatsapp] Final message: {len(message)} chars")
        return message
    
    def save_analysis_to_drive(
        self,
        analysis_result: Dict,
        transcript_file_id: str,
        drive_service
    ) -> Optional[str]:
        """
        Save the expert analysis as a companion file to the transcript.
        This enables retroactive updates when speakers are identified.
        
        Returns:
            File ID of saved analysis, or None if failed
        """
        if not analysis_result.get("success"):
            return None
        
        try:
            # Build analysis document
            analysis_doc = {
                "persona": analysis_result.get("persona"),
                "persona_keys": analysis_result.get("persona_keys"),
                "context": analysis_result.get("context"),
                "speakers": analysis_result.get("speakers"),
                "analysis": analysis_result.get("raw_analysis"),
                "timestamp": analysis_result.get("timestamp"),
                "transcript_file_id": transcript_file_id
            }
            
            # Save via drive service if available
            # This would be implemented in drive_memory_service
            # For now, the analysis is included in the main transcript save
            return None
            
        except Exception as e:
            logger.error(f"❌ שגיאה בשמירת ניתוח: {e}")
            return None


# Singleton instance
expert_analysis_service = ExpertAnalysisService()
