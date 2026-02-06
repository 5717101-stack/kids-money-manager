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

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

import google.generativeai as genai

from app.core.config import settings

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
            genai.configure(api_key=self.api_key)
            
            # Try models in order of preference (same as gemini_service.py)
            # gemini-2.5-pro is the stable model that works
            models_to_try = [
                'gemini-2.5-pro',          # Primary - stable and works
                'gemini-2.0-flash',        # Fallback 1 - newer flash
                'gemini-1.5-flash-latest', # Fallback 2 - flash with latest suffix
                'gemini-pro',              # Fallback 3 - basic pro
            ]
            
            for model_name in models_to_try:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    self.model_name = model_name
                    logger.info(f"✅ שירות ניתוח המומחים אותחל עם {model_name}")
                    print(f"✅ [Expert Analysis] Model initialized: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️  Could not init {model_name}: {e}")
                    print(f"⚠️  [Expert Analysis] Model {model_name} failed: {e}")
                    continue
            
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
        
        prompt = f"""אתה חבר במועצת המומחים של "המוח השני".

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
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                print(f"   🔄 Attempt {attempt + 1}/{max_retries}")
                
                # Use simpler prompt on retry
                current_prompt = prompt if attempt == 0 else self._build_fallback_prompt(transcript_text, speakers)
                
                response = self.model.generate_content(
                    current_prompt,
                    generation_config={
                        'temperature': 0.3 if attempt > 0 else 0.4,
                        'max_output_tokens': 1000
                    }
                )
                
                # Safe extraction of response.text
                try:
                    analysis_text = response.text.strip() if response.text else ""
                except (ValueError, AttributeError) as text_err:
                    print(f"   ⚠️ response.text access failed: {text_err}")
                    analysis_text = ""
                
                print(f"   📝 Response: {len(analysis_text)} chars")
                
                # Check for empty response
                if len(analysis_text.strip()) < 50:
                    print(f"   ⚠️  Response too short ({len(analysis_text)} chars), retrying...")
                    continue
                
                # SUCCESS - break out of retry loop
                break
                
            except Exception as e:
                print(f"   ❌ Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ [CRITICAL] ניתוח מומחה נכשל לאחר {max_retries} נסיונות: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Final validation
        if not analysis_text or len(analysis_text.strip()) < 50:
            print("❌ [CRITICAL] Analysis returned EMPTY after all retries!")
            logger.error("❌ [CRITICAL] Expert analysis returned empty text")
            return {
                "success": False,
                "error": "ניתוח חזר ריק - בדוק את המודל",
                "persona": " + ".join(persona_names),
                "model_used": self.model_name
            }
        
        print(f"✅ [Expert Analysis] SUCCESS - {len(analysis_text)} chars")
        israel_time = get_israel_time()
        
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
        
        persona = analysis_result.get("persona", "עוזר אישי")
        context = analysis_result.get("context", {})
        raw = analysis_result.get("raw_analysis", "")
        
        # Debug logging
        print(f"📊 [format_for_whatsapp] Raw analysis: {len(raw)} chars")
        if not raw:
            print("   ⚠️  WARNING: raw_analysis is EMPTY!")
        
        # Build message with minimal header
        message = ""
        
        if include_header:
            # Minimal header - ONE line
            category = context.get('primary_category', 'כללי')
            message += f"🧠 *{persona}* | {category}\n\n"
        
        # Add the raw analysis (formatted by Gemini)
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
