
from pathlib import Path
import shutil

# Locate actual graph.py
file_path = Path("src/odhikar/graph.py")

if not file_path.exists():
    raise FileNotFoundError("graph.py not found!")

# Read actual source
source = file_path.read_text(encoding="utf-8")

# Check whether helper already exists
if "def extract_text(" in source:
    print("extract_text() already exists.")
else:

    # Backup original file
    backup_path = file_path.with_suffix(".py.bak")
    shutil.copy2(file_path, backup_path)

    # Helper function
    helper = '''
# ==========================================
# EXTRACT READABLE TEXT
# ==========================================

def extract_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        answer = []

        for block in content:

            if isinstance(block, dict):
                if block.get("type") == "text":
                    answer.append(block.get("text", ""))

            elif hasattr(block, "text"):
                answer.append(block.text)

        return "\\n".join(answer).strip()

    return str(content)


'''

    # Insert helper before main function
    marker = "def ask_odhikar_graph("

    if marker not in source:
        raise ValueError(
            "ask_odhikar_graph() definition not found!"
        )

    source = source.replace(
        marker,
        helper + marker,
        1
    )

    file_path.write_text(
        source,
        encoding="utf-8"
    )

    print("extract_text() successfully inserted!")
    print("Backup created:", backup_path)


# Verify actual source
updated_source = file_path.read_text(encoding="utf-8")

print(
    "Helper definition exists:",
    "def extract_text(" in updated_source
)

print(
    "Old function call exists:",
    "return extract_text(final_message.content)" in updated_source
)

