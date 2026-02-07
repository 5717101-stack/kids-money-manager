"""
Service for handling Google Gemini AI operations.
"""

import json
import os
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import google.generativeai as genai

from app.core.config import settings
from app.prompts import SYSTEM_PROMPT, AUDIO_ANALYSIS_PROMPT, AUDIO_ANALYSIS_PROMPT_BASE, FORENSIC_ANALYST_PROMPT, COMBINED_DIARIZATION_EXPERT_PROMPT
from app.services.knowledge_base_service import get_system_instruction_block as get_kb_context


class GeminiService:
    """Service for Google Gemini AI operations."""
    
    @staticmethod
    def _fix_incomplete_json(text: str) -> str:
        """
        Try to fix incomplete JSON by removing incomplete properties.
        
        Strategy: If we're in the middle of a string, find the last complete property
        and remove everything after it, then close the JSON structure properly.
        
        Args:
            text: Incomplete JSON text
            
        Returns:
            Fixed JSON text
        """
        # Check if we're in the middle of a string
        quote_count = text.count('"')
        in_string = quote_count % 2 != 0
        
        if in_string:
            # We're in the middle of a string - need to remove the incomplete property
            # Find the last complete property by looking for the last comma before the incomplete string
            
            # Find the last colon (property value separator)
            last_colon = text.rfind(':')
            if last_colon > 0:
                # Find the property name (quote before colon)
                prop_start = text.rfind('"', 0, last_colon)
                if prop_start >= 0:
                    # Find the comma before this property (or opening brace if it's the first)
                    comma_before = text.rfind(',', 0, prop_start)
                    if comma_before >= 0:
                        # Remove everything from the comma onwards
                        text = text[:comma_before]
                    else:
                        # This is the first property in an object/array
                        # Find the opening brace or bracket
                        brace_before = text.rfind('{', 0, prop_start)
                        bracket_before = text.rfind('[', 0, prop_start)
                        if bracket_before > brace_before:
                            # Inside an array
                            text = text[:bracket_before + 1]
                        elif brace_before >= 0:
                            # Inside an object
                            text = text[:brace_before + 1]
        
        # Remove any trailing commas
        import re
        text = re.sub(r',\s*$', '', text)
        
        # Count braces and brackets (after removing incomplete properties)
        brace_count = text.count('{') - text.count('}')
        bracket_count = text.count('[') - text.count(']')
        
        # Close unclosed arrays first (they're inside objects)
        text += ']' * bracket_count
        
        # Then close unclosed objects
        text += '}' * brace_count
        
        return text
    
    @staticmethod
    def _fix_json_errors(text: str) -> str:
        """
        Try to fix common JSON errors.
        
        Args:
            text: JSON text with potential errors
            
        Returns:
            Fixed JSON text
        """
        import re
        # Remove trailing commas before } or ]
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        # Try to close unclosed strings
        text = GeminiService._fix_incomplete_json(text)
        
        return text
    
    def __init__(self):
        """Initialize Gemini service with API key."""
        if not settings.google_api_key:
            print("⚠️  WARNING: GOOGLE_API_KEY not set. Please set GOOGLE_API_KEY in environment variables.")
            print("   The service will start but Gemini analysis will not work until API key is configured.")
            self.model = None
            self.is_configured = False
            return
        
        genai.configure(api_key=settings.google_api_key)
        self.is_configured = True
        # Use gemini-2.5-pro (available model) or gemini-pro-latest as fallback
        model_name = getattr(settings, 'gemini_model', 'gemini-2.5-pro')
        # Map old model names to new ones
        if model_name in ['gemini-1.5-pro', 'gemini-1.5-pro-latest']:
            model_name = 'gemini-2.5-pro'
        self.model = genai.GenerativeModel(model_name)
        print(f"✅ Initialized Gemini model: {model_name}")
        self.uploaded_files = []
    
    def upload_and_wait(self, file_path: str, display_name: Optional[str] = None, mime_type: Optional[str] = None, max_wait: int = 300):
        """
        Upload a file and wait for it to be processed.
        
        Args:
            file_path: Path to the file to upload
            display_name: Display name for the file (safe to pass)
            mime_type: MIME type of the file (auto-detected if None)
            max_wait: Maximum time to wait for processing in seconds
        
        Returns:
            Refreshed File object with state='ACTIVE'
        """
        path = Path(file_path)
        display_name = display_name or path.name
        
        # Auto-detect MIME type if not provided
        if not mime_type:
            if path.suffix.lower() in ['.mp3', '.wav', '.m4a', '.ogg']:
                mime_type = f'audio/{path.suffix[1:]}'
            elif path.suffix.lower() in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif path.suffix.lower() == '.png':
                mime_type = 'image/png'
            else:
                mime_type = 'application/octet-stream'
        
        # Step 1: Upload - Let Google generate the ID (do NOT pass name=...)
        print(f"📤 Uploading {display_name}...")
        file_ref = genai.upload_file(
            path=file_path,
            display_name=display_name,
            mime_type=mime_type
        )
        
        # Step 2: Get the file ID from the returned object's name property
        # According to user instructions: "get the file.name property (this is the ID like 'files/123')"
        # We need to access .name to get the ID, but this might trigger get_file() internally
        # So we'll extract the ID from the name and use it for subsequent calls
        try:
            # Get the file ID - file_ref.name is like 'files/123'
            full_file_id = file_ref.name  # e.g., 'files/5ie9zz0xtcqc'
        except Exception as e:
            # If accessing .name fails, try extracting from URI as fallback
            print(f"   [WARN] Could not access file_ref.name, trying URI: {e}")
            uri = file_ref.uri
            if '/files/' in uri:
                file_id_only = uri.split('/files/')[-1].split('?')[0]
                full_file_id = f'files/{file_id_only}'
            else:
                raise ValueError(f"Could not extract file ID from name or URI")
        
        # Extract just the ID part (without 'files/' prefix) for get_file()
        if full_file_id.startswith('files/'):
            file_id_only = full_file_id[6:]  # Extract just '5ie9zz0xtcqc'
        else:
            file_id_only = full_file_id
        
        # Verify ID is not too long
        if len(file_id_only) > 40:
            raise ValueError(f"File ID too long: {len(file_id_only)} characters (max 40). ID: {file_id_only[:50]}")
        
        print(f"   File ID: {full_file_id} (ID only: {file_id_only}, length: {len(file_id_only)})")
        
        # Step 3: Wait for processing using just the ID part (without 'files/' prefix)
        # The API expects just the ID, not 'files/ID'
        start_time = time.time()
        while time.time() - start_time < max_wait:
            print(f"   [DEBUG] Calling genai.get_file with ID: '{file_id_only}'")
            import sys
            sys.stdout.flush()
            
            # Refresh the object using just the ID part (without 'files/' prefix)
            try:
                file_ref = genai.get_file(file_id_only)
            except Exception as e:
                print(f"   [ERROR] genai.get_file failed with: {e}")
                print(f"   [ERROR] file_id_only = '{file_id_only}' (length: {len(file_id_only)})")
                raise
            
            # Check state
            state = file_ref.state
            if hasattr(state, 'name'):
                state_name = state.name
            else:
                state_name = str(state)
            
            if state_name == "ACTIVE":
                print(f"✅ File {display_name} is ready (state: ACTIVE)")
                self.uploaded_files.append(file_ref)
                return file_ref
            elif state_name == "FAILED":
                raise ValueError(f"File {display_name} failed to process.")
            
            print(f"⏳ Processing {display_name}... (state: {state_name})")
            time.sleep(2)
        
        raise TimeoutError(f"File {display_name} processing timeout after {max_wait} seconds")
    
    def wait_for_processing(self, file_uri: str, max_wait: int = 300) -> bool:
        """
        Wait for an audio file to be processed (state='ACTIVE').
        
        Args:
            file_uri: URI of the uploaded file (or File object)
            max_wait: Maximum time to wait in seconds
        
        Returns:
            True if file is ready, False if timeout
        """
        start_time = time.time()
        
        # Debug: log what we received
        print(f"[WAIT] Entry - file_uri type: {type(file_uri)}")
        print(f"[WAIT] Has 'name': {hasattr(file_uri, 'name')}")
        print(f"[WAIT] Has 'uri': {hasattr(file_uri, 'uri')}")
        if hasattr(file_uri, 'name'):
            print(f"[WAIT] file_uri.name: '{file_uri.name}' (length: {len(file_uri.name)})")
        if hasattr(file_uri, 'uri'):
            print(f"[WAIT] file_uri.uri: '{file_uri.uri}'")
        
        # Extract file ID from File object or URI
        # genai.get_file() expects the full 'files/FILE_ID' format (not just FILE_ID)
        if hasattr(file_uri, 'name'):
            # File object - use the 'name' attribute directly (it's 'files/FILE_ID')
            file_name = file_uri.name
            # Use the full name (with 'files/' prefix) for get_file
            file_id_for_get = file_name
        elif hasattr(file_uri, 'uri'):
            # Has URI - extract file ID from URI and construct 'files/FILE_ID'
            uri = file_uri.uri
            if '/files/' in uri:
                file_id = uri.split('/files/')[-1].split('?')[0]  # Extract just the ID
                file_id_for_get = f'files/{file_id}'  # Add 'files/' prefix
            else:
                file_id_for_get = uri
        else:
            # String - extract file ID
            file_uri_str = str(file_uri)
            if '/files/' in file_uri_str:
                file_id = file_uri_str.split('/files/')[-1].split('?')[0]
                file_id_for_get = f'files/{file_id}'  # Add 'files/' prefix
            elif file_uri_str.startswith('files/'):
                file_id_for_get = file_uri_str  # Already has 'files/' prefix
            else:
                file_id_for_get = f'files/{file_uri_str}'  # Add 'files/' prefix
        
        # Extract just the ID part for logging (without 'files/' prefix)
        if file_id_for_get.startswith('files/'):
            file_id_only = file_id_for_get[6:]
        else:
            file_id_only = file_id_for_get
        
        # Ensure file_id_only is not too long (Gemini API limit is 40 chars)
        if len(file_id_only) > 40:
            raise ValueError(f"File ID too long: {len(file_id_only)} characters (max 40). File ID: {file_id_only[:50]}")
        
        print(f"[WAIT] Using file_id_for_get: '{file_id_for_get}' (ID only: '{file_id_only}', length: {len(file_id_only)})")
        import sys
        sys.stdout.flush()
        
        # Double-check: make sure we're not passing display_name by mistake
        if hasattr(file_uri, 'display_name'):
            print(f"[WAIT] WARNING: file_uri has display_name: '{file_uri.display_name}' (length: {len(file_uri.display_name)})")
            if len(file_uri.display_name) > 40:
                print(f"[WAIT] ERROR: display_name is longer than 40 chars! This might be the issue.")
        
        while time.time() - start_time < max_wait:
            # genai.get_file() can accept either 'files/FILE_ID' or just 'FILE_ID'
            # Based on our tests, both work. Let's try with just the ID first.
            print(f"[WAIT] Calling genai.get_file with file_id_only: '{file_id_only}' (length: {len(file_id_only)})")
            sys.stdout.flush()
            try:
                # Try with just the file_id (without 'files/' prefix) first
                file = genai.get_file(file_id_only)
            except Exception as e:
                error_str = str(e)
                # Handle connection errors with retry
                if 'Connection reset' in error_str or '503' in error_str or 'recvmsg' in error_str:
                    print(f"[WAIT] ⚠️  Connection error (will retry): {error_str}")
                    time.sleep(5)  # Wait before retry
                    continue  # Retry the loop
                print(f"[WAIT] ❌ Error calling get_file('{file_id}'): {e}")
                raise
            
            if file.state == 'ACTIVE':
                print(f"✅ File ready: {file_id}")
                return True
            elif file.state == 'FAILED':
                raise ValueError(f"File processing failed: {file_id}")
            
            print(f"⏳ Waiting for file processing... ({file.state})")
            time.sleep(2)
        
        raise TimeoutError(f"File processing timeout: {file_id}")
    
    def chat_with_memory(
        self,
        user_message: str,
        chat_history: List[Dict[str, Any]] = None,
        user_profile: Dict[str, Any] = None,
        current_session: Dict[str, Any] = None,
        recent_transcripts: List[Dict[str, Any]] = None
    ) -> str:
        """
        Chat with Gemini using conversation history, user profile, and RAG context.
        
        Args:
            user_message: Current user message
            chat_history: List of previous interactions, each with 'user_message' and 'ai_response'
            user_profile: Dictionary containing user profile data (name, family members, etc.)
            current_session: Most recent audio session context (summary, speakers, segments)
            recent_transcripts: List of recent transcript data for deep search
        
        Returns:
            AI response text
        """
        chat_history = chat_history or []
        user_profile = user_profile or {}
        current_session = current_session or {}
        recent_transcripts = recent_transcripts or []
        
        # Check if service is configured
        if not self.is_configured or self.model is None:
            raise ValueError(
                "GOOGLE_API_KEY is not configured. "
                "Please set GOOGLE_API_KEY in environment variables."
            )
        
        # Build conversation context
        contents = []
        
        # CRITICAL: Dynamically construct System Prompt with user profile
        system_instruction = SYSTEM_PROMPT
        
        # Append user profile to system instructions if available
        if user_profile:
            user_profile_json = json.dumps(user_profile, indent=2, ensure_ascii=False)
            system_instruction += f"""

=== USER PROFILE / CONTEXT ===
Here is structured data about the user. You MUST use this to answer personal questions accurately:

{user_profile_json}

**Important:** When the user asks personal questions (e.g., "Who is my son?", "What is my name?", "Tell me about my family"), you MUST reference this profile data to provide accurate answers.
"""
            
            # VOICE MAP: Explain speaker ID mappings if available
            voice_map = user_profile.get('voice_map', {})
            if voice_map:
                voice_map_str = json.dumps(voice_map, ensure_ascii=False, indent=2)
                system_instruction += f"""

=== VOICE MAP (Speaker Identification) ===
When analyzing transcripts, use this mapping to understand who generic speaker IDs refer to:

{voice_map_str}

**Example:** If a transcript contains "Unknown Speaker 2", and voice_map has {{"unknown speaker 2": "שי"}}, 
then "Unknown Speaker 2" is actually "שי".

Use this mapping to provide accurate answers about conversations and who said what.
"""
                print(f"🎤 Voice map injected ({len(voice_map)} mappings)")
            
            print(f"👤 User profile injected into system prompt ({len(user_profile)} keys)")
        
        # ================================================================
        # WORKING MEMORY: Zero Latency access to the conversation that just ended
        # This is the PRIMARY source for questions about "the conversation"
        # ================================================================
        if current_session and current_session.get('summary'):
            session_summary = current_session.get('summary', '')
            session_speakers = current_session.get('speakers', [])
            session_timestamp = current_session.get('timestamp', '')
            session_segments = current_session.get('segments', [])
            identified_speakers = current_session.get('identified_speakers', {})
            current_voice_map = current_session.get('current_voice_map', {})
            
            system_instruction += f"""

=== 🧠 WORKING MEMORY (PRIORITY 1 - Check This FIRST!) ===
This is the conversation that JUST ENDED. It may not be in Drive yet.

**Summary:** {session_summary}
**Participants:** {', '.join(session_speakers) if session_speakers else 'Participants being identified'}
**Timestamp:** {session_timestamp}

**REAL-TIME SPEAKER IDENTIFICATIONS:**
Even if the transcript below shows "Unknown Speaker X", use this mapping to know who they really are:
{json.dumps(current_voice_map, ensure_ascii=False, indent=2) if current_voice_map else "No identifications yet"}

**⚠️ CRITICAL INSTRUCTION:**
When the user asks about "the conversation", "what we talked about", "what did we decide", "מה אמרנו":
1. FIRST: Search this Working Memory (the conversation that just ended)
2. ONLY IF not found here: Search the Drive transcripts below

**Full Transcript (Zero Latency):**
"""
            # Add full transcript segments with real-time speaker resolution
            if session_segments:
                for seg in session_segments[:30]:  # Increased limit for full context
                    raw_speaker = seg.get('speaker', 'Unknown')
                    # Try to resolve speaker using voice_map
                    resolved_speaker = current_voice_map.get(raw_speaker.lower(), raw_speaker)
                    text = seg.get('text', '')
                    system_instruction += f"- {resolved_speaker}: {text}\n"
            
            system_instruction += """
---
"""
            print(f"🧠 WORKING MEMORY injected:")
            print(f"   Summary: {len(session_summary)} chars")
            print(f"   Segments: {len(session_segments)} entries")
            print(f"   Voice map: {current_voice_map}")
        
        # RECENT TRANSCRIPTS: Deep search context (PRIORITY 2 - Only if not in Working Memory)
        if recent_transcripts:
            system_instruction += f"""

=== 📁 DRIVE TRANSCRIPTS (PRIORITY 2 - Search Only If Not In Working Memory) ===
These are older conversations from Google Drive. 
Note: The Working Memory above may have more recent data not yet synced to Drive.

"""
            for i, transcript in enumerate(recent_transcripts[:3], 1):  # Limit to 3
                filename = transcript.get('filename', 'Unknown')
                created_time = transcript.get('created_time', '')
                content = transcript.get('content', {})
                segments = content.get('segments', [])
                summary = content.get('summary', '')
                
                system_instruction += f"""
--- Transcript {i}: {filename} ({created_time}) ---
Summary: {summary}

"""
                for seg in segments[:15]:  # Limit segments per transcript
                    speaker = seg.get('speaker', 'Unknown')
                    text = seg.get('text', '')
                    system_instruction += f"{speaker}: {text}\n"
            
            print(f"📚 Recent transcripts injected ({len(recent_transcripts)} files)")
        
        # Inject Knowledge Base context into regular chat as well
        kb_block = get_kb_context()
        if kb_block:
            system_instruction += "\n" + kb_block
            print(f"📚 Knowledge Base context injected into chat ({len(kb_block)} chars)")
        
        # Add enhanced system prompt
        contents.append(system_instruction)
        
        # Add chat history if available
        if chat_history:
            contents.append("\n## Previous Conversation History:\n")
            for i, interaction in enumerate(chat_history, 1):
                user_msg = interaction.get('user_message', '')
                ai_resp = interaction.get('ai_response', '')
                timestamp = interaction.get('timestamp', '')
                
                contents.append(f"\n### Conversation {i} ({timestamp}):\n")
                contents.append(f"**User:** {user_msg}\n")
                contents.append(f"**AI:** {ai_resp}\n")
        
        # Add current user message
        contents.append(f"\n## Current User Message:\n{user_message}")
        
        # Add instruction for natural response
        contents.append("\n\nPlease provide a natural, conversational response. Do NOT output JSON unless explicitly asked. Respond in Hebrew (or English if the user wrote in English).")
        
        print(f"💬 Chatting with Gemini (history: {len(chat_history)} entries)")
        
        # Generate response with retry logic
        max_retries = 3
        retry_delay = 5
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 Attempt {attempt + 1}/{max_retries}: Calling model.generate_content...")
                response = self.model.generate_content(
                    contents,
                    generation_config={'max_output_tokens': 2048},
                    request_options={'timeout': 120}
                )
                print(f"✅ Successfully received response from Gemini")
                break
            except Exception as e:
                error_str = str(e)
                is_connection_error = (
                    'Connection reset' in error_str or 
                    '503' in error_str or 
                    'recvmsg' in error_str or 
                    'Connection' in error_str or
                    'timeout' in error_str.lower()
                )
                
                if is_connection_error and attempt < max_retries - 1:
                    print(f"⚠️  Connection error (attempt {attempt + 1}/{max_retries}): {error_str[:200]}")
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    print(f"❌ Error generating content: {error_str}")
                    raise
        
        if response is None:
            raise RuntimeError("Failed to generate content after all retries")
        
        # Extract response text with proper error handling
        try:
            return response.text.strip()
        except ValueError as e:
            print(f"⚠️  Gemini response.text accessor failed: {e}")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                feedback = response.prompt_feedback
                if hasattr(feedback, 'block_reason') and feedback.block_reason:
                    raise RuntimeError(f"Gemini blocked the request: {feedback.block_reason}")
            raise RuntimeError(f"Failed to extract text from Gemini response: {e}")
    
    def answer_history_query(
        self,
        user_query: str,
        history_context: str,
        user_profile: Dict[str, Any] = None
    ) -> str:
        """
        Answer a user's question about their conversation history.
        
        Args:
            user_query: The user's question (e.g., "What did I talk about with Miri?")
            history_context: Formatted transcript context from search_history_for_context()
            user_profile: Optional user profile for personalization
            
        Returns:
            Natural language answer to the user's question
        """
        if not self.is_configured or self.model is None:
            return "שגיאה: שירות Gemini לא מוגדר. אנא בדוק את הגדרות ה-API."
        
        # Build the prompt
        prompt = """אתה עוזר אישי שעונה על שאלות על שיחות קודמות.

המשתמש שואל על היסטוריית השיחות שלו. להלן תמלולים רלוונטיים מהקלטות קודמות:

"""
        
        if history_context:
            prompt += history_context
        else:
            prompt += "(לא נמצאו הקלטות רלוונטיות בזיכרון)"
        
        prompt += f"""

---

שאלת המשתמש: {user_query}

הוראות:
1. ענה על השאלה בהתבסס על התמלולים שלמעלה
2. אם יש מידע רלוונטי - סכם אותו בצורה ברורה ותמציתית
3. אם אין מידע רלוונטי - אמור זאת בנימוס והצע לשאול שאלה אחרת
4. ענה בעברית אלא אם המשתמש שאל באנגלית
5. היה ידידותי ועזור ככל האפשר

תשובה:"""
        
        print(f"🔍 Answering history query: {user_query[:50]}...")
        
        # Generate response
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={'max_output_tokens': 2048},
                request_options={'timeout': 60}
            )
            return response.text.strip()
        except Exception as e:
            print(f"❌ Error generating history answer: {e}")
            return f"מצטער, לא הצלחתי לעבד את השאלה. נסה שוב מאוחר יותר."
    
    def answer_kb_query(
        self,
        user_query: str,
        kb_context: str,
        user_profile: Dict[str, Any] = None
    ) -> str:
        """
        Answer a direct Knowledge Base query using:
        1. Semantic Identity Resolver — Hebrew ↔ English, nicknames, phonetic
        2. Recursive Graph Search — traverse the hierarchy tree
        3. Cross-Context Resolution — work + family identities
        4. Direct Answer Mode — factual, never false "not found"
        
        Args:
            user_query: The user's organizational question
            kb_context: Raw Knowledge Base content (includes vision-parsed graph)
            user_profile: Optional user profile
            
        Returns:
            Direct, fact-based answer from the Knowledge Base
        """
        if not self.is_configured or self.model is None:
            return "שגיאה: שירות Gemini לא מוגדר. אנא בדוק את הגדרות ה-API."
        
        if not kb_context:
            return "⚠️ בסיס הידע לא מוגדר או ריק. ודא ש-CONTEXT_FOLDER_ID מוגדר ושיש קבצים בתיקיית Second_Brain_Context ב-Google Drive."
        
        prompt = f"""אתה מומחה ארגוני עם יכולות מתקדמות של זיהוי זהויות וניווט היררכי.

═══════════════════════════════════════════════════════════════════════════════
בסיס הידע (מקור האמת היחיד):
═══════════════════════════════════════════════════════════════════════════════
{kb_context}
═══════════════════════════════════════════════════════════════════════════════

**שאלת המשתמש:** {user_query}

═══════════════════════════════════════════════════════════════════════════════
STEP 1 — SEMANTIC IDENTITY RESOLVER (זיהוי זהויות סמנטי):
═══════════════════════════════════════════════════════════════════════════════
אם השאלה מזכירה שם:

A) בצע PHONETIC MATCHING (התאמה פונטית):
   • "יובל" → חפש גם "Yuval", "Yuval Leikin", "יובל לייקין"
   • "שי" → חפש גם "Shey", "Shey Heven", "שי הון"
   • "ערן" → חפש גם "Eran"
   עברית ואנגלית הם שני ייצוגים של אותו אדם!

B) בצע CONTEXTUAL MATCHING (התאמה הקשרית):
   • אם יש "Name Mappings" בנתונים — השתמש בהם
   • אם יש "aliases" — כל כינוי מפנה לאותו אדם
   • אם שם מופיע גם בארגון וגם במשפחה — זה אותו אדם

C) בצע FUZZY MATCHING (התאמה גמישה):
   • שם חלקי: "יובל" מתאים ל-"יובל לייקין"
   • תפקיד חלקי: "מנהל" מתאים ל-"Manager, Accounting"
   • אל תדרוש התאמה מדויקת של תווים

═══════════════════════════════════════════════════════════════════════════════
STEP 2 — RECURSIVE GRAPH SEARCH (חיפוש גרפי רקורסיבי):
═══════════════════════════════════════════════════════════════════════════════
כשנשאל "מי מדווח ל-X":
1. מצא את X בגרף (באמצעות Step 1)
2. חפש את כל ה-nodes שמצביעים עליו:
   • בשדה "reports_to_name" / "reports_to"
   • בשדה "direct_reports" של X
   • ב-"edges" — כל edge שה-from_id שלו הוא X
   • ב-"hierarchy_tree" — כל מי שנמצא תחת X
3. עשה זאת רקורסיבית: אם A מדווח ל-X, ו-B מדווח ל-A, אז B הוא כפוף עקיף ל-X
4. פרט גם כפופים ישירים וגם עקיפים

כשנשאל "מי המנהל של X":
1. מצא את X
2. חפש את שדה "reports_to" / "reports_to_name" / "manager"
3. עלה בהיררכיה לצומת האב

כשנשאל "מה התפקיד של X":
1. מצא את X
2. החזר: title, department, level, reports_to

═══════════════════════════════════════════════════════════════════════════════
STEP 3 — CROSS-CONTEXT RESOLUTION (זיהוי חוצה הקשרים):
═══════════════════════════════════════════════════════════════════════════════
אדם יכול להופיע בשני הקשרים:
• "work" — תפקיד ארגוני, צוות, מנהל
• "family" — יחס משפחתי, תפקיד בבית
אם אדם מופיע בשניהם — שלב את כל המידע לתשובה אחת.

═══════════════════════════════════════════════════════════════════════════════
STEP 4 — DIRECT ANSWER MODE (תשובה ישירה):
═══════════════════════════════════════════════════════════════════════════════
פורמט תשובה:
• "ליובל לייקין (Manager, Accounting) — מדווחים אליו: שי הון, ליה כהן, אורית יוספי (3 כפופים ישירים)"
• "שי הון — תפקיד: Accountant, מדווח ל: יובל לייקין (Manager)"
• "הצוות של יובל: שי הון, ליה כהן, אורית יוספי"

כללים:
• לעולם אל תגיד "לא נמצא" אם יש התאמה חלקית כלשהי — תן את המידע הקרוב ביותר
• רק אם האדם לא מופיע בשום מקום — אמור: "לא מצאתי את [שם] בבסיס הידע."
• ענה בעברית
• היה ממוקד ותמציתי
• אל תמציא — השתמש רק בנתונים

תשובה:"""
        
        print(f"📚 [KB Query] Answering: {user_query[:60]}...")
        print(f"📚 [KB Query] Context: {len(kb_context)} chars")
        
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # ── FORCED MODEL: gemini-1.5-pro-latest for org queries ──
            # Do NOT use self.model (gemini-2.5-pro) — it hallucinates roles
            kb_model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
            print(f"📚 [KB Query] Using FORCED model: models/gemini-1.5-pro-latest")
            
            response = kb_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 1500
                },
                safety_settings=safety_settings,
                request_options={'timeout': 90}
            )
            
            answer = ""
            try:
                answer = response.text.strip() if response.text else ""
            except (ValueError, AttributeError):
                if hasattr(response, 'candidates') and response.candidates:
                    parts = response.candidates[0].content.parts
                    answer = "".join(p.text for p in parts if hasattr(p, 'text')).strip()
            
            if not answer:
                return "⚠️ לא הצלחתי לייצר תשובה. נסה לנסח את השאלה אחרת."
            
            print(f"✅ [KB Query] Answer: {len(answer)} chars")
            return answer
            
        except Exception as e:
            print(f"❌ [KB Query] Error: {e}")
            import traceback
            traceback.print_exc()
            return f"שגיאה בעיבוד השאלה: {str(e)[:100]}"
    
    def analyze_day(
        self,
        audio_paths: List[str] = None,
        image_paths: List[str] = None,
        text_inputs: List[str] = None,
        chat_history: List[Dict[str, Any]] = None,
        audio_file_metadata: List[Dict[str, str]] = None,
        reference_voices: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a day's worth of inputs using Gemini 1.5 Pro.
        
        Args:
            audio_paths: List of paths to audio files (MP3, WAV, etc.)
        
        Raises:
            ValueError: If GOOGLE_API_KEY is not configured
            image_paths: List of paths to image files (JPG, PNG)
            text_inputs: List of text notes/inputs
        
        Returns:
            Structured JSON response with analysis
        """
        audio_paths = audio_paths or []
        image_paths = image_paths or []
        text_inputs = text_inputs or []
        reference_voices = reference_voices or []
        
        # Check if service is configured
        if not self.is_configured or self.model is None:
            raise ValueError(
                "GOOGLE_API_KEY is not configured. "
                "Please set GOOGLE_API_KEY in Render Dashboard → Environment Variables. "
                "The server started successfully, but Gemini analysis requires the API key."
            )
        
        # Upload all files and wait for processing
        uploaded_files = []  # Store refreshed File objects with state='ACTIVE'
        reference_voice_files = []  # Store reference voice File objects separately
        
        # Upload and wait for audio files (main audio to transcribe)
        for audio_path in audio_paths:
            path = Path(audio_path)
            file_ref = self.upload_and_wait(audio_path, display_name=path.name)
            uploaded_files.append(file_ref)
        
        # Upload and wait for reference voice files (for speaker identification)
        for ref_voice in reference_voices:
            person_name = ref_voice.get('name', 'Unknown')
            file_path = ref_voice.get('file_path')
            if file_path and os.path.exists(file_path):
                path = Path(file_path)
                file_ref = self.upload_and_wait(file_path, display_name=f"Reference_Voice_{person_name}.mp3")
                reference_voice_files.append({
                    'file_ref': file_ref,
                    'name': person_name
                })
                print(f"✅ Uploaded reference voice for '{person_name}'")
        
        # Upload and wait for image files
        for image_path in image_paths:
            path = Path(image_path)
            file_ref = self.upload_and_wait(image_path, display_name=path.name)
            uploaded_files.append(file_ref)
        
        # Build the contents list for Gemini
        # model.generate_content expects a single list of parts (strings and File objects)
        contents = []
        
        # Use appropriate prompt based on context
        if audio_paths:
            # COMBINED DIARIZATION + EXPERT ANALYSIS in ONE call
            # This is the same approach used by process_meetings.py which works reliably
            print("🎙️ Using COMBINED Diarization + Expert Analysis prompt")
            
            # Start with the combined prompt + Knowledge Base context
            prompt = COMBINED_DIARIZATION_EXPERT_PROMPT
            
            # Inject personal knowledge base (cached in memory)
            kb_context = get_kb_context()
            if kb_context:
                prompt += "\n" + kb_context
                print(f"   📚 Knowledge Base injected ({len(kb_context)} chars)")
            
            if reference_voice_files:
                # Add reference voice information for speaker identification
                print(f"   📊 Reference voices available: {[rv['name'] for rv in reference_voice_files]}")
                
                prompt += "\n\n" + "="*50 + "\n"
                prompt += "**REFERENCE VOICE SAMPLES - ACOUSTIC FINGERPRINTS:**\n"
                prompt += "="*50 + "\n\n"
                prompt += "The following audio files are KNOWN voice samples.\n"
                prompt += "Listen to each one carefully and memorize their acoustic characteristics.\n\n"
                
                for i, rv in enumerate(reference_voice_files, 1):
                    prompt += f"📌 **Reference Audio {i}** = Voice of **{rv['name']}**\n"
                    prompt += f"   (This audio clip belongs to {rv['name']} - use this to compare)\n\n"
                
                prompt += "\n" + "="*50 + "\n"
                prompt += "**PRIMARY CONVERSATION TO ANALYZE:**\n"
                prompt += "="*50 + "\n"
                prompt += "The main audio file follows after all reference samples.\n"
                prompt += "Compare EACH speaker in this conversation to the reference samples.\n"
                prompt += "If voice matches reference with 90%+ confidence → use that name.\n"
                prompt += "If NO match with 90%+ confidence → use 'Speaker X'.\n\n"
            else:
                print("   📊 No reference voices - using speaker labels only")
            
            contents.append(prompt)
        else:
            # Regular text/image analysis
            contents.append(SYSTEM_PROMPT)
        
        # Add chat history if available (for context)
        if chat_history:
            contents.append("\n## Previous Conversation History:\n")
            for i, interaction in enumerate(chat_history[-5:], 1):  # Last 5 interactions for context
                user_msg = interaction.get('user_message', '')
                ai_resp = interaction.get('ai_response', '')
                timestamp = interaction.get('timestamp', '')
                
                contents.append(f"\n### Previous Interaction {i} ({timestamp}):\n")
                contents.append(f"**User:** {user_msg}\n")
                contents.append(f"**AI:** {ai_resp}\n")
            contents.append("\n---\n")
        
        # Add text inputs if any
        if text_inputs:
            contents.append("\n## Text Notes:\n")
            for i, text in enumerate(text_inputs, 1):
                contents.append(f"### Note {i}:\n{text}\n")
        
        contents.append("\n\nPlease provide your analysis in the JSON format specified above.")
        
        # Add the refreshed file objects (with state='ACTIVE') to contents
        # IMPORTANT: Add explicit labels BEFORE each file for clear physical mapping
        print("🔍 Adding files to contents with explicit labels...")
        print(f"   Main audio files: {len(uploaded_files)}")
        print(f"   Reference voice files: {len(reference_voice_files)}")
        
        # Add reference voice files first (so Gemini can learn them before transcribing)
        # Each reference file is preceded by a text label for clear identification
        for i, rv in enumerate(reference_voice_files, 1):
            file_ref = rv['file_ref']
            state = file_ref.state
            if hasattr(state, 'name'):
                state_name = state.name
            else:
                state_name = str(state)
            print(f"   Reference voice {rv['name']}: state={state_name}")
            
            # Add explicit label BEFORE the audio file
            contents.append(f"\n[Reference Audio {i} - Voice of {rv['name']}]:\n")
            contents.append(file_ref)
        
        # Then add main audio files with explicit label
        if uploaded_files:
            contents.append("\n\n[PRIMARY CONVERSATION TO TRANSCRIBE]:\n")
        
        for file_ref in uploaded_files:
            # Verify file is ready
            state = file_ref.state
            if hasattr(state, 'name'):
                state_name = state.name
            else:
                state_name = str(state)
            print(f"   Main audio file {file_ref.name}: state={state_name}")
            contents.append(file_ref)
        
        print("🤖 Sending request to Gemini 1.5 Pro...")
        print(f"   Contents: {len(contents)} items")
        print(f"   Types: {[type(x).__name__ for x in contents]}")
        print(f"   Files: {len(uploaded_files)}, Text parts: {len(contents) - len(uploaded_files)}")
        
        # Generate response with retry logic for connection errors
        max_retries = 3
        retry_delay = 5
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 Attempt {attempt + 1}/{max_retries}: Calling model.generate_content...")
                # Increase timeout for large files (default is 60s, we need more for audio processing)
                # Use generation_config with maximum output tokens for long audio files
                generation_config = {
                    'max_output_tokens': 65536,  # Maximum for Gemini 1.5 Pro (allows long transcripts)
                }
                response = self.model.generate_content(
                    contents,
                    generation_config=generation_config,
                    request_options={'timeout': 600}  # 10 minutes timeout
                )
                print(f"✅ Successfully received response from Gemini")
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e)
                # Check if it's a connection error that we should retry
                is_connection_error = (
                    'Connection reset' in error_str or 
                    '503' in error_str or 
                    'recvmsg' in error_str or 
                    'Connection' in error_str or
                    'timeout' in error_str.lower() or
                    'reset' in error_str.lower()
                )
                
                if is_connection_error and attempt < max_retries - 1:
                    print(f"⚠️  Connection error (attempt {attempt + 1}/{max_retries}): {error_str[:200]}")
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # Not a connection error or out of retries
                    print(f"❌ Error generating content: {error_str}")
                    raise
        
        if response is None:
            raise RuntimeError("Failed to generate content after all retries")
        
        # Extract response text with proper error handling
        # Gemini may return empty/blocked responses that don't have .text available
        try:
            response_text = response.text.strip()
        except ValueError as e:
            # This happens when response.text accessor fails (blocked/empty response)
            print(f"⚠️  Gemini response.text accessor failed: {e}")
            
            # Check if response was blocked by safety filters
            if hasattr(response, 'prompt_feedback'):
                feedback = response.prompt_feedback
                print(f"   Prompt feedback: {feedback}")
                if hasattr(feedback, 'block_reason') and feedback.block_reason:
                    raise RuntimeError(f"Gemini blocked the request: {feedback.block_reason}")
            
            # Check candidates for finish reason and try to extract partial content
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', None)
                print(f"   Finish reason: {finish_reason}")
                
                # Try to extract text from parts even if response is incomplete
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    parts = candidate.content.parts
                    if parts:
                        partial_text = ''.join(part.text for part in parts if hasattr(part, 'text'))
                        if partial_text.strip():
                            print(f"⚠️  Using partial response ({len(partial_text)} chars) - finish_reason: {finish_reason}")
                            response_text = partial_text.strip()
                            # Don't raise error - use the partial content
                        else:
                            raise RuntimeError(f"Gemini response incomplete with no usable content: {finish_reason}")
                    else:
                        raise RuntimeError(f"Gemini response has no parts: {finish_reason}")
                else:
                    raise RuntimeError(f"Gemini response incomplete: {finish_reason}")
            else:
                # If we can't get text, raise the original error
                raise RuntimeError(f"Failed to extract text from Gemini response: {e}")
        
        original_length = len(response_text)
        print(f"📄 Response length: {original_length} characters")
        
        # Check if this is an audio analysis response (should be JSON with segments + expert_summary)
        if audio_paths:
            # Parse audio analysis response (JSON format with segments + expert_summary)
            print("🎤 Detected audio analysis response - parsing JSON transcript + expert summary...")
            transcript_json = self._parse_audio_response(response_text)
            
            # Extract expert_summary from the combined response
            expert_summary = transcript_json.get('expert_summary', '')
            
            # Return structured audio analysis result with expert summary
            result = {
                "type": "audio_analysis",
                "transcript": transcript_json,  # Full JSON object with segments
                "summary": transcript_json.get('summary', ''),  # Extract basic summary (if any)
                "expert_summary": expert_summary,  # NEW: Full expert analysis from combined prompt
                "audio_file_metadata": audio_file_metadata or []
            }
            
            print("✅ Audio analysis complete!")
            print(f"   Segments: {len(transcript_json.get('segments', []))} segments")
            print(f"   Expert Summary: {len(expert_summary)} chars" if expert_summary else "   Expert Summary: (none)")
            if expert_summary:
                print(f"   First 100 chars: {expert_summary[:100]}...")
            
            return result
        
        # Regular JSON response (for non-audio analysis)
        try:
            # Clean JSON: Remove markdown code blocks before parsing
            clean_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
                print("📄 Extracted JSON from ```json block")
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                print("📄 Extracted JSON from ``` block")
            else:
                # Use cleaned text if no code blocks found
                response_text = clean_text
                print("📄 Using cleaned text (no code blocks detected)")
            
            # Try to find JSON object boundaries
            # Look for first { and try to find matching }
            # We need to be careful about strings - don't count braces inside strings
            if response_text.startswith('{'):
                brace_count = 0
                in_string = False
                escape_next = False
                last_valid_pos = -1
                
                for i, char in enumerate(response_text):
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                last_valid_pos = i + 1
                                break
                
                if last_valid_pos > 0:
                    response_text = response_text[:last_valid_pos]
                    print(f"📄 Trimmed JSON to valid boundaries (position {last_valid_pos})")
                else:
                    print("⚠️  Could not find closing brace (likely incomplete), trying to fix JSON...")
                    # Try to remove incomplete properties and close structures
                    response_text = self._fix_incomplete_json(response_text)
                    print(f"📄 Fixed JSON length: {len(response_text)} characters")
            
            # Parse JSON
            result = json.loads(response_text)
            
            print("✅ Analysis complete!")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Error position: line {e.lineno}, column {e.colno}")
            # Verbose response logging removed - check logs in debug mode if needed
            
            # Try to fix common JSON issues
            try:
                fixed_text = self._fix_json_errors(response_text)
                result = json.loads(fixed_text)
                print("✅ Fixed JSON errors and parsed successfully!")
                return result
            except Exception as fix_error:
                print(f"❌ Failed to fix JSON: {fix_error}")
                raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            print(f"❌ Error processing response: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _parse_audio_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse audio analysis response to extract JSON transcript with segments.
        
        Expected format:
        {
          "segments": [
            {
              "speaker": "Speaker 1",
              "start": 0.0,
              "end": 5.2,
              "text": "..."
            }
          ]
        }
        
        Args:
            response_text: Full response text from Gemini
        
        Returns:
            Dictionary with 'segments' key containing list of segment dicts
        """
        try:
            # Note: Raw response logging removed to reduce log noise
            # If debugging needed, uncomment: print(f"RAW: {response_text[:500]}...")
            
            # Try to extract JSON from response (might be wrapped in markdown code blocks)
            text = response_text.strip()
            
            # Clean JSON: Remove markdown code blocks before parsing
            if text.startswith("```json"):
                text = text[7:]  # Remove ```json
            elif text.startswith("```"):
                text = text[3:]  # Remove ```
            
            if text.endswith("```"):
                text = text[:-3]  # Remove closing ```
            
            # Final cleanup: remove any remaining markdown artifacts
            text = text.replace('```json', '').replace('```', '').strip()
            
            # ROBUST JSON EXTRACTION: Use regex to find JSON object
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = text
                print(f"⚠️  No JSON object found via regex")
            
            # SANITIZE: Remove invalid control characters that break JSON parsing
            # Control characters (0x00-0x1F except \t, \n, \r) are invalid in JSON strings
            def sanitize_json_string(s):
                """Remove invalid control characters from JSON string."""
                # Replace problematic control chars with space
                import re
                # Match control chars except tab, newline, carriage return
                s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', s)
                # Also fix unescaped newlines inside strings by finding quoted sections
                # This is a simplified approach - replace literal newlines with \n
                return s
            
            json_text = sanitize_json_string(json_text)
            
            # Try to parse as JSON
            try:
                transcript_json = json.loads(json_text)
                
                # Validate structure
                if not isinstance(transcript_json, dict):
                    raise ValueError("Response is not a JSON object")
                
                if "segments" not in transcript_json:
                    raise ValueError("Response missing 'segments' key")
                
                if not isinstance(transcript_json["segments"], list):
                    raise ValueError("'segments' must be a list")
                
                print(f"✅ Successfully parsed JSON transcript with {len(transcript_json['segments'])} segments")
                return transcript_json
                
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error: {e}")
                print(f"   Error position: char {e.pos if hasattr(e, 'pos') else 'unknown'}")
                
                # Try additional sanitization: escape unescaped newlines in strings
                # Find the problematic area and try to fix it
                try:
                    # More aggressive sanitization: replace all newlines with escaped versions
                    sanitized = json_text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    transcript_json = json.loads(sanitized)
                    if "segments" in transcript_json:
                        print(f"✅ Aggressive sanitization worked! Parsed {len(transcript_json['segments'])} segments")
                        return transcript_json
                except:
                    pass
                
                # Try to fix incomplete JSON using existing helper
                fixed_text = self._fix_incomplete_json(json_text)
                fixed_text = sanitize_json_string(fixed_text)
                try:
                    transcript_json = json.loads(fixed_text)
                    if "segments" in transcript_json:
                        print(f"✅ Fixed incomplete JSON and parsed {len(transcript_json['segments'])} segments")
                        return transcript_json
                except Exception as fix_error:
                    print(f"⚠️  Failed to fix JSON: {fix_error}")
                
                # Fallback: Try to extract expert_summary from raw text even if JSON failed
                # This handles cases where the expert_summary contains characters that break JSON
                print("🔍 Attempting to extract expert_summary from raw text...")
                expert_summary = ""
                
                # Try to find expert_summary content using regex
                # Look for common patterns like "🧠 הכובע שנבחר" which starts the expert section
                import re
                
                # Pattern 1: Look for expert_summary field in broken JSON
                expert_match = re.search(r'"expert_summary"\s*:\s*"(.*?)"(?:\s*}|,\s*")', text, re.DOTALL)
                if expert_match:
                    expert_summary = expert_match.group(1)
                    # Unescape JSON escapes
                    expert_summary = expert_summary.replace('\\n', '\n').replace('\\"', '"')
                    print(f"   ✅ Extracted expert_summary via JSON field: {len(expert_summary)} chars")
                
                # Pattern 2: Look for Hebrew expert format directly
                if not expert_summary:
                    # Find the expert section by looking for the emoji header
                    expert_start = text.find('🧠 הכובע שנבחר')
                    if expert_start == -1:
                        expert_start = text.find('🧠 הכובע')
                    
                    if expert_start > 0:
                        # Find end - usually before the closing JSON brace or end of text
                        expert_end = text.find('"}', expert_start)
                        if expert_end == -1:
                            expert_end = len(text)
                        
                        expert_summary = text[expert_start:expert_end]
                        # Clean up JSON artifacts
                        expert_summary = expert_summary.replace('\\n', '\n').replace('\\"', '"')
                        print(f"   ✅ Extracted expert_summary via emoji marker: {len(expert_summary)} chars")
                
                if expert_summary and len(expert_summary) > 50:
                    print(f"   📝 Expert preview: {expert_summary[:100]}...")
                    return {
                        "segments": [],
                        "expert_summary": expert_summary
                    }
                
                # No expert summary found
                print("⚠️  Could not parse JSON or extract expert_summary")
                print("   Returning empty result - speaker identification will be skipped")
                return {
                    "segments": []
                }
            
        except Exception as e:
            print(f"⚠️  Error parsing audio response: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: create a single segment with the full response
            return {
                "segments": [{
                    "speaker": "Unknown",
                    "start": 0.0,
                    "end": 0.0,
                    "text": response_text
                }]
            }
    
    def cleanup_files(self):
        """Delete all uploaded files from Google's storage."""
        for uploaded_file in self.uploaded_files:
            try:
                # uploaded_file is a File object
                # Extract file ID (without 'files/' prefix)
                if hasattr(uploaded_file, 'name'):
                    # 'name' is 'files/FILE_ID', extract just FILE_ID
                    file_name = uploaded_file.name
                    if file_name.startswith('files/'):
                        file_id = file_name[6:]  # Remove 'files/' prefix
                    else:
                        file_id = file_name
                elif hasattr(uploaded_file, 'uri'):
                    # Extract file ID from URI
                    uri = uploaded_file.uri
                    if '/files/' in uri:
                        file_id = uri.split('/files/')[-1].split('?')[0]  # Remove query params
                    else:
                        file_id = uri
                else:
                    # If it's already a file_id string
                    file_id = uploaded_file
                    if file_id.startswith('files/'):
                        file_id = file_id[6:]  # Remove 'files/' prefix
                
                # genai.delete_file() expects just the file ID (without 'files/' prefix)
                genai.delete_file(file_id)
                print(f"🗑️  Deleted: {file_id}")
            except Exception as e:
                print(f"⚠️  Failed to delete {uploaded_file}: {e}")
        
        self.uploaded_files = []


# Singleton instance
gemini_service = GeminiService()
