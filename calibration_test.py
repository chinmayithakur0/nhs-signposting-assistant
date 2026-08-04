from retrieval import find_best_match

# ---- Test set: (question, expected_destination_or_None) ----
# None means "should NOT match anything -- correctly defer to 111"
test_cases = from test_cases import test_cases

# ---- Run every test case and score the results ----
correct = 0
total = len(test_cases)

print(f"{'Query':<65} {'Expected':<12} {'Got':<12} {'Score':<8} {'OK?'}")
print("-" * 110)

for query, expected in test_cases:
    result = find_best_match(query)
    got = result["correct_destination"] if result["matched"] else None
    score = result["score"]

    is_correct = (got == expected)
    correct += is_correct

    expected_str = expected if expected else "no_match"
    got_str = got if got else "no_match"
    mark = "✅" if is_correct else "❌"

    print(f"{query[:63]:<65} {expected_str:<12} {got_str:<12} {score:.3f}    {mark}")

print("-" * 110)
print(f"\nAccuracy: {correct}/{total} = {correct/total:.1%}")