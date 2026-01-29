"""
Test script to simulate a day with dummy inputs and see the AI agents in action.

This script:
1. Creates dummy text and audio transcript inputs
2. Ingests them into the system
3. Runs all three AI agents on the combined content
4. Generates a daily digest
5. Prints all results in a readable format
"""

import asyncio
import json
from datetime import date, datetime
from typing import Dict, Any

from app.services.ingestion_service import ingestion_service
from app.services.agent_service import AgentService
from app.services.digest_service import DigestService
from app.core.database import get_db_path
import aiosqlite


# Dummy data simulating a real day
DUMMY_DAY_DATA = {
    "morning_voice_note": """
    Good morning! Had a great team meeting today. We discussed the Q1 strategy 
    and I noticed that Sarah seemed really engaged when we talked about the new 
    product direction. I think we're building something meaningful here. 
    The team is starting to trust each other more, which is great to see.
    """,
    
    "whatsapp_export": """
    [WhatsApp Export - Work Group]
    - Meeting notes: Need to focus on user retention metrics
    - Product roadmap discussion: Prioritize mobile app features
    - Budget approval: Got green light for Q1 marketing spend
    - Team velocity: We're hitting 85% of sprint goals, need to improve
    
    [WhatsApp Export - Family Group]
    - Kids had a rough morning getting ready for school
    - My daughter was upset because I praised her for being "smart" 
      instead of acknowledging her effort
    - Need to have a family meeting about morning routines
    - Son asked why we have rules - good opportunity for discussion
    """,
    
    "afternoon_reflection": """
    Reflecting on today: I realized I've been too focused on metrics and KPIs 
    lately, and maybe losing sight of why we're doing this. The team meeting 
    reminded me of our mission - to help people manage their finances better. 
    That's the "why" that drives us.
    
    At home, I noticed I'm falling back into old parenting patterns - using 
    praise instead of encouragement, and getting into power struggles. Need 
    to reconnect with the kids and focus on cooperation rather than control.
    """,
    
    "evening_voice_note": """
    End of day thoughts: The strategy session went well, but I'm concerned 
    about our go-to-market approach. We're not clear on our target customer 
    segments yet. Also, our operational efficiency could be better - too 
    many meetings, not enough execution time.
    
    Home front: Had a better evening with the kids. We sat down together 
    and talked about the morning issues. I asked them what they thought 
    would help, and they came up with some good ideas. Felt more like 
    cooperation than me just telling them what to do.
    """
}


def print_section(title: str, char: str = "=", width: int = 80):
    """Print a formatted section header."""
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}\n")


def print_json_pretty(data: Dict[str, Any], title: str = None):
    """Print JSON data in a readable format."""
    if title:
        print(f"\n{title}:")
        print("-" * 80)
    print(json.dumps(data, indent=2, ensure_ascii=False))


async def simulate_day():
    """Simulate a full day with ingestion, agent analysis, and digest generation."""
    
    print_section("🧪 Daily Sync - Test Simulation", "=", 80)
    print("Simulating a day with dummy inputs...")
    print("This will show how the AI agents analyze content and generate insights.\n")
    
    # Step 1: Ingest all the dummy data
    print_section("📥 Step 1: Ingesting Daily Content", "-", 80)
    
    ingested_items = []
    
    # Ingest morning voice note (as text transcript)
    print("\n📝 Ingesting morning voice note...")
    morning_result = await ingestion_service.ingest_text(
        text=DUMMY_DAY_DATA["morning_voice_note"],
        metadata={"source": "voice_note", "time": "08:30", "type": "morning_reflection"}
    )
    ingested_items.append(("Morning Voice Note", morning_result))
    print(f"   ✅ Ingested: {morning_result['content_hash'][:16]}...")
    
    # Ingest WhatsApp exports
    print("\n💬 Ingesting WhatsApp exports...")
    whatsapp_result = await ingestion_service.ingest_text(
        text=DUMMY_DAY_DATA["whatsapp_export"],
        metadata={"source": "whatsapp", "time": "12:00", "type": "communication"}
    )
    ingested_items.append(("WhatsApp Exports", whatsapp_result))
    print(f"   ✅ Ingested: {whatsapp_result['content_hash'][:16]}...")
    
    # Ingest afternoon reflection
    print("\n📔 Ingesting afternoon reflection...")
    afternoon_result = await ingestion_service.ingest_text(
        text=DUMMY_DAY_DATA["afternoon_reflection"],
        metadata={"source": "journal", "time": "15:00", "type": "reflection"}
    )
    ingested_items.append(("Afternoon Reflection", afternoon_result))
    print(f"   ✅ Ingested: {afternoon_result['content_hash'][:16]}...")
    
    # Ingest evening voice note
    print("\n🌙 Ingesting evening voice note...")
    evening_result = await ingestion_service.ingest_text(
        text=DUMMY_DAY_DATA["evening_voice_note"],
        metadata={"source": "voice_note", "time": "20:00", "type": "evening_reflection"}
    )
    ingested_items.append(("Evening Voice Note", evening_result))
    print(f"   ✅ Ingested: {evening_result['content_hash'][:16]}...")
    
    print(f"\n✅ Total items ingested: {len(ingested_items)}")
    
    # Step 2: Combine all content
    print_section("📋 Step 2: Combining Daily Content", "-", 80)
    
    combined_content = "\n\n---\n\n".join([
        f"[{name}]\n{item['processed_content']}"
        for name, item in ingested_items
    ])
    
    print(f"Combined content length: {len(combined_content)} characters")
    print(f"\nFirst 200 characters:\n{combined_content[:200]}...")
    
    # Step 3: Run AI Agents
    print_section("🤖 Step 3: Running AI Agents Analysis", "-", 80)
    
    try:
        # Initialize agent service
        agent_service = AgentService()
        
        print("\n🔍 Running Leadership Coach (Simon Sinek persona)...")
        leadership_result = await agent_service.analyze_with_leadership_coach(combined_content)
        print("   ✅ Leadership analysis complete")
        
        print("\n📊 Running Strategy Consultant...")
        strategy_result = await agent_service.analyze_with_strategy_consultant(combined_content)
        print("   ✅ Strategy analysis complete")
        
        print("\n👨‍👩‍👧 Running Parenting Coach (Adler Institute persona)...")
        parenting_result = await agent_service.analyze_with_parenting_coach(combined_content)
        print("   ✅ Parenting analysis complete")
        
        # Combine all agent results
        all_agent_results = {
            "leadership_coach": leadership_result,
            "strategy_consultant": strategy_result,
            "parenting_coach": parenting_result
        }
        
    except Exception as e:
        print(f"\n❌ Error running agents: {e}")
        print("\n💡 Note: You need to set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")
        print("   The agents require API access to analyze content.")
        print("\n   For now, showing structure without actual AI analysis...")
        
        # Create dummy responses to show structure
        all_agent_results = {
            "leadership_coach": {
                "agent_type": "leadership_coach",
                "response": "[AI Analysis would appear here - requires API key]",
                "content_analyzed": combined_content[:200] + "..."
            },
            "strategy_consultant": {
                "agent_type": "strategy_consultant",
                "response": "[AI Analysis would appear here - requires API key]",
                "content_analyzed": combined_content[:200] + "..."
            },
            "parenting_coach": {
                "agent_type": "parenting_coach",
                "response": "[AI Analysis would appear here - requires API key]",
                "content_analyzed": combined_content[:200] + "..."
            }
        }
    
    # Display agent results
    print_section("💡 Agent Analysis Results", "=", 80)
    
    print("\n" + "="*80)
    print("LEADERSHIP COACH ANALYSIS (Simon Sinek Persona)")
    print("="*80)
    print(all_agent_results["leadership_coach"]["response"])
    
    print("\n" + "="*80)
    print("STRATEGY CONSULTANT ANALYSIS")
    print("="*80)
    print(all_agent_results["strategy_consultant"]["response"])
    
    print("\n" + "="*80)
    print("PARENTING COACH ANALYSIS (Adler Institute Persona)")
    print("="*80)
    print(all_agent_results["parenting_coach"]["response"])
    
    # Step 4: Generate Daily Digest
    print_section("📝 Step 4: Generating Daily Digest", "-", 80)
    
    try:
        digest_service = DigestService()
        today = date.today().isoformat()
        
        print(f"\n🔄 Synthesizing insights for {today}...")
        digest = await digest_service.generate_daily_digest(
            agent_responses=all_agent_results,
            date_str=today
        )
        print("   ✅ Digest generated")
        
    except Exception as e:
        print(f"\n❌ Error generating digest: {e}")
        print("   Creating summary structure...")
        digest = {
            "date": date.today().isoformat(),
            "summary": "[Digest would be generated here - requires API key]",
            "full_digest": "[Full digest would appear here]",
            "action_items": "[Action items would be listed here]"
        }
    
    # Display final digest
    print_section("📰 Daily Digest - Final Result", "=", 80)
    
    print(f"\n📅 Date: {digest.get('date', 'N/A')}")
    print(f"\n📊 Summary:")
    print("-" * 80)
    print(digest.get('summary', 'N/A'))
    
    print(f"\n✅ Action Items:")
    print("-" * 80)
    print(digest.get('action_items', 'N/A'))
    
    print(f"\n📄 Full Digest:")
    print("=" * 80)
    print(digest.get('full_digest', 'N/A'))
    
    # Step 5: Show what's in the database
    print_section("💾 Step 5: Database Contents", "-", 80)
    
    try:
        db_path = get_db_path()
        async with aiosqlite.connect(db_path) as db:
            # Count ingestion logs
            async with db.execute("SELECT COUNT(*) FROM ingestion_logs") as cursor:
                count = await cursor.fetchone()
                print(f"\n📥 Ingestion logs: {count[0]} items")
            
            # Count digests
            async with db.execute("SELECT COUNT(*) FROM daily_digests") as cursor:
                count = await cursor.fetchone()
                print(f"📰 Daily digests: {count[0]} items")
            
            # Count agent responses
            async with db.execute("SELECT COUNT(*) FROM agent_responses") as cursor:
                count = await cursor.fetchone()
                print(f"🤖 Agent responses: {count[0]} items")
            
    except Exception as e:
        print(f"❌ Error reading database: {e}")
    
    # Final summary
    print_section("✅ Simulation Complete!", "=", 80)
    
    print("\n📋 Summary:")
    print(f"   • Ingested {len(ingested_items)} items")
    print(f"   • Ran 3 AI agents")
    print(f"   • Generated 1 daily digest")
    print(f"   • Saved to database")
    
    print("\n💡 Next Steps:")
    print("   1. Set API keys in .env to see actual AI analysis")
    print("   2. Check the database: data/sqlite/daily_sync.db")
    print("   3. Use the API: http://localhost:8000/docs")
    print("   4. Run again with different dummy data")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    print("\n🚀 Starting Daily Sync Test Simulation...\n")
    
    try:
        asyncio.run(simulate_day())
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
