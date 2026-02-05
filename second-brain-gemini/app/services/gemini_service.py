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
from app.prompts import SYSTEM_PROMPT, AUDIO_ANALYSIS_PROMPT, AUDIO_ANALYSIS_PROMPT_BASE


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
        user_profile: Dict[str, Any] = None
    ) -> str:
        """
        Chat with Gemini using conversation history and user profile.
        
        Args:
            user_message: Current user message
            chat_history: List of previous interactions, each with 'user_message' and 'ai_response'
            user_profile: Dictionary containing user profile data (name, family members, etc.)
        
        Returns:
            AI response text
        """
        chat_history = chat_history or []
        user_profile = user_profile or {}
        
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
            print(f"👤 User profile injected into system prompt ({len(user_profile)} keys)")
        
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
        
        # Use AUDIO_ANALYSIS_PROMPT if we have audio files, otherwise use regular SYSTEM_PROMPT
        if audio_paths:
            # For audio analysis, we need structured output (transcript + summary)
            # Build enhanced prompt with reference voice instructions if available
            prompt = AUDIO_ANALYSIS_PROMPT_BASE
            
            if reference_voice_files:
                # Add AGGRESSIVE instructions for matching reference voices
                voice_names = [rv['name'] for rv in reference_voice_files]
                prompt += f"""

**🎯 MANDATORY VOICE IDENTIFICATION - YOU MUST USE THESE NAMES:**

You are an EXPERT voice analyzer. You are provided with reference voice samples for these KNOWN speakers: **{', '.join(voice_names)}**

**CRITICAL RULES - FOLLOW EXACTLY:**

1. **ALWAYS identify the phone owner as the FIRST speaker** - they are recording these conversations, so "Speaker 1" is ALWAYS the phone owner.

2. **USE THE PROVIDED NAMES**: You have {len(reference_voice_files)} reference voice samples. When you hear a voice that matches ANY of these references, you MUST use their name: {', '.join(voice_names)}

3. **SPEAKER 1 IS THE USER**: The person recording is always Speaker 1. If you have a reference for them (like "Itzik"), use that name instead of "Speaker 1".

4. **MATCH AGGRESSIVELY**: If a voice sounds similar to a reference sample (similar pitch, tone, speaking style), USE THAT NAME. Don't be overly conservative.

5. **ONLY USE "Speaker X" FOR TRULY UNKNOWN VOICES**: Only use generic "Speaker 2", "Speaker 3" etc. for voices that don't match ANY of the reference samples.

**NEVER DO THIS:**
- ❌ Never output "Speaker 1" if you have a reference for the main user
- ❌ Never ask "Who is this?" for known names
- ❌ Never use generic IDs when you have matching reference voices

**ALWAYS DO THIS:**
- ✅ Use "{voice_names[0] if voice_names else 'Name'}" when the voice matches that reference
- ✅ Assume Speaker 1 is the phone owner (user)
- ✅ Match voices to references, even with 70%+ confidence

**Output Format**: In the "speaker" field, use the ACTUAL PERSON NAME from the reference list whenever possible. Only use "Speaker 2", "Speaker 3" for genuinely unknown voices.
"""
            
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
        
        # Add file references in the prompt
        if uploaded_files or reference_voice_files:
            contents.append("\n## Media Files:\n")
            if uploaded_files:
                contents.append(f"**Main audio file(s) to transcribe**: {len(uploaded_files)} file(s)\n")
            if reference_voice_files:
                voice_list = ', '.join([rv['name'] for rv in reference_voice_files])
                contents.append(f"**Reference voice samples for speaker identification**: {len(reference_voice_files)} sample(s) - {voice_list}\n")
        
        contents.append("\n\nPlease provide your analysis in the JSON format specified above.")
        
        # Add the refreshed file objects (with state='ACTIVE') to contents
        print("🔍 Adding files to contents...")
        print(f"   Main audio files: {len(uploaded_files)}")
        print(f"   Reference voice files: {len(reference_voice_files)}")
        
        # Add reference voice files first (so Gemini can learn them before transcribing)
        for rv in reference_voice_files:
            file_ref = rv['file_ref']
            state = file_ref.state
            if hasattr(state, 'name'):
                state_name = state.name
            else:
                state_name = str(state)
            print(f"   Reference voice {rv['name']}: state={state_name}")
            contents.append(file_ref)
        
        # Then add main audio files
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
        
        # Check if this is an audio analysis response (should be JSON with segments)
        if audio_paths:
            # Parse audio analysis response (JSON format with segments)
            print("🎤 Detected audio analysis response - parsing JSON transcript...")
            transcript_json = self._parse_audio_response(response_text)
            
            # Return structured audio analysis result
            result = {
                "type": "audio_analysis",
                "transcript": transcript_json,  # Full JSON object with segments
                "summary": transcript_json.get('summary', ''),  # Extract summary from JSON
                "audio_file_metadata": audio_file_metadata or []
            }
            
            print("✅ Audio analysis complete!")
            print(f"   Segments: {len(transcript_json.get('segments', []))} segments")
            print(f"   Summary: {result['summary'][:100]}..." if result['summary'] else "   Summary: (none)")
            
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
            print(f"Response text (first 1000 chars): {response_text[:1000]}")
            print(f"Response text (last 500 chars): {response_text[-500:]}")
            
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
            # CRITICAL: Log the RAW AI response before any processing
            print("=" * 80)
            print("📥 RAW_AI_RESPONSE from Gemini:")
            print(response_text)
            print("=" * 80)
            
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
                print(f"🔍 Found JSON object via regex: {len(json_text)} characters")
            else:
                json_text = text
                print(f"⚠️  No JSON object found via regex, using cleaned text: {len(json_text)} characters")
            
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
                print(f"   Attempted to parse: {json_text[:500]}")
                
                # Try to fix incomplete JSON using existing helper
                fixed_text = self._fix_incomplete_json(json_text)
                try:
                    transcript_json = json.loads(fixed_text)
                    if "segments" in transcript_json:
                        print(f"✅ Fixed incomplete JSON and parsed {len(transcript_json['segments'])} segments")
                        return transcript_json
                except Exception as fix_error:
                    print(f"⚠️  Failed to fix JSON: {fix_error}")
                
                # Fallback: cannot create valid segments without proper JSON
                # Return empty segments list instead of invalid 0-second segment
                print("⚠️  Could not parse JSON - cannot create segments without valid timestamps")
                print("   Returning empty segments list - speaker identification will be skipped")
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
