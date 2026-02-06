"""
Architecture Audit Service - Comprehensive Weekly Stack Analysis

This service performs a weekly audit of the Second Brain system:
1. External Scan: Research latest AI updates (Diarization, RAG, Latency)
2. Internal Analytics: Voice identification accuracy, weak signatures
3. Data Hygiene: Transcript folder size, archiving recommendations
4. Strategic Report: Actionable recommendations via WhatsApp

Triggers:
- Scheduled: Every Friday at 08:00 AM
- Manual: WhatsApp message "בדוק את הסטאק"
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)


class ArchitectureAuditService:
    """
    Comprehensive Architect Agent for weekly system audits.
    """
    
    def __init__(self):
        self.api_key = settings.google_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use Gemini 2.0 with Google Search grounding
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
            logger.warning("⚠️  Google API key not set - Audit service limited")
        
        self.is_configured = bool(self.api_key)
    
    # ================================================================
    # EXTERNAL SCAN: Market Research with Google Search
    # ================================================================
    
    def research_ai_updates(self) -> Dict[str, Any]:
        """
        Use Gemini with Google Search to find latest AI updates.
        Focus areas: Diarization, RAG, Latency optimization.
        """
        if not self.is_configured:
            return {"error": "Service not configured"}
        
        print("🌍 Running external market scan...")
        
        research_prompt = """
        You are a technical AI researcher. Search for and summarize the LATEST developments (last 7 days) in:
        
        1. **Speaker Diarization & Voice ID:**
           - New models or APIs for speaker identification
           - Accuracy improvements in multi-speaker scenarios
           - Compare: Gemini vs Deepgram vs AssemblyAI vs Pyannote
        
        2. **RAG (Retrieval Augmented Generation):**
           - New frameworks or optimizations
           - Best practices for long-term memory in conversational AI
           - Vector database innovations
        
        3. **Latency Optimization:**
           - Techniques for faster voice transcription
           - Streaming vs batch processing trends
           - Edge AI developments
        
        For each finding, provide:
        - Source/Company
        - Key innovation
        - Relevance to a personal voice assistant (Hebrew support bonus)
        
        Format your response as a structured analysis in Hebrew.
        Focus on GAME CHANGERS only - skip incremental updates.
        """
        
        try:
            # Use Google Search grounding
            response = self.model.generate_content(
                research_prompt,
                tools='google_search_retrieval',
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 2000
                }
            )
            
            return {
                "success": True,
                "findings": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ External scan failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": "לא הצלחתי לבצע סריקה חיצונית. בדוק את החיבור ל-Google Search."
            }
    
    def compare_to_competitors(self) -> Dict[str, Any]:
        """
        Compare current Gemini-based stack to alternatives.
        """
        if not self.is_configured:
            return {"error": "Service not configured"}
        
        print("⚔️ Running competitor comparison...")
        
        comparison_prompt = """
        Compare these speech-to-text and diarization solutions for a Hebrew voice assistant:
        
        | Feature | Gemini 2.0 | Deepgram Nova-2 | AssemblyAI Universal-2 |
        |---------|------------|-----------------|------------------------|
        | Hebrew Support | ? | ? | ? |
        | Speaker Diarization | ? | ? | ? |
        | Real-time Streaming | ? | ? | ? |
        | Pricing (per hour) | ? | ? | ? |
        | Accuracy (estimated) | ? | ? | ? |
        
        Fill in this table with current data (use Google Search to verify).
        Add a recommendation: Which is best for a personal voice assistant with Hebrew?
        
        Output in Hebrew.
        """
        
        try:
            response = self.model.generate_content(
                comparison_prompt,
                tools='google_search_retrieval',
                generation_config={
                    'temperature': 0.2,
                    'max_output_tokens': 1500
                }
            )
            
            return {
                "success": True,
                "comparison": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Competitor comparison failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ================================================================
    # INTERNAL ANALYTICS: Voice Identification Metrics
    # ================================================================
    
    def analyze_voice_identification(self, drive_service) -> Dict[str, Any]:
        """
        Analyze voice_map.json and identification accuracy.
        """
        print("📊 Analyzing voice identification metrics...")
        
        metrics = {
            "total_speakers": 0,
            "auto_identified": 0,
            "manually_tagged": 0,
            "weak_signatures": [],
            "accuracy_ratio": 0.0,
            "recommendations": []
        }
        
        try:
            # Get memory from Drive
            if not drive_service or not drive_service.is_configured:
                return {"error": "Drive service not configured"}
            
            memory = drive_service.get_memory()
            user_profile = memory.get('user_profile', {})
            voice_map = user_profile.get('voice_map', {})
            
            # Analyze voice map
            metrics["total_speakers"] = len(voice_map)
            
            # Check chat history for identification patterns
            chat_history = memory.get('chat_history', [])
            
            auto_count = 0
            manual_count = 0
            
            for interaction in chat_history[-100:]:  # Last 100 interactions
                content = str(interaction)
                if 'auto-identified' in content.lower() or 'זוהה אוטומטית' in content:
                    auto_count += 1
                if 'manually tagged' in content.lower() or 'למדתי' in content or 'זה *' in content:
                    manual_count += 1
            
            metrics["auto_identified"] = auto_count
            metrics["manually_tagged"] = manual_count
            
            total = auto_count + manual_count
            if total > 0:
                metrics["accuracy_ratio"] = round(auto_count / total * 100, 1)
            
            # Identify weak signatures (speakers with low usage)
            # For now, consider speakers with less than 3 mentions as "weak"
            for speaker_id, name in voice_map.items():
                mention_count = sum(1 for i in chat_history if name in str(i))
                if mention_count < 3:
                    metrics["weak_signatures"].append({
                        "name": name,
                        "mentions": mention_count,
                        "reason": "מעט אינטראקציות - ייתכן שדגימת הקול חלשה"
                    })
            
            # Generate recommendations
            if metrics["accuracy_ratio"] < 70:
                metrics["recommendations"].append(
                    "🔴 יחס זיהוי נמוך - שקול להקליט דגימות קול נוספות"
                )
            if len(metrics["weak_signatures"]) > 0:
                metrics["recommendations"].append(
                    f"⚠️ יש {len(metrics['weak_signatures'])} דוברים עם דגימות חלשות"
                )
            if metrics["total_speakers"] < 3:
                metrics["recommendations"].append(
                    "💡 מעט דוברים במערכת - הוסף עוד אנשים לזיהוי"
                )
            
            return {
                "success": True,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Voice analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "metrics": metrics
            }
    
    # ================================================================
    # DATA HYGIENE: Transcript & Storage Analysis
    # ================================================================
    
    def analyze_data_hygiene(self, drive_service) -> Dict[str, Any]:
        """
        Check transcript folder size and recommend archiving.
        """
        print("🧹 Analyzing data hygiene...")
        
        hygiene = {
            "transcript_count": 0,
            "oldest_transcript": None,
            "newest_transcript": None,
            "total_size_mb": 0,
            "archive_threshold": 100,
            "needs_archiving": False,
            "recommendations": []
        }
        
        try:
            if not drive_service or not drive_service.is_configured:
                return {"error": "Drive service not configured"}
            
            # Get recent transcripts to count
            transcripts = drive_service.get_recent_transcripts(limit=200)
            hygiene["transcript_count"] = len(transcripts)
            
            if transcripts:
                # Sort by date
                sorted_transcripts = sorted(
                    transcripts, 
                    key=lambda x: x.get('created_time', ''),
                    reverse=True
                )
                hygiene["newest_transcript"] = sorted_transcripts[0].get('created_time', 'Unknown')
                hygiene["oldest_transcript"] = sorted_transcripts[-1].get('created_time', 'Unknown')
            
            # Check if archiving needed
            if hygiene["transcript_count"] > hygiene["archive_threshold"]:
                hygiene["needs_archiving"] = True
                excess = hygiene["transcript_count"] - hygiene["archive_threshold"]
                hygiene["recommendations"].append(
                    f"🗄️ יש {excess} תמלולים מעבר לסף - מומלץ להעביר לארכיון"
                )
            
            # Check for old transcripts (more than 30 days)
            if hygiene["oldest_transcript"]:
                try:
                    oldest_date = datetime.fromisoformat(hygiene["oldest_transcript"].replace('Z', '+00:00'))
                    age_days = (datetime.now(oldest_date.tzinfo) - oldest_date).days
                    if age_days > 30:
                        hygiene["recommendations"].append(
                            f"📅 יש תמלולים בני {age_days} ימים - שקול ארכוב לפי תאריך"
                        )
                except:
                    pass
            
            return {
                "success": True,
                "hygiene": hygiene
            }
            
        except Exception as e:
            logger.error(f"❌ Data hygiene analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "hygiene": hygiene
            }
    
    # ================================================================
    # STRATEGIC REPORT GENERATION
    # ================================================================
    
    def generate_strategic_report(
        self,
        external_scan: Dict[str, Any],
        comparison: Dict[str, Any],
        voice_metrics: Dict[str, Any],
        data_hygiene: Dict[str, Any]
    ) -> str:
        """
        Generate the comprehensive WhatsApp report.
        """
        print("📝 Generating strategic report...")
        
        report_parts = []
        
        # Header
        report_parts.append("🏗️ *דו״ח ארכיטקטורה שבועי*")
        report_parts.append(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        report_parts.append("")
        
        # System Status
        report_parts.append("=" * 30)
        report_parts.append("🛡️ *סטטוס מערכת*")
        report_parts.append("")
        
        metrics = voice_metrics.get('metrics', {})
        accuracy = metrics.get('accuracy_ratio', 0)
        total_speakers = metrics.get('total_speakers', 0)
        weak_count = len(metrics.get('weak_signatures', []))
        
        report_parts.append(f"📊 יחס זיהוי אוטומטי: *{accuracy}%*")
        report_parts.append(f"👥 דוברים במערכת: *{total_speakers}*")
        
        if weak_count > 0:
            report_parts.append(f"⚠️ דגימות קול חלשות: *{weak_count}*")
            for weak in metrics.get('weak_signatures', [])[:3]:
                report_parts.append(f"   • {weak['name']}: {weak['reason']}")
        else:
            report_parts.append("✅ כל דגימות הקול תקינות")
        
        report_parts.append("")
        
        # Market News
        report_parts.append("=" * 30)
        report_parts.append("🌍 *חדשות מהשוק*")
        report_parts.append("")
        
        if external_scan.get('success'):
            # Summarize findings (first 500 chars)
            findings = external_scan.get('findings', '')
            if len(findings) > 500:
                findings = findings[:500] + "..."
            report_parts.append(findings)
        else:
            report_parts.append("⚠️ לא הצלחתי לסרוק חדשות - בדוק חיבור")
        
        report_parts.append("")
        
        # Data Hygiene
        report_parts.append("=" * 30)
        report_parts.append("🧹 *היגיינת נתונים*")
        report_parts.append("")
        
        hygiene = data_hygiene.get('hygiene', {})
        transcript_count = hygiene.get('transcript_count', 0)
        
        report_parts.append(f"📁 תמלולים בדרייב: *{transcript_count}*")
        
        if hygiene.get('needs_archiving'):
            report_parts.append("🔴 *נדרש ארכוב!*")
        else:
            report_parts.append("✅ נפח תקין")
        
        for rec in hygiene.get('recommendations', []):
            report_parts.append(f"   {rec}")
        
        report_parts.append("")
        
        # Strategic Recommendation
        report_parts.append("=" * 30)
        report_parts.append("💡 *המלצה אסטרטגית*")
        report_parts.append("")
        
        # Determine Stay vs Move recommendation
        if accuracy >= 80 and weak_count == 0:
            report_parts.append("✅ *STAY* - הסטאק הנוכחי עובד מצוין")
            report_parts.append("   Gemini 2.0 מספק ביצועים טובים לעברית")
        elif accuracy < 50:
            report_parts.append("🔴 *CONSIDER MOVE* - יחס הזיהוי נמוך מדי")
            report_parts.append("   שקול לבדוק Deepgram או AssemblyAI")
        else:
            report_parts.append("🟡 *OPTIMIZE* - יש מקום לשיפור")
            report_parts.append("   הוסף דגימות קול נוספות לפני החלטה על מעבר")
        
        report_parts.append("")
        report_parts.append("_סריקה אוטומטית כל יום שישי 08:00_")
        
        return "\n".join(report_parts)
    
    # ================================================================
    # MAIN AUDIT FUNCTION
    # ================================================================
    
    def run_weekly_architecture_audit(self, drive_service=None) -> Dict[str, Any]:
        """
        Run the complete weekly architecture audit.
        
        Returns:
            Dict with report text and all collected data
        """
        print("\n" + "=" * 60)
        print("🏗️ WEEKLY ARCHITECTURE AUDIT STARTED")
        print("=" * 60)
        
        start_time = datetime.utcnow()
        
        # Step 1: External Scan
        print("\n📡 Step 1/4: External market scan...")
        external_scan = self.research_ai_updates()
        
        # Step 2: Competitor Comparison
        print("\n⚔️ Step 2/4: Competitor comparison...")
        comparison = self.compare_to_competitors()
        
        # Step 3: Voice Identification Analysis
        print("\n📊 Step 3/4: Voice identification analysis...")
        voice_metrics = self.analyze_voice_identification(drive_service)
        
        # Step 4: Data Hygiene
        print("\n🧹 Step 4/4: Data hygiene check...")
        data_hygiene = self.analyze_data_hygiene(drive_service)
        
        # Generate Report
        print("\n📝 Generating strategic report...")
        report = self.generate_strategic_report(
            external_scan=external_scan,
            comparison=comparison,
            voice_metrics=voice_metrics,
            data_hygiene=data_hygiene
        )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Audit completed in {duration:.1f} seconds")
        print("=" * 60 + "\n")
        
        return {
            "success": True,
            "report": report,
            "duration_seconds": duration,
            "timestamp": start_time.isoformat(),
            "data": {
                "external_scan": external_scan,
                "comparison": comparison,
                "voice_metrics": voice_metrics,
                "data_hygiene": data_hygiene
            }
        }


# Singleton instance
architecture_audit_service = ArchitectureAuditService()
