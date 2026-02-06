"""
Architecture Audit Service - Comprehensive Weekly Stack Analysis

This service performs a weekly audit of the Second Brain system:
1. External Scan: Research latest AI updates (Diarization, RAG, Latency)
2. Internal Analytics: Voice identification accuracy, weak signatures
3. Data Hygiene: Transcript folder size, archiving recommendations
4. Strategic Report: Actionable recommendations via WhatsApp

Triggers:
- Scheduled: Every Friday at 13:00 (1 PM Israel time)
- Manual: WhatsApp message "בדוק את הסטאק"
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path

import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Israel timezone offset (UTC+2 winter, UTC+3 summer)
# Using UTC+2 as default
ISRAEL_TZ_OFFSET = timedelta(hours=2)


def get_israel_time() -> datetime:
    """Get current time in Israel timezone."""
    utc_now = datetime.now(timezone.utc)
    israel_time = utc_now + ISRAEL_TZ_OFFSET
    return israel_time


class ArchitectureAuditService:
    """
    Comprehensive Architect Agent for weekly system audits.
    """
    
    def __init__(self):
        self.api_key = settings.google_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use Gemini 1.5 Pro for reliable responses
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.model = None
            logger.warning("⚠️  Google API key not set - Audit service limited")
        
        self.is_configured = bool(self.api_key)
    
    # ================================================================
    # EXTERNAL SCAN: Market Research
    # ================================================================
    
    def research_ai_updates(self) -> Dict[str, Any]:
        """
        Use Gemini to analyze latest AI developments.
        Since Google Search grounding is unreliable, use Gemini's knowledge
        with explicit instructions to provide recent updates.
        """
        if not self.is_configured:
            return {"error": "Service not configured", "success": False}
        
        print("🌍 Running external market scan...")
        
        # Use a focused prompt that leverages Gemini's knowledge
        research_prompt = """
        אתה אנליסט טכנולוגי. ספק ניתוח קצר ומדויק של ההתפתחויות האחרונות ב-AI:
        
        **1. Speaker Diarization (זיהוי דוברים):**
        - מה המודלים המובילים? (Gemini, Deepgram, AssemblyAI, Pyannote)
        - איזה שיפורים חשובים פורסמו לאחרונה?
        - מי הכי טוב לעברית?
        
        **2. RAG (Retrieval Augmented Generation):**
        - מה הטרנדים העדכניים?
        - כלים חדשים שכדאי לבדוק?
        
        **3. Latency Optimization:**
        - טכניקות לשיפור מהירות transcription
        - Streaming vs Batch - מה עדיף?
        
        **פורמט התשובה:**
        - כתוב בעברית
        - תמציתי (עד 300 מילים)
        - רק עדכונים משמעותיים (Game Changers)
        - ציין אם יש משהו שרלוונטי במיוחד לעברית
        
        אם אין לך מידע עדכני על נושא מסוים, ציין זאת במפורש.
        """
        
        try:
            print("   Querying Gemini for AI market analysis...")
            response = self.model.generate_content(
                research_prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 1500
                }
            )
            
            findings = response.text if response.text else "לא התקבל מידע"
            
            return {
                "success": True,
                "findings": findings,
                "timestamp": get_israel_time().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ External scan failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "findings": f"⚠️ שגיאה בסריקה: {str(e)[:100]}"
            }
    
    def compare_to_competitors(self) -> Dict[str, Any]:
        """
        Compare current Gemini-based stack to alternatives.
        """
        if not self.is_configured:
            return {"error": "Service not configured", "success": False}
        
        print("⚔️ Running competitor comparison...")
        
        comparison_prompt = """
        השווה בין הפתרונות הבאים לזיהוי דיבור ודוברים:
        
        | תכונה | Gemini 2.0 | Deepgram Nova-2 | AssemblyAI |
        |--------|------------|-----------------|------------|
        | תמיכה בעברית | | | |
        | Speaker Diarization | | | |
        | Streaming | | | |
        | עלות (לשעה) | | | |
        | דיוק משוער | | | |
        
        מלא את הטבלה על בסיס הידע שלך.
        הוסף המלצה: מה הכי טוב לעוזר קולי אישי בעברית?
        
        כתוב בעברית, תמציתי.
        """
        
        try:
            response = self.model.generate_content(
                comparison_prompt,
                generation_config={
                    'temperature': 0.2,
                    'max_output_tokens': 1000
                }
            )
            
            return {
                "success": True,
                "comparison": response.text if response.text else "לא התקבלה השוואה",
                "timestamp": get_israel_time().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Competitor comparison failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "comparison": f"⚠️ שגיאה בהשוואה: {str(e)[:50]}"
            }
    
    # ================================================================
    # INTERNAL ANALYTICS: Voice Identification Metrics
    # ================================================================
    
    def analyze_voice_identification(self, drive_service) -> Dict[str, Any]:
        """
        Analyze voice signatures and identification accuracy.
        Directly counts files in Google Drive folders.
        """
        print("📊 Analyzing voice identification metrics...")
        
        metrics = {
            "total_speakers": 0,
            "voice_signatures_count": 0,
            "auto_identified": 0,
            "manually_tagged": 0,
            "weak_signatures": [],
            "accuracy_ratio": 0.0,
            "recommendations": [],
            "drive_connected": False
        }
        
        try:
            # Check Drive connection
            if not drive_service:
                print("   ⚠️ No drive_service provided")
                return {"error": "Drive service not provided", "metrics": metrics}
            
            if not drive_service.is_configured:
                print("   ⚠️ Drive service not configured")
                return {"error": "Drive service not configured", "metrics": metrics}
            
            metrics["drive_connected"] = True
            print("   ✅ Drive service connected")
            
            # Method 1: Count voice signatures directly from folder
            try:
                voice_signatures = drive_service.get_voice_signatures(max_signatures=50)
                metrics["voice_signatures_count"] = len(voice_signatures)
                print(f"   📁 Voice signatures in folder: {len(voice_signatures)}")
            except Exception as e:
                print(f"   ⚠️ Could not get voice signatures: {e}")
            
            # Method 2: Get voice_map from memory
            try:
                memory = drive_service.get_memory()
                user_profile = memory.get('user_profile', {})
                voice_map = user_profile.get('voice_map', {})
                metrics["total_speakers"] = len(voice_map)
                print(f"   👥 Speakers in voice_map: {len(voice_map)}")
                
                # List the speakers
                if voice_map:
                    for speaker_id, name in list(voice_map.items())[:5]:
                        print(f"      - {speaker_id}: {name}")
                
                # Analyze chat history for identification patterns
                chat_history = memory.get('chat_history', [])
                print(f"   💬 Chat history entries: {len(chat_history)}")
                
                auto_count = 0
                manual_count = 0
                
                for interaction in chat_history[-100:]:
                    content = str(interaction).lower()
                    # Auto-identified patterns
                    if 'auto' in content or 'אוטומטי' in content or 'זוהה' in content:
                        auto_count += 1
                    # Manually tagged patterns
                    if 'למדתי' in content or 'זה *' in content or 'נשמר במערכת' in content:
                        manual_count += 1
                
                metrics["auto_identified"] = auto_count
                metrics["manually_tagged"] = manual_count
                
                # Calculate accuracy only if we have data
                total_identifications = auto_count + manual_count
                if total_identifications > 0:
                    metrics["accuracy_ratio"] = round(auto_count / total_identifications * 100, 1)
                elif metrics["total_speakers"] > 0:
                    # If we have speakers but no identification data, assume 50%
                    metrics["accuracy_ratio"] = 50.0
                else:
                    metrics["accuracy_ratio"] = 0.0
                
                print(f"   🎯 Auto: {auto_count}, Manual: {manual_count}, Ratio: {metrics['accuracy_ratio']}%")
                
                # Check for weak signatures (speakers not in voice_signatures folder)
                for speaker_id, name in voice_map.items():
                    # Check if this speaker has a signature file
                    has_signature = any(
                        sig.get('name', '').lower() == name.lower() 
                        for sig in voice_signatures
                    ) if voice_signatures else False
                    
                    if not has_signature:
                        metrics["weak_signatures"].append({
                            "name": name,
                            "reason": "אין קובץ חתימה בתיקייה"
                        })
                
            except Exception as e:
                print(f"   ⚠️ Could not read memory: {e}")
                import traceback
                traceback.print_exc()
            
            # Generate recommendations based on actual data
            if metrics["total_speakers"] == 0 and metrics["voice_signatures_count"] == 0:
                metrics["recommendations"].append(
                    "💡 טרם נרשמו דוברים - התחל לזהות אנשים בהקלטות"
                )
            elif metrics["accuracy_ratio"] < 50 and metrics["total_speakers"] > 0:
                metrics["recommendations"].append(
                    "🔴 יחס זיהוי נמוך - שקול להקליט דגימות קול נוספות"
                )
            
            if len(metrics["weak_signatures"]) > 0:
                metrics["recommendations"].append(
                    f"⚠️ יש {len(metrics['weak_signatures'])} דוברים ללא חתימה"
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
        Directly queries Google Drive for accurate counts.
        """
        print("🧹 Analyzing data hygiene...")
        
        hygiene = {
            "transcript_count": 0,
            "voice_signatures_count": 0,
            "audio_archive_count": 0,
            "oldest_transcript": None,
            "newest_transcript": None,
            "archive_threshold": 100,
            "needs_archiving": False,
            "recommendations": [],
            "drive_connected": False
        }
        
        try:
            if not drive_service or not drive_service.is_configured:
                return {"error": "Drive service not configured", "hygiene": hygiene}
            
            hygiene["drive_connected"] = True
            print("   ✅ Drive service connected")
            
            # Get transcripts count
            try:
                transcripts = drive_service.get_recent_transcripts(limit=200)
                hygiene["transcript_count"] = len(transcripts) if transcripts else 0
                print(f"   📄 Transcripts: {hygiene['transcript_count']}")
                
                if transcripts and len(transcripts) > 0:
                    # Get dates
                    sorted_transcripts = sorted(
                        transcripts, 
                        key=lambda x: x.get('created_time', ''),
                        reverse=True
                    )
                    hygiene["newest_transcript"] = sorted_transcripts[0].get('created_time', 'Unknown')
                    hygiene["oldest_transcript"] = sorted_transcripts[-1].get('created_time', 'Unknown')
                    print(f"   📅 Newest: {hygiene['newest_transcript']}")
                    print(f"   📅 Oldest: {hygiene['oldest_transcript']}")
            except Exception as e:
                print(f"   ⚠️ Could not get transcripts: {e}")
            
            # Get voice signatures count
            try:
                signatures = drive_service.get_voice_signatures(max_signatures=50)
                hygiene["voice_signatures_count"] = len(signatures) if signatures else 0
                print(f"   🎤 Voice signatures: {hygiene['voice_signatures_count']}")
            except Exception as e:
                print(f"   ⚠️ Could not get voice signatures: {e}")
            
            # Check if archiving needed
            if hygiene["transcript_count"] > hygiene["archive_threshold"]:
                hygiene["needs_archiving"] = True
                excess = hygiene["transcript_count"] - hygiene["archive_threshold"]
                hygiene["recommendations"].append(
                    f"🗄️ יש {excess} תמלולים מעבר לסף - מומלץ לארכב"
                )
            
            # Check for old transcripts
            if hygiene["oldest_transcript"] and hygiene["oldest_transcript"] != 'Unknown':
                try:
                    oldest_date = datetime.fromisoformat(
                        hygiene["oldest_transcript"].replace('Z', '+00:00')
                    )
                    age_days = (datetime.now(timezone.utc) - oldest_date).days
                    if age_days > 30:
                        hygiene["recommendations"].append(
                            f"📅 יש תמלולים בני {age_days} ימים"
                        )
                except Exception as e:
                    print(f"   ⚠️ Could not parse date: {e}")
            
            if hygiene["transcript_count"] == 0:
                hygiene["recommendations"].append(
                    "💡 אין תמלולים - התחל להקליט שיחות"
                )
            
            return {
                "success": True,
                "hygiene": hygiene
            }
            
        except Exception as e:
            logger.error(f"❌ Data hygiene analysis failed: {e}")
            import traceback
            traceback.print_exc()
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
        Uses Israel timezone for timestamps.
        """
        print("📝 Generating strategic report...")
        
        report_parts = []
        israel_time = get_israel_time()
        
        # Header
        report_parts.append("🏗️ *דו״ח ארכיטקטורה שבועי*")
        report_parts.append(f"📅 {israel_time.strftime('%d/%m/%Y %H:%M')} (שעון ישראל)")
        report_parts.append("")
        
        # ============== SYSTEM STATUS ==============
        report_parts.append("═" * 25)
        report_parts.append("🛡️ *סטטוס מערכת*")
        report_parts.append("")
        
        metrics = voice_metrics.get('metrics', {})
        hygiene = data_hygiene.get('hygiene', {})
        
        # Connection status
        if metrics.get('drive_connected') or hygiene.get('drive_connected'):
            report_parts.append("✅ חיבור ל-Drive: פעיל")
        else:
            report_parts.append("❌ חיבור ל-Drive: לא פעיל")
        
        # Stats
        total_speakers = metrics.get('total_speakers', 0)
        voice_sigs = metrics.get('voice_signatures_count', 0) or hygiene.get('voice_signatures_count', 0)
        transcript_count = hygiene.get('transcript_count', 0)
        accuracy = metrics.get('accuracy_ratio', 0)
        
        report_parts.append(f"👥 דוברים מזוהים: *{total_speakers}*")
        report_parts.append(f"🎤 חתימות קול: *{voice_sigs}*")
        report_parts.append(f"📄 תמלולים: *{transcript_count}*")
        
        if accuracy > 0:
            report_parts.append(f"🎯 יחס זיהוי אוטומטי: *{accuracy}%*")
        
        # Weak signatures
        weak_count = len(metrics.get('weak_signatures', []))
        if weak_count > 0:
            report_parts.append(f"⚠️ דגימות חלשות: *{weak_count}*")
            for weak in metrics.get('weak_signatures', [])[:3]:
                report_parts.append(f"   • {weak['name']}: {weak['reason']}")
        
        report_parts.append("")
        
        # ============== MARKET NEWS ==============
        report_parts.append("═" * 25)
        report_parts.append("🌍 *חדשות מהשוק*")
        report_parts.append("")
        
        if external_scan.get('success'):
            findings = external_scan.get('findings', '')
            # Limit to ~600 chars for WhatsApp
            if len(findings) > 600:
                findings = findings[:600] + "..."
            report_parts.append(findings)
        else:
            error = external_scan.get('error', 'Unknown error')
            report_parts.append(f"⚠️ סריקה חלקית: {error[:50]}")
        
        report_parts.append("")
        
        # ============== DATA HYGIENE ==============
        report_parts.append("═" * 25)
        report_parts.append("🧹 *היגיינת נתונים*")
        report_parts.append("")
        
        if hygiene.get('needs_archiving'):
            report_parts.append("🔴 *נדרש ארכוב!*")
        elif transcript_count > 0:
            report_parts.append("✅ נפח תקין")
        else:
            report_parts.append("📭 טרם נוצרו תמלולים")
        
        for rec in hygiene.get('recommendations', [])[:3]:
            report_parts.append(f"   {rec}")
        
        report_parts.append("")
        
        # ============== STRATEGIC RECOMMENDATION ==============
        report_parts.append("═" * 25)
        report_parts.append("💡 *המלצה אסטרטגית*")
        report_parts.append("")
        
        # Determine recommendation based on ACTUAL data
        has_data = total_speakers > 0 or transcript_count > 0
        
        if not has_data:
            # No data yet - encourage usage
            report_parts.append("🆕 *START* - התחל להשתמש במערכת")
            report_parts.append("   שלח הקלטות כדי לבנות את בסיס הנתונים")
        elif accuracy >= 70:
            report_parts.append("✅ *STAY* - הסטאק הנוכחי עובד מצוין")
            report_parts.append("   Gemini מספק ביצועים טובים")
        elif accuracy >= 40 and accuracy < 70:
            report_parts.append("🟡 *OPTIMIZE* - יש מקום לשיפור")
            report_parts.append("   הוסף דגימות קול נוספות לפני החלטה על מעבר")
        elif accuracy > 0 and accuracy < 40:
            report_parts.append("🔴 *CONSIDER MOVE* - יחס זיהוי נמוך")
            report_parts.append("   שקול לבדוק Deepgram או AssemblyAI")
        else:
            # No accuracy data but has speakers
            report_parts.append("🟡 *MONITOR* - אסוף עוד נתונים")
            report_parts.append("   ממשיך לנטר את הביצועים")
        
        report_parts.append("")
        report_parts.append("_סריקה אוטומטית כל יום שישי 13:00_")
        
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
        israel_time = get_israel_time()
        
        print("\n" + "=" * 60)
        print("🏗️ WEEKLY ARCHITECTURE AUDIT STARTED")
        print(f"⏰ {israel_time.strftime('%d/%m/%Y %H:%M')} (Israel Time)")
        print("=" * 60)
        
        start_time = datetime.now(timezone.utc)
        
        # Check Drive service
        if drive_service:
            print(f"📁 Drive service: {'Configured' if drive_service.is_configured else 'Not configured'}")
        else:
            print("📁 Drive service: Not provided")
        
        # Step 1: External Scan
        print("\n📡 Step 1/4: External market scan...")
        external_scan = self.research_ai_updates()
        print(f"   Result: {'Success' if external_scan.get('success') else 'Failed'}")
        
        # Step 2: Competitor Comparison
        print("\n⚔️ Step 2/4: Competitor comparison...")
        comparison = self.compare_to_competitors()
        print(f"   Result: {'Success' if comparison.get('success') else 'Failed'}")
        
        # Step 3: Voice Identification Analysis
        print("\n📊 Step 3/4: Voice identification analysis...")
        voice_metrics = self.analyze_voice_identification(drive_service)
        print(f"   Result: {'Success' if voice_metrics.get('success') else 'Failed'}")
        
        # Step 4: Data Hygiene
        print("\n🧹 Step 4/4: Data hygiene check...")
        data_hygiene = self.analyze_data_hygiene(drive_service)
        print(f"   Result: {'Success' if data_hygiene.get('success') else 'Failed'}")
        
        # Generate Report
        print("\n📝 Generating strategic report...")
        report = self.generate_strategic_report(
            external_scan=external_scan,
            comparison=comparison,
            voice_metrics=voice_metrics,
            data_hygiene=data_hygiene
        )
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Audit completed in {duration:.1f} seconds")
        print("=" * 60 + "\n")
        
        return {
            "success": True,
            "report": report,
            "duration_seconds": duration,
            "timestamp": israel_time.isoformat(),
            "data": {
                "external_scan": external_scan,
                "comparison": comparison,
                "voice_metrics": voice_metrics,
                "data_hygiene": data_hygiene
            }
        }


# Singleton instance
architecture_audit_service = ArchitectureAuditService()
