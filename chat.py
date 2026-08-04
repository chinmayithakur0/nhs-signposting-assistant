import os
import time
from dotenv import load_dotenv
from groq import Groq
from retrieval import find_best_match

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are an NHS signposting assistant. Your ONLY job is to tell
the user which type of care to seek, using ONLY the guidance text provided to you.

STRICT RULES:
1. Only use the RETRIEVED GUIDANCE given to you. Never add medical facts, symptoms,
   or advice from your own general knowledge.
2. Always clearly state the recommended destination in plain terms.
3. Always mention the source NHS page at the end so the user can read more.
4. Keep your tone calm, clear, and direct -- the person reading this may be worried.
5. You are signposting to the right SERVICE, never diagnosing what condition they have.
6. The FIRST time you discuss a topic in the conversation, mention the full set
   of specific red flag warning signs from the retrieved guidance. In LATER
   follow-up turns on the same topic, do not repeat the entire red flag list
   again -- only reference a specific red flag if it's directly relevant to
   what the user just said in their latest message.
7. When the user mentions a new or additional symptom, you may acknowledge how it
   connects to the conversation naturally (e.g. "that's one of the specific reasons
   to see a GP"), but NEVER speculate about what is causing a symptom, NEVER suggest
   a symptom is "probably" from something benign, and NEVER offer reassurance about
   what a symptom does or doesn't mean medically.
"""

CLARIFYING_REPLY = (
    "Could you tell me a bit more about that -- for example, how long you've "
    "had this, how severe it feels, and whether there's anything else going on "
    "alongside it? That'll help me point you in the right direction."
)


def call_llm_with_retry(messages, max_retries=4):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception:
            if attempt < max_retries - 1:
                wait_time = 3 * (attempt + 1)
                print(f"  (API busy, retrying in {wait_time}s...)")
                time.sleep(wait_time)
            else:
                raise


def build_fallback_reply(result):
    destination_readable = result['correct_destination'].replace('_', ' ')
    return (
        f"Based on what you've described, you should contact your "
        f"**{destination_readable}**.\n\n"
        f"{result['summary']}\n\n"
        f"{result['red_flag_notes']}\n\n"
        f"You can read the full official guidance here: {result['source_url']}\n\n"
        f"(Note: our AI assistant is briefly unavailable, so this answer was "
        f"built directly from our verified NHS source rather than rephrased "
        f"by AI -- the guidance itself is unaffected.)"
    )


def get_chatbot_response(user_query):
    result = find_best_match(user_query)

    if result.get("needs_clarification"):
        return {
            "matched": False,
            "destination": None,
            "possible_emergency": False,
            "reply": CLARIFYING_REPLY,
        }

    if not result["matched"]:
        reply = (
            "I don't have specific guidance on this. To be safe, please contact "
            "NHS 111 (call 111 or visit 111.nhs.uk) for advice tailored to your "
            "situation -- they can properly assess what you've described."
        )
        return {
            "matched": False,
            "destination": None,
            "possible_emergency": False,
            "reply": reply,
        }

    user_prompt = f"""RETRIEVED GUIDANCE:
- Recommended destination: {result['correct_destination']}
- Summary: {result['summary']}
- Red flag notes: {result['red_flag_notes']}
- Source: {result['source_url']}

USER'S QUESTION: {user_query}

Write a short, clear, natural reply using ONLY the guidance above."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        reply = call_llm_with_retry(messages)
    except Exception:
        reply = build_fallback_reply(result)

    if result["possible_emergency"]:
        reply = "⚠️ THIS MAY BE A MEDICAL EMERGENCY -- CALL 999 NOW ⚠️\n\n" + reply

    return {
        "matched": True,
        "destination": result["correct_destination"],
        "possible_emergency": result["possible_emergency"],
        "reply": reply,
    }


if __name__ == "__main__":
    test_queries = [
        "I've had a cough for weeks, should I see someone?",
        "My dad's face suddenly looks droopy and his speech is slurred",
        "What's the best pizza topping?",
        "i have cough",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"USER: {q}")
        print(f"{'-'*60}")
        print(get_chatbot_response(q)["reply"])