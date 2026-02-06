"""
Expert Analysis Service - Multi-Agent System for Meeting Analysis

This service applies expert personas to analyze transcribed conversations:
- Simon Sinek (Leadership/Management)
- Adler Institute (Parenting/Home)
- Esther Perel (Relationships)
- McKinsey + Tech (Strategy/Business)

Each persona provides:
- Sentiment analysis
- Action items (assigned to specific speakers)
- Detailed summary (who said what)
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)


# Expert Persona Definitions
EXPERT_PERSONAS = {
    "leadership": {
        "name": "סיימון סינק (מנהיגות)",
        "trigger_keywords": ["צוות", "עובדים", "מנהל", "חברה", "תרבות", "hiring", "mentoring", "culture"],
        "focus": "Start with Why, The Infinite Game, Circle of Safety, Leaders Eat Last",
        "tone": "מעורר השראה, ממוקד באנשים, חזוני"
    },
    "parenting": {
        "name": "מכון אדלר (הורות)",
        "trigger_keywords": ["ילדים", "בנים", "בנות", "בית", "חינוך", "מטלות", "שיעורי בית", "kids", "children"],
        "focus": "עידוד, תוצאות טבעיות, שיתוף פעולה, הימנעות ממאבקי כוח",
        "tone": "תומך, פרקטי, חינוכי"
    },
    "relationship": {
        "name": "אסתר פרל (יחסים)",
        "trigger_keywords": ["בעל", "אישה", "זוגיות", "רגשות", "אהבה", "relationship", "partner"],
        "focus": "אינטליגנציה רגשית, איזון בין ביטחון וחופש, הקשבה ל'לא נאמר'",
        "tone": "אמפתי, עמוק, תובנתי"
    },
    "strategy": {
        "name": "מקינזי + Tech Innovation (אסטרטגיה)",
        "trigger_keywords": ["עסק", "מוצר", "לקוחות", "אסטרטגיה", "roadmap", "MVP", "startup", "product"],
        "focus": "MECE structure, data-driven, scalability, Agile/Lean thinking",
        "tone": "חד, מקצועי, ממוקד פעולה"
    },
    "general": {
        "name": "עוזר אישי כללי",
        "trigger_keywords": [],
        "focus": "סיכום ברור ותמציתי עם אקשן אייטמס",
        "tone": "ישיר, שימושי, פרקטי"
    }
}


class ExpertAnalysisService:
    """
    Multi-Agent Analysis System for meeting transcripts.
    Applies expert personas based on conversation context.
    """
    
    def __init__(self):
        self.api_key = settings.google_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ ExpertAnalysisService initialized with Gemini 1.5 Flash")
            except Exception as e:
                logger.error(f"❌ Could not init model: {e}")
                self.model = None
        else:
            self.model = None
            logger.warning("⚠️  Google API key not set - Expert Analysis disabled")
        
        self.is_configured = bool(self.api_key and self.model)
    
    def detect_persona(self, transcript_text: str, segments: List[Dict]) -> str:
        """
        Detect which expert persona to apply based on conversation content.
        
        Args:
            transcript_text: Full text of the transcript
            segments: List of transcript segments with speaker info
            
        Returns:
            Persona key (leadership, parenting, relationship, strategy, general)
        """
        text_lower = transcript_text.lower()
        
        # Check each persona's trigger keywords
        scores = {}
        for persona_key, persona in EXPERT_PERSONAS.items():
            if persona_key == "general":
                continue
            score = sum(1 for kw in persona["trigger_keywords"] if kw in text_lower)
            scores[persona_key] = score
        
        # Return persona with highest score, or "general" if no matches
        if not scores or max(scores.values()) == 0:
            return "general"
        
        return max(scores, key=scores.get)
    
    def build_expert_prompt(self, persona_key: str, segments: List[Dict], voice_map: Dict) -> str:
        """
        Build the analysis prompt for the selected expert persona.
        
        Args:
            persona_key: Which persona to use
            segments: Transcript segments with speaker info
            voice_map: Mapping of speaker IDs to names
            
        Returns:
            Full prompt for Gemini
        """
        persona = EXPERT_PERSONAS.get(persona_key, EXPERT_PERSONAS["general"])
        
        # Build readable transcript with speaker names
        transcript_lines = []
        for seg in segments:
            speaker_id = seg.get("speaker", "Unknown")
            # Replace speaker ID with name if known
            speaker_name = voice_map.get(speaker_id, speaker_id)
            text = seg.get("text", "")
            transcript_lines.append(f"**{speaker_name}**: {text}")
        
        transcript_text = "\n".join(transcript_lines)
        
        prompt = f"""אתה מומחה בשם {persona['name']}.

**הגישה שלך:**
{persona['focus']}

**הטון שלך:**
{persona['tone']}

---

**תמליל השיחה:**
{transcript_text}

---

**בצע ניתוח מקיף בעברית לפי הפורמט הבא:**

🎯 **סנטימנט כללי:**
[חיובי/שלילי/ניטרלי - עם הסבר קצר על האווירה הכללית של השיחה]

📌 **נושאי השיחה העיקריים:**
[1-3 נושאים מרכזיים שעלו בשיחה]

🕵️ **ניתוח עומק (הסאב-טקסט):**
[2-3 משפטים על מה שבאמת קורה מתחת לפני השטח, לפי המומחיות שלך]

💡 **תובנה מרכזית:**
[תובנה אחת עמוקה שהמומחה שלך היה מדגיש - זו ה"אהא" שלך]

👥 **סיכום מפורט (מי אמר מה):**
[פרט לפי דוברים:
- **[שם דובר 1]**: מה הם הביעו/החליטו/הציעו
- **[שם דובר 2]**: מה הם הביעו/החליטו/הציעו
וכו']

✅ **אקשן אייטמס (משימות):**
[רשימת משימות ספציפיות עם שמות האחראים:
- **[שם]**: משימה ספציפית
- **[שם]**: משימה ספציפית
או "אין משימות להמשך" אם אין]

❓ **שאלה למחשבה:**
[שאלה פרובוקטיבית אחת שהמומחה היה שואל כדי לקדם חשיבה]

---

**חשוב:**
- כתוב בעברית
- השתמש בשמות הדוברים (לא "דובר 1")
- היה ספציפי ופרקטי
- אל תסכם סתם - תן תובנות עמוקות
"""
        return prompt
    
    async def analyze_transcript(
        self,
        segments: List[Dict],
        voice_map: Optional[Dict] = None,
        force_persona: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform expert analysis on a transcript.
        
        Args:
            segments: List of transcript segments
            voice_map: Optional mapping of speaker IDs to names
            force_persona: Optional - force a specific persona
            
        Returns:
            Dict with analysis results:
            - persona: Which expert was used
            - sentiment: Overall tone
            - summary: Detailed summary by speaker
            - action_items: List of tasks with assignees
            - insight: Key takeaway
            - reflection_question: Provocative question
            - raw_analysis: Full text from Gemini
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "Expert Analysis Service not configured"
            }
        
        voice_map = voice_map or {}
        
        # Build transcript text for persona detection
        transcript_text = " ".join(seg.get("text", "") for seg in segments)
        
        # Detect or use forced persona
        if force_persona and force_persona in EXPERT_PERSONAS:
            persona_key = force_persona
        else:
            persona_key = self.detect_persona(transcript_text, segments)
        
        persona = EXPERT_PERSONAS[persona_key]
        print(f"🧠 [Expert Analysis] Selected persona: {persona['name']}")
        
        # Build and send prompt
        prompt = self.build_expert_prompt(persona_key, segments, voice_map)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.4,
                    'max_output_tokens': 2000
                }
            )
            
            analysis_text = response.text if response.text else ""
            
            return {
                "success": True,
                "persona": persona["name"],
                "persona_key": persona_key,
                "raw_analysis": analysis_text,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Expert analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "persona": persona["name"]
            }
    
    def format_for_whatsapp(self, analysis_result: Dict) -> str:
        """
        Format the expert analysis for WhatsApp message.
        
        Args:
            analysis_result: Result from analyze_transcript
            
        Returns:
            Formatted WhatsApp message string
        """
        if not analysis_result.get("success"):
            return f"⚠️ לא הצלחתי לבצע ניתוח מומחה: {analysis_result.get('error', 'שגיאה לא ידועה')}"
        
        persona = analysis_result.get("persona", "עוזר אישי")
        raw = analysis_result.get("raw_analysis", "")
        
        # Build message header
        message = f"🧠 *ניתוח מומחה: {persona}*\n"
        message += "═" * 25 + "\n\n"
        
        # Add the raw analysis (already formatted by Gemini)
        message += raw
        
        # Trim if too long for WhatsApp
        if len(message) > 3500:
            message = message[:3400] + "\n\n... (הניתוח המלא נשמר בדרייב)"
        
        return message


# Singleton instance
expert_analysis_service = ExpertAnalysisService()
