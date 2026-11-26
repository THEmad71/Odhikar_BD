
from src.odhikar.langchain_tools import (
    ODHIKAR_TOOLS,
    lookup_traffic_offence,
    check_fine_claim
)


# Test 1: Check registered tools
print("\n--- TEST 1: REGISTERED TOOLS ---")

for tool in ODHIKAR_TOOLS:
    print("Tool Name:", tool.name)
    print("Description:", tool.description)
    print("Input Schema:", tool.args)
    print()


# Test 2: Invoke Fine Lookup Tool
print("\n--- TEST 2: FINE LOOKUP TOOL ---")

result = lookup_traffic_offence.invoke({
    "offence": "no_helmet",
    "vehicle_type": "motorcycle"
})

print(result)


# Test 3: Invoke Claim Check Tool
print("\n--- TEST 3: CLAIM CHECK TOOL ---")

result = check_fine_claim.invoke({
    "offence_id": "no_helmet",
    "claimed_amount": 15000,
    "receipt_given": True,
    "case_number_given": True
})

print(result)


print("\nAll LangChain tool tests completed!")
