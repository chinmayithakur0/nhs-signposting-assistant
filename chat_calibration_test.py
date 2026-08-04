import time
from chat import get_chatbot_response
from test_cases import test_cases

correct = 0
total = len(test_cases)

print(f"{'Query':<65} {'Expected':<12} {'Got':<12} {'Banner?':<20} {'OK?'}")
print("-" * 120)

for query, expected in test_cases:
    result = get_chatbot_response(query)
    got = result["destination"]
    is_correct = (got == expected)
    correct += is_correct

    expected_str = expected if expected else "no_match"
    got_str = got if got else "no_match"
    mark = "✅" if is_correct else "❌"

    banner_present = "CALL 999 NOW" in result["reply"]
    if expected == "call_999":
        banner_check = "✅ present" if banner_present else "❌ MISSING!"
    elif banner_present:
        banner_check = "❌ WRONGLY SHOWN"
    else:
        banner_check = "correctly absent"

    print(f"{query[:63]:<65} {expected_str:<12} {got_str:<12} {banner_check:<20} {mark}")

    time.sleep(3)  # gentle pacing to avoid hitting the free-tier rate limit

print("-" * 120)
print(f"\nDestination accuracy: {correct}/{total} = {correct/total:.1%}")