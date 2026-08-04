import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

df = pd.read_csv("data/nhs_scenarios_template.csv")
print(f"Loaded {len(df)} scenarios")

model = SentenceTransformer("all-MiniLM-L6-v2")

scenario_embeddings = model.encode(
    df["example_user_query"].tolist(),
    convert_to_numpy=True
)
scenario_embeddings = scenario_embeddings / np.linalg.norm(
    scenario_embeddings, axis=1, keepdims=True
)

EMERGENCY_THRESHOLD = 0.50   # easier bar -- rather over-flag a possible emergency than miss one
CLARIFY_THRESHOLD = 0.55     # below this: too dissimilar to anything -- no match
STANDARD_THRESHOLD = 0.65    # at/above this: confident enough to answer directly


def find_best_match(user_query):
    query_embedding = model.encode([user_query], convert_to_numpy=True)
    query_embedding = query_embedding / np.linalg.norm(query_embedding)
    similarities = scenario_embeddings @ query_embedding[0]

    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]
    row = df.iloc[best_idx]

    is_emergency = row["correct_destination"] == "call_999"
    threshold = EMERGENCY_THRESHOLD if is_emergency else STANDARD_THRESHOLD

    if best_score >= threshold:
        return {
            "matched": True,
            "needs_clarification": False,
            "possible_emergency": is_emergency,
            "score": float(best_score),
            "scenario_id": int(row["id"]),
            "category": row["category"],
            "matched_query": row["example_user_query"],
            "summary": row["summary_in_own_words"],
            "correct_destination": row["correct_destination"],
            "source_url": row["source_url"],
            "red_flag_notes": row["red_flag_notes"],
        }

    # Borderline zone: not confident enough to answer, but not dissimilar
    # enough to dismiss either -- ask for more detail instead of guessing
    if not is_emergency and best_score >= CLARIFY_THRESHOLD:
        return {
            "matched": False,
            "needs_clarification": True,
            "possible_emergency": False,
            "score": float(best_score),
        }

    return {
        "matched": False,
        "needs_clarification": False,
        "possible_emergency": False,
        "score": float(best_score),
        "message": "No confident match -- defer to NHS 111"
    }


if __name__ == "__main__":
    test_queries = [
        "I've had a cough for a while now, should I see someone?",
        "My face suddenly went droopy and I can't speak properly",
        "What's the best pizza topping?",
        "i have cough",
    ]

    for q in test_queries:
        print(f"\nQuery: '{q}'")
        print(find_best_match(q))