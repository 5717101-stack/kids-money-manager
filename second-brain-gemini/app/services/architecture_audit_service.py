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
        self.model = None
        self.model_name = None
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
            # Try models in order of preference (same order as gemini_service.py)
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
                    logger.info(f"✅ Audit service using model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️  Could not init {model_name}: {e}")
                    continue
            
            if not self.model:
                logger.error("❌ Could not init any model for audit service")
        else:
            logger.warning("⚠️  Google API key not set - Audit service limited")
        
        self.is_configured = bool(self.api_key and self.model)
        
        # Store recent errors for health reporting
        self.last_expert_error: Optional[str] = None
        self.last_expert_error_time: Optional[datetime] = None
        
        # Safety settings to prevent content blocking
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    
    # ================================================================
    # SYSTEM HEALTH CHECK
    # ================================================================
    
    def check_system_health(self, drive_service=None) -> Dict[str, Any]:
        """
        Comprehensive system health diagnostic.
        
        Checks:
        1. Gemini API connectivity (ping with simple prompt)
        2. Google Drive access (list files in key folders)
        3. Environment variables (critical keys)
        4. Recent errors from expert analysis
        
        Returns:
            Dict with health status for each component
        """
        israel_time = get_israel_time()
        
        health = {
            "timestamp": israel_time.isoformat(),
            "timestamp_display": israel_time.strftime('%d/%m/%Y %H:%M'),
            "gemini": {"status": "unknown"},
            "drive": {"status": "unknown", "transcripts": 0, "voice_signatures": 0},
            "env": {"all_present": False, "missing": []},
            "errors": []
        }
        
        # 1. Gemini API Connectivity
        print("🏥 [Health] Checking Gemini API...")
        try:
            import time
            start = time.time()
            response = self.model.generate_content(
                "שלום, החזר 'OK'",
                generation_config={'max_output_tokens': 10},
                safety_settings=self.safety_settings
            )
            elapsed = (time.time() - start) * 1000  # ms
            
            # Safe text extraction
            try:
                text = response.text.strip() if response.text else ""
            except (ValueError, AttributeError):
                text = ""
            
            if text:
                health["gemini"] = {
                    "status": "ok",
                    "model": self.model_name,
                    "response_time_ms": round(elapsed)
                }
                print(f"   ✅ Gemini OK ({self.model_name}, {elapsed:.0f}ms)")
            else:
                health["gemini"] = {
                    "status": "error",
                    "model": self.model_name,
                    "error": "Empty response"
                }
                print(f"   ⚠️ Gemini returned empty response")
                
        except Exception as e:
            error_msg = str(e)[:100]
            health["gemini"] = {
                "status": "error",
                "model": self.model_name,
                "error": error_msg
            }
            print(f"   ❌ Gemini error: {error_msg}")
        
        # 2. Google Drive Access
        print("🏥 [Health] Checking Google Drive...")
        if drive_service and drive_service.is_configured:
            try:
                # Count transcripts
                transcripts = 0
                voice_sigs = 0
                
                if hasattr(drive_service, 'get_voice_signatures'):
                    try:
                        sigs = drive_service.get_voice_signatures(max_signatures=50)
                        voice_sigs = len(sigs) if sigs else 0
                    except:
                        pass
                
                # Count transcript files using memory
                if hasattr(drive_service, 'get_memory'):
                    try:
                        memory = drive_service.get_memory()
                        chat_history = memory.get('chat_history', [])
                        # Count audio interactions
                        transcripts = sum(1 for h in chat_history if h.get('type') == 'audio')
                    except:
                        pass
                
                health["drive"] = {
                    "status": "connected",
                    "transcripts": transcripts,
                    "voice_signatures": voice_sigs
                }
                print(f"   ✅ Drive connected (transcripts: {transcripts}, voice sigs: {voice_sigs})")
                
            except Exception as e:
                health["drive"] = {
                    "status": "error",
                    "error": str(e)[:100]
                }
                print(f"   ❌ Drive error: {e}")
        else:
            health["drive"] = {"status": "not_configured"}
            print("   ⚠️ Drive not configured")
        
        # 3. Environment Variables
        print("🏥 [Health] Checking environment...")
        from app.core.config import settings
        
        critical_vars = {
            "GOOGLE_API_KEY": bool(settings.google_api_key),
            "DRIVE_FOLDER_ID": bool(settings.drive_memory_folder_id),
            "WHATSAPP_TOKEN": bool(settings.whatsapp_cloud_api_token),
            "WHATSAPP_PHONE_ID": bool(settings.whatsapp_phone_number_id)
        }
        
        missing = [k for k, v in critical_vars.items() if not v]
        health["env"] = {
            "all_present": len(missing) == 0,
            "missing": missing,
            "checked": list(critical_vars.keys())
        }
        
        if missing:
            print(f"   ⚠️ Missing: {', '.join(missing)}")
        else:
            print(f"   ✅ All critical env vars present")
        
        # 4. Recent Errors
        if self.last_expert_error:
            health["errors"].append({
                "source": "expert_analysis",
                "error": self.last_expert_error,
                "time": self.last_expert_error_time.isoformat() if self.last_expert_error_time else None
            })
            print(f"   ⚠️ Recent error: {self.last_expert_error[:50]}...")
        else:
            print(f"   ✅ No recent errors")
        
        return health
    
    def record_expert_error(self, error: str):
        """Record an expert analysis error for health reporting."""
        self.last_expert_error = error
        self.last_expert_error_time = get_israel_time()
    
    def clear_expert_error(self):
        """Clear the recorded error after successful analysis."""
        self.last_expert_error = None
        self.last_expert_error_time = None
    
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
                },
                safety_settings=self.safety_settings
            )
            
            # Safe extraction of response.text (may throw if blocked)
            try:
                findings = response.text.strip() if response.text else ""
            except (ValueError, AttributeError) as text_err:
                print(f"   ⚠️ response.text access failed: {text_err}")
                findings = ""
            
            if not findings or len(findings) < 20:
                return {
                    "success": False,
                    "findings": "⚠️ סריקת שוק לא זמינה כרגע",
                    "timestamp": get_israel_time().isoformat()
                }
            
            return {
                "success": True,
                "findings": findings,
                "timestamp": get_israel_time().isoformat()
            }
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ External scan failed: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Provide graceful fallback message instead of just showing error
            fallback_msg = ""
            if "404" in error_str or "not found" in error_str.lower():
                fallback_msg = "⚠️ מודל ה-AI לא זמין כרגע. מנסה שוב בסריקה הבאה."
            elif "quota" in error_str.lower() or "rate" in error_str.lower():
                fallback_msg = "⚠️ הגעתי למכסת השימוש. ננסה שוב מאוחר יותר."
            elif "connection" in error_str.lower() or "timeout" in error_str.lower():
                fallback_msg = "⚠️ בעיית חיבור לשרת. בדוק את החיבור לאינטרנט."
            else:
                fallback_msg = f"⚠️ שגיאה טכנית: {error_str[:50]}"
            
            return {
                "success": False,
                "error": error_str,
                "findings": fallback_msg + "\n\n💡 *מידע כללי:*\n• Gemini 2.0 - מוביל בזיהוי דוברים בעברית\n• Deepgram Nova-2 - אלטרנטיבה מהירה\n• AssemblyAI - טוב ל-RAG"
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
                },
                safety_settings=self.safety_settings
            )
            
            # Safe extraction of response.text
            try:
                comparison = response.text.strip() if response.text else ""
            except (ValueError, AttributeError) as text_err:
                print(f"   ⚠️ response.text access failed: {text_err}")
                comparison = ""
            
            if not comparison or len(comparison) < 20:
                return {
                    "success": False,
                    "comparison": "⚠️ השוואה לא זמינה כרגע",
                    "timestamp": get_israel_time().isoformat()
                }
            
            return {
                "success": True,
                "comparison": comparison,
                "timestamp": get_israel_time().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Competitor comparison failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "comparison": "⚠️ השוואה לא זמינה כרגע"
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
            voice_signatures = []
            try:
                # Debug: Print folder ID being scanned
                if hasattr(drive_service, '_ensure_voice_signatures_folder') and drive_service.service:
                    folder_id = drive_service._ensure_voice_signatures_folder()
                    print(f"   📁 Voice Signatures folder ID: {folder_id}")
                
                voice_signatures = drive_service.get_voice_signatures(max_signatures=50)
                metrics["voice_signatures_count"] = len(voice_signatures)
                print(f"   🎤 Voice signatures found: {len(voice_signatures)}")
                
                # List signature names
                for sig in voice_signatures[:5]:
                    print(f"      - {sig.get('name', 'unknown')}")
                    
            except Exception as e:
                print(f"   ⚠️ Could not get voice signatures: {e}")
            
            # Method 2: Get voice_map from memory
            try:
                memory = drive_service.get_memory()
                user_profile = memory.get('user_profile', {})
                voice_map = user_profile.get('voice_map', {})
                
                # Count only identified speakers (exclude "Unknown" and empty names)
                identified_speakers = {
                    k: v for k, v in voice_map.items() 
                    if v and v.lower() not in ['unknown', 'לא ידוע', '']
                }
                unknown_speakers = len(voice_map) - len(identified_speakers)
                
                metrics["total_speakers"] = len(identified_speakers)
                print(f"   👥 Identified speakers: {len(identified_speakers)} (+ {unknown_speakers} unknown)")
                
                # List the identified speakers
                if identified_speakers:
                    for speaker_id, name in list(identified_speakers.items())[:5]:
                        print(f"      - {speaker_id}: {name}")
                
                # Get chat history for context
                chat_history = memory.get('chat_history', [])
                print(f"   💬 Chat history entries: {len(chat_history)}")
                
                # Count identification events from chat
                # Look for patterns indicating speaker learning
                auto_count = 0
                manual_count = 0
                
                for interaction in chat_history[-100:]:
                    content = str(interaction).lower()
                    # Auto-identified patterns (system recognized)
                    if 'זוהה כ' in content or 'מזהה את' in content or 'speaker_' in content:
                        auto_count += 1
                    # Manually tagged patterns (user taught)
                    if 'זה ' in content and ('אבא' in content or 'אמא' in content or 'סבא' in content or 'סבתא' in content):
                        manual_count += 1
                    if 'למדתי' in content or 'נשמר' in content:
                        manual_count += 1
                
                # If we have identified speakers, infer identification
                if len(identified_speakers) > 0 and auto_count == 0 and manual_count == 0:
                    # Assume these were manually identified if we have names
                    manual_count = len(identified_speakers)
                    print(f"   ℹ️  Inferred {manual_count} manual identifications from voice_map")
                
                metrics["auto_identified"] = auto_count
                metrics["manually_tagged"] = manual_count
                
                # Calculate accuracy ratio
                total_identifications = auto_count + manual_count
                if total_identifications > 0:
                    metrics["accuracy_ratio"] = round(auto_count / total_identifications * 100, 1)
                elif len(identified_speakers) > 0:
                    # Have speakers but no auto-detection data
                    metrics["accuracy_ratio"] = 0.0  # All were manual
                else:
                    metrics["accuracy_ratio"] = 0.0
                
                print(f"   🎯 Auto: {auto_count}, Manual: {manual_count}, Ratio: {metrics['accuracy_ratio']}%")
                
                # Check for weak signatures (speakers not in voice_signatures folder)
                if voice_signatures:
                    signature_names = [
                        sig.get('name', '').lower().replace('.mp3', '').replace('_', ' ') 
                        for sig in voice_signatures
                    ]
                    for speaker_id, name in identified_speakers.items():
                        has_signature = name.lower() in signature_names
                        if not has_signature:
                            metrics["weak_signatures"].append({
                                "name": name,
                                "reason": "אין קובץ חתימת קול"
                            })
                else:
                    # No signatures at all - all speakers are weak
                    for speaker_id, name in identified_speakers.items():
                        metrics["weak_signatures"].append({
                            "name": name,
                            "reason": "לא נמצאו חתימות קול"
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
            
            # Get transcripts count - try multiple methods
            try:
                # Method 1: Use get_recent_transcripts (looks for .json files)
                transcripts = drive_service.get_recent_transcripts(limit=200)
                json_count = len(transcripts) if transcripts else 0
                print(f"   📄 JSON transcripts: {json_count}")
                
                # Method 2: Also count .txt transcript files directly
                txt_count = 0
                try:
                    if hasattr(drive_service, '_ensure_transcripts_folder') and drive_service.service:
                        folder_id = drive_service._ensure_transcripts_folder()
                        if folder_id:
                            print(f"   📁 Transcripts folder ID: {folder_id}")
                            # Count .txt files
                            query = f"'{folder_id}' in parents and mimeType = 'text/plain' and trashed = false"
                            results = drive_service.service.files().list(
                                q=query,
                                pageSize=500,
                                fields="files(id)"
                            ).execute()
                            txt_count = len(results.get('files', []))
                            print(f"   📄 TXT transcripts: {txt_count}")
                except Exception as txt_error:
                    print(f"   ⚠️ Could not count TXT files: {txt_error}")
                
                hygiene["transcript_count"] = json_count + txt_count
                print(f"   📄 Total transcripts: {hygiene['transcript_count']}")
                
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
        data_hygiene: Dict[str, Any],
        health_status: Dict[str, Any] = None
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
        
        # ============== SYSTEM HEALTH DASHBOARD (NEW) ==============
        report_parts.append("═" * 25)
        report_parts.append("🏥 *בריאות המערכת*")
        report_parts.append("")
        
        if health_status:
            # Gemini status
            gemini = health_status.get('gemini', {})
            gemini_status = gemini.get('status', 'unknown')
            if gemini_status == 'ok':
                model = gemini.get('model', 'N/A')
                time_ms = gemini.get('response_time_ms', 0)
                report_parts.append(f"✅ Gemini API: תקין ({model}, {time_ms}ms)")
            else:
                error = gemini.get('error', 'Unknown')[:30]
                report_parts.append(f"❌ Gemini API: שגיאה ({error})")
            
            # Drive status
            drive = health_status.get('drive', {})
            drive_status = drive.get('status', 'unknown')
            if drive_status == 'connected':
                transcripts = drive.get('transcripts', 0)
                sigs = drive.get('voice_signatures', 0)
                report_parts.append(f"✅ Google Drive: מחובר ({transcripts} תמלולים, {sigs} חתימות)")
            elif drive_status == 'not_configured':
                report_parts.append("⚠️ Google Drive: לא מוגדר")
            else:
                report_parts.append(f"❌ Google Drive: {drive.get('error', 'שגיאה')[:30]}")
            
            # Environment
            env = health_status.get('env', {})
            if env.get('all_present'):
                report_parts.append("✅ משתני סביבה: תקינים")
            else:
                missing = env.get('missing', [])
                report_parts.append(f"⚠️ משתנים חסרים: {', '.join(missing[:3])}")
            
            # Recent errors
            errors = health_status.get('errors', [])
            if errors:
                latest = errors[0]
                report_parts.append(f"⚠️ שגיאה אחרונה: {latest.get('error', '')[:40]}")
            else:
                report_parts.append("✅ שגיאות אחרונות: אין")
        else:
            report_parts.append("⚠️ בדיקת בריאות לא זמינה")
        
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
        
        # Show actual file counts
        report_parts.append(f"📁 קבצי תמלול: *{transcript_count}*")
        report_parts.append(f"🎤 קבצי חתימות קול: *{voice_sigs}*")
        
        if hygiene.get('needs_archiving'):
            threshold = hygiene.get('archive_threshold', 100)
            report_parts.append(f"🔴 *נדרש ארכוב!* (סף: {threshold})")
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
        
        # Step 0: System Health Check (NEW)
        print("\n🏥 Step 0/5: System Health Check...")
        health_status = self.check_system_health(drive_service)
        print(f"   Gemini: {health_status['gemini'].get('status', 'unknown')}")
        print(f"   Drive: {health_status['drive'].get('status', 'unknown')}")
        print(f"   Env: {'OK' if health_status['env'].get('all_present') else 'Missing vars'}")
        
        # Step 1: External Scan
        print("\n📡 Step 1/5: External market scan...")
        external_scan = self.research_ai_updates()
        print(f"   Result: {'Success' if external_scan.get('success') else 'Failed'}")
        
        # Step 2: Competitor Comparison
        print("\n⚔️ Step 2/5: Competitor comparison...")
        comparison = self.compare_to_competitors()
        print(f"   Result: {'Success' if comparison.get('success') else 'Failed'}")
        
        # Step 3: Voice Identification Analysis
        print("\n📊 Step 3/5: Voice identification analysis...")
        voice_metrics = self.analyze_voice_identification(drive_service)
        print(f"   Result: {'Success' if voice_metrics.get('success') else 'Failed'}")
        
        # Step 4: Data Hygiene
        print("\n🧹 Step 4/5: Data hygiene check...")
        data_hygiene = self.analyze_data_hygiene(drive_service)
        print(f"   Result: {'Success' if data_hygiene.get('success') else 'Failed'}")
        
        # Generate Report (Step 5)
        print("\n📝 Step 5/5: Generating strategic report...")
        report = self.generate_strategic_report(
            external_scan=external_scan,
            comparison=comparison,
            voice_metrics=voice_metrics,
            data_hygiene=data_hygiene,
            health_status=health_status
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
                "health_status": health_status,
                "external_scan": external_scan,
                "comparison": comparison,
                "voice_metrics": voice_metrics,
                "data_hygiene": data_hygiene
            }
        }


# Singleton instance
architecture_audit_service = ArchitectureAuditService()
