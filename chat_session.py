from chat import call_llm_with_retry, build_fallback_reply, SYSTEM_PROMPT, CLARIFYING_REPLY
from retrieval import find_best_match


class ChatSession:
    def __init__(self):
        self.history = []

    def _build_combined_query(self, new_message, lookback=2):
        recent_user_messages = [
            turn["content"] for turn in self.history if turn["role"] == "user"
        ][-lookback:]
        return " ".join(recent_user_messages + [new_message])

    def _resolve_match(self, user_message):
        """Try the message ALONE first (handles clean topic switches without
        dilution). Only fall back to combining with recent context if the
        standalone search finds nothing -- that's specifically for short,
        vague follow-ups that genuinely need earlier context to make sense."""
        standalone_result = find_best_match(user_message)

        if standalone_result["matched"] or standalone_result.get("needs_clarification"):
            return standalone_result

        combined_query = self._build_combined_query(user_message)
        combined_result = find_best_match(combined_query)
        return combined_result

    def send(self, user_message):
        result = self._resolve_match(user_message)

        if result.get("needs_clarification"):
            reply = CLARIFYING_REPLY
        elif not result["matched"]:
            reply = (
                "I don't have specific guidance on this. To be safe, please contact "
                "NHS 111 (call 111 or visit 111.nhs.uk) for advice tailored to your "
                "situation -- they can properly assess what you've described."
            )
        else:
            augmented_message = f"""RETRIEVED GUIDANCE FOR THIS MESSAGE:
- Recommended destination: {result['correct_destination']}
- Summary: {result['summary']}
- Red flag notes: {result['red_flag_notes']}
- Source: {result['source_url']}

USER'S ACTUAL MESSAGE: {user_message}

Write a short, clear, natural reply using ONLY the guidance above. You may refer
back naturally to earlier parts of the conversation, but do not introduce any
new medical facts beyond what's in the retrieved guidance."""

            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": augmented_message})

            try:
                reply = call_llm_with_retry(messages)
            except Exception:
                reply = build_fallback_reply(result)

            if result["possible_emergency"]:
                reply = "⚠️ THIS MAY BE A MEDICAL EMERGENCY -- CALL 999 NOW ⚠️\n\n" + reply

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": reply})

        return {
            "reply": reply,
            "destination": result.get("correct_destination") if result["matched"] else None,
            "possible_emergency": result.get("possible_emergency", False) if result["matched"] else False,
        }


if __name__ == "__main__":
    session = ChatSession()

    conversation = [
        "I've had a cough for a while now",
        "does it matter that I've also been really tired lately?",
        "i fell off my bike and hurt my hand",
    ]

    for msg in conversation:
        print(f"\n{'='*60}")
        print(f"USER: {msg}")
        print(f"{'-'*60}")
        print(session.send(msg)["reply"])