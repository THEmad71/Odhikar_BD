
from src.odhikar.ormsgpack_compat import install

install()

from pydantic import BaseModel

from langgraph.checkpoint.serde.jsonplus import (
    JsonPlusSerializer
)


# ==========================================
# 1. CREATE PYDANTIC MODEL
# ==========================================

class TrafficOffence(BaseModel):

    offence: str
    vehicle_type: str
    max_fine_bdt: int
    imprisonment: str


# ==========================================
# 2. INITIALIZE SERIALIZER
# ==========================================

serializer = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ("__main__", "TrafficOffence")
    ]
)


# ==========================================
# 3. CREATE ORIGINAL OBJECT
# ==========================================

original = TrafficOffence(
    offence="No helmet",
    vehicle_type="Motorcycle",
    max_fine_bdt=10000,
    imprisonment="Up to 3 months"
)


# ==========================================
# 4. SERIALIZE
# ==========================================

saved = serializer.dumps_typed(original)

print("Saved Type:", saved[0])


# ==========================================
# 5. DESERIALIZE
# ==========================================

restored = serializer.loads_typed(saved)

print("\nRestored Object:", restored)
print("Restored Class:", type(restored).__name__)


# ==========================================
# 6. VALIDATION
# ==========================================

assert isinstance(restored, TrafficOffence)

assert restored.offence == original.offence

assert restored.vehicle_type == original.vehicle_type

assert restored.max_fine_bdt == original.max_fine_bdt

assert restored.imprisonment == original.imprisonment

print("\nPydantic Serialization PASSED!")
