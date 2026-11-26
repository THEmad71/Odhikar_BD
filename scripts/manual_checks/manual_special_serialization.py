
from src.odhikar.ormsgpack_compat import install

install()

from datetime import datetime, timezone
from uuid import UUID
from enum import Enum

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


# ==========================================
# 1. DEFINE ENUM
# ==========================================

class VehicleType(str, Enum):
    MOTORCYCLE = "motorcycle"
    CAR = "car"


# ==========================================
# 2. INITIALIZE SERIALIZER
# ==========================================

serializer = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ("__main__", "VehicleType")
    ]
)


# ==========================================
# 3. CREATE ORIGINAL DATA
# ==========================================

original = {
    "created_at": datetime(
        2026, 11, 20, 0, 0,
        tzinfo=timezone.utc
    ),

    "user_id": UUID(
        "12345678-1234-5678-1234-567812345678"
    ),

    "vehicle_type": VehicleType.MOTORCYCLE
}


# ==========================================
# 4. SERIALIZATION
# ==========================================

saved = serializer.dumps_typed(original)

print("Saved Type:", saved[0])


# ==========================================
# 5. DESERIALIZATION
# ==========================================

restored = serializer.loads_typed(saved)

print("\nRestored Data:", restored)


# ==========================================
# 6. VALIDATION
# ==========================================

assert restored["created_at"] == original["created_at"]

assert isinstance(
    restored["user_id"],
    UUID
)

assert restored["user_id"] == original["user_id"]

assert isinstance(
    restored["vehicle_type"],
    VehicleType
)

assert restored["vehicle_type"] == original["vehicle_type"]


# ==========================================
# 7. FINAL RESULT
# ==========================================

print("\nDatetime Test: PASSED")
print("UUID Test: PASSED")
print("Enum Test: PASSED")

print("\nALL SPECIAL SERIALIZATION TESTS PASSED!")
