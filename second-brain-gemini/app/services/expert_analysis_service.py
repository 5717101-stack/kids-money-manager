"""
Expert Analysis Service - Council of Experts for Meeting Analysis

This service applies expert personas to analyze transcribed conversations:
- Michal Dalyot / Adler Institute (Parenting/Boundaries)
- Esther Perel (Relationships/Communication)
- McKinsey & Co. / Israeli Tech (Business/Strategy)
- Simon Sinek (Leadership/The Why)

Each persona provides:
- Sentiment analysis
- Executive summary
- Expert insights
- Action items (assigned to specific speakers)
- Mandatory Kaizen Feedback (לשימור / לשיפור)
"""

import json
import logging
from typing import Dict, List, Any, Optional
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
        "trigger_keywords": [
            "ילדים", "בנים", "בנות", "בית", "חינוך", "מטלות", "שיעורי בית",
            "kids", "children", "הורים", "משפחה", "גבולות", "כללים",
            "ילד", "ילדה", "בן", "בת", "התנהגות", "משמעת"
        ],
        "focus": """
גישת אדלר להורות דמוקרטית:
- עידוד במקום שבח (Encouragement vs Praise)
- תוצאות טבעיות והגיוניות (Natural & Logical Consequences)
- שיתוף פעולה ואחריות משותפת
- הימנעות ממאבקי כוח
- כבוד הדדי וגבולות ברורים
- מתן בחירות במסגרת גבולות
""",
        "tone": "תומך, פרקטי, חינוכי, ללא שיפוטיות"
    },
    "relationship": {
        "name": "אסתר פרל (יחסים ותקשורת)",
        "short_name": "אסתר פרל",
        "trigger_keywords": [
            "בעל", "אישה", "זוגיות", "רגשות", "אהבה", "relationship", "partner",
            "ערן", "זוג", "כעס", "תסכול", "אינטימיות", "קשר", "חיבור",
            "ריב", "ויכוח", "לא מבין", "לא מבינה"
        ],
        "focus": """
גישת אסתר פרל לזוגיות:
- אינטליגנציה רגשית עמוקה
- איזון בין ביטחון (Security) לחופש (Freedom)
- הקשבה ל"לא נאמר" - מה בין השורות
- הבנת דינמיקות כוח נסתרות
- פישור בין תשוקה לחיי יום-יום
- זיהוי דפוסים חוזרים בתקשורת
""",
        "tone": "אמפתי, עמוק, תובנתי, ללא שיפוט"
    },
    "strategy": {
        "name": "מקינזי וטק ישראלי (אסטרטגיה ועסקים)",
        "short_name": "מקינזי + Tech",
        "trigger_keywords": [
            "עסק", "מוצר", "לקוחות", "אסטרטגיה", "roadmap", "MVP", "startup",
            "product", "כסף", "תקציב", "הכנסות", "מכירות", "שוק", "מתחרים",
            "פיצ'ר", "פיתוח", "tech", "קוד", "משקיעים", "גיוס", "חברה"
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
""",
        "tone": "חד, מקצועי, ממוקד פעולה, חותך לעניין"
    },
    "leadership": {
        "name": "סיימון סינק (מנהיגות והשראה)",
        "short_name": "סיימון סינק",
        "trigger_keywords": [
            "צוות", "עובדים", "מנהל", "חברה", "תרבות", "hiring", "mentoring",
            "culture", "מנהיגות", "השראה", "ערכים", "חזון", "משמעות",
            "מוטיבציה", "גיוס", "פיטורים", "ביצועים", "משוב"
        ],
        "focus": """
גישת סיימון סינק למנהיגות:
- Start with Why - תתחיל מה"למה"
- The Infinite Game - משחק אינסופי, לא ניצחון חד פעמי
- Circle of Safety - יצירת מעגל ביטחון לצוות
- Leaders Eat Last - מנהיג דואג קודם לאחרים
- מנהיגות משרתת (Servant Leadership)
- בניית אמון לטווח ארוך
""",
        "tone": "מעורר השראה, ממוקד באנשים, חזוני, אנושי"
    },
    "general": {
        "name": "עוזר אישי חכם",
        "short_name": "עוזר אישי",
        "trigger_keywords": [],
        "focus": "סיכום ברור ותמציתי עם תובנות פרקטיות ואקשן אייטמס",
        "tone": "ישיר, שימושי, פרקטי"
    }
}


class ExpertAnalysisService:
    """
    Council of Experts Analysis System for meeting transcripts.
    Applies expert personas based on conversation context.
    Includes mandatory Kaizen feedback for personal growth.
    """
    
    def __init__(self):
        self.api_key = settings.google_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ בשירות ניתוח המומחים אותחל עם Gemini 1.5 Flash")
            except Exception as e:
                logger.error(f"❌ שגיאה באתחול המודל: {e}")
                self.model = None
        else:
            self.model = None
            logger.warning("⚠️  מפתח Google API לא מוגדר - ניתוח מומחים מושבת")
        
        self.is_configured = bool(self.api_key and self.model)
    
    def detect_persona(self, transcript_text: str, segments: List[Dict]) -> str:
        """
        Detect which expert persona to apply based on conversation content.
        Uses weighted keyword matching for accurate routing.
        """
        text_lower = transcript_text.lower()
        
        # Check each persona's trigger keywords with scoring
        scores = {}
        for persona_key, persona in EXPERT_PERSONAS.items():
            if persona_key == "general":
                continue
            score = sum(1 for kw in persona["trigger_keywords"] if kw in text_lower)
            scores[persona_key] = score
        
        # Return persona with highest score, or "general" if no matches
        if not scores or max(scores.values()) == 0:
            return "general"
        
        best_persona = max(scores, key=scores.get)
        print(f"   ניתוב אוטומטי: {best_persona} (ציון: {scores[best_persona]})")
        return best_persona
    
    def build_expert_prompt(self, persona_key: str, segments: List[Dict], voice_map: Dict) -> str:
        """
        Build the analysis prompt for the selected expert persona.
        Includes mandatory Kaizen feedback section.
        """
        persona = EXPERT_PERSONAS.get(persona_key, EXPERT_PERSONAS["general"])
        israel_time = get_israel_time()
        
        # Build readable transcript with speaker names (RTL-friendly)
        transcript_lines = []
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
            text = seg.get("text", "")
            transcript_lines.append(f"**{speaker_name}**: {text}")
        
        transcript_text = "\n".join(transcript_lines)
        
        prompt = f"""אתה חבר במועצת המומחים של "המוח השני" (Second Brain).

**הפרסונה שלך:** {persona['name']}

**הגישה והמתודולוגיה שלך:**
{persona['focus']}

**הטון שלך:**
{persona['tone']}

**זמן הניתוח:** {israel_time.strftime('%d/%m/%Y %H:%M')} (שעון ישראל)

---

**תמליל השיחה:**
{transcript_text}

---

**הנחיות חשובות:**
1. כתוב בעברית בלבד
2. השתמש בשמות הדוברים האמיתיים (לא "דובר 1" או "Speaker 2")
3. היה ספציפי ופרקטי - תובנות שאפשר ליישם
4. כשיש מילים באנגלית, התחל את המשפט בעברית לתמיכה ב-RTL
   (למשל: "ברגעים אלה Cursor החל...")

---

**בצע ניתוח מקיף בפורמט הבא:**

🎯 **סנטימנט כללי:**
[חיובי/שלילי/מעורב - עם הסבר קצר על האווירה הכללית]

📋 **תקציר מנהלים (Executive Summary):**
[3-4 משפטים שמסכמים את עיקרי השיחה - מה נדון, מה הוחלט, מה נשאר פתוח]

🔍 **תובנות המומחה ({persona['short_name']}):**
[2-3 תובנות עמוקות מנקודת המבט של המומחיות שלך. מה קורה מתחת לפני השטח? מה הדינמיקה האמיתית?]

👥 **מי אמר מה (סיכום לפי דוברים):**
[לכל דובר:
- **[שם]**: עמדה/הצעה/החלטה עיקרית
]

✅ **אקשן אייטמס (משימות):**
[משימות ספציפיות עם אחראים:
- **[שם]**: משימה קונקרטית
או: "לא זוהו משימות ספציפיות"]

═══════════════════════════════
📈 **פידבק לצמיחה (Kaizen)**
═══════════════════════════════

✅ **לשימור (מה היה טוב):**
[1-2 התנהגויות/החלטות/דפוסי תקשורת חיוביים שראוי לשמר. אם לא זוהה משהו בולט - אפשר לדלג]

🎯 **לשיפור (הזדמנות לצמיחה):**
[**חובה!** גם בשיחה טובה יש תמיד הזדמנות ל-Level Up.
דוגמאות:
- "לשאול יותר שאלות פתוחות"
- "להגדיר KPI ברור יותר"
- "להשתמש בשפה מעודדת יותר"
- "לתת יותר מרחב לצד השני לדבר"
ציין דוגמה ספציפית מהשיחה אם אפשר]

❓ **שאלה למחשבה:**
[שאלה פרובוקטיבית אחת שתעזור לצמיחה אישית]
"""
        return prompt
    
    async def analyze_transcript(
        self,
        segments: List[Dict],
        voice_map: Optional[Dict] = None,
        force_persona: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform expert analysis on a transcript with Kaizen feedback.
        
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
        
        voice_map = voice_map or {}
        
        # Build transcript text for persona detection
        transcript_text = " ".join(seg.get("text", "") for seg in segments)
        
        # Detect or use forced persona
        if force_persona and force_persona in EXPERT_PERSONAS:
            persona_key = force_persona
            print(f"🧠 [ניתוח מומחה] פרסונה נכפית: {force_persona}")
        else:
            persona_key = self.detect_persona(transcript_text, segments)
        
        persona = EXPERT_PERSONAS[persona_key]
        print(f"🧠 [ניתוח מומחה] פרסונה נבחרה: {persona['name']}")
        
        # Build and send prompt
        prompt = self.build_expert_prompt(persona_key, segments, voice_map)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.4,
                    'max_output_tokens': 2500
                }
            )
            
            analysis_text = response.text if response.text else ""
            israel_time = get_israel_time()
            
            return {
                "success": True,
                "persona": persona["name"],
                "persona_key": persona_key,
                "raw_analysis": analysis_text,
                "timestamp": israel_time.isoformat(),
                "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M')
            }
            
        except Exception as e:
            logger.error(f"❌ ניתוח מומחה נכשל: {e}")
            return {
                "success": False,
                "error": str(e),
                "persona": persona["name"]
            }
    
    def format_for_whatsapp(self, analysis_result: Dict, include_header: bool = True) -> str:
        """
        Format the expert analysis for WhatsApp message.
        RTL-friendly formatting with clear sections.
        
        Args:
            analysis_result: Result from analyze_transcript
            include_header: Whether to include the decorative header
            
        Returns:
            Formatted WhatsApp message string
        """
        if not analysis_result.get("success"):
            error = analysis_result.get('error', 'שגיאה לא ידועה')
            return f"⚠️ לא הצלחתי לבצע ניתוח מומחה: {error}"
        
        persona = analysis_result.get("persona", "עוזר אישי")
        raw = analysis_result.get("raw_analysis", "")
        timestamp = analysis_result.get("timestamp_display", "")
        
        # Build message with RTL-friendly header
        message = ""
        
        if include_header:
            message += f"🧠 *ניתוח מועצת המומחים*\n"
            message += f"📊 פרסונה: *{persona}*\n"
            if timestamp:
                message += f"⏰ זמן: {timestamp} (שעון ישראל)\n"
            message += "═" * 25 + "\n\n"
        
        # Add the raw analysis (already formatted by Gemini)
        message += raw
        
        # Trim if too long for WhatsApp (4096 char limit, leave buffer)
        if len(message) > 3800:
            message = message[:3700] + "\n\n... (הניתוח המלא נשמר בדרייב)"
        
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
                "persona_key": analysis_result.get("persona_key"),
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
