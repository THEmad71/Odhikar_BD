
from uuid import uuid4

from src.odhikar.graph import (
    ask_odhikar_graph,
    get_conversation_history
)


# ==========================================
# 1. CREATE NEW THREAD
# ==========================================

def create_thread_id():

    return f"odhikar_{uuid4().hex[:12]}"


# ==========================================
# 2. ASK QUESTION IN A THREAD
# ==========================================

def ask_in_thread(query: str, thread_id: str):

    return ask_odhikar_graph(
        query,
        thread_id=thread_id
    )


# ==========================================
# 3. GET THREAD HISTORY
# ==========================================

def get_thread_history(thread_id: str):

    return get_conversation_history(thread_id)
