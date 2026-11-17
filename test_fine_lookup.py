
from src.odhikar.tools import fine_lookup


queries = [
    "no_helmet",
    "helmet nai",
    "helmet chara",
    "amar helmet chilo na",
    "unknown offence"
]


for query in queries:

    print("\nUser Query:", query)

    result = fine_lookup(
        offence=query,
        vehicle_type="motorcycle"
    )

    print("Status:", result["status"])

    if result["status"] == "success":
        print("Offence:", result["offence"])
        print("Maximum Fine:", result["max_fine_bdt"])
