import json
from pathlib import Path
from typing import Generator


def parse_jsonl_line(line: str, line_number: int) -> tuple[dict | None, str | None]:
    """Parse a single JSONL line and validate the training format.

    Returns (parsed_dict, error_message). One will be None.
    """
    line = line.strip()
    if not line:
        return None, None  # Skip blank lines

    try:
        data = json.loads(line)
    except json.JSONDecodeError as e:
        return None, f"Line {line_number}: Invalid JSON - {e}"

    if "messages" not in data:
        return None, f"Line {line_number}: Missing 'messages' key"

    messages = data["messages"]
    if not isinstance(messages, list) or len(messages) < 2:
        return None, f"Line {line_number}: 'messages' must be a list with at least 2 entries"

    for i, msg in enumerate(messages):
        if "role" not in msg or "content" not in msg:
            return None, f"Line {line_number}: Message {i} missing 'role' or 'content'"
        if msg["role"] not in ("system", "user", "assistant"):
            return None, f"Line {line_number}: Message {i} has invalid role '{msg['role']}'"

    return data, None


def extract_fields(data: dict) -> dict:
    """Extract system_prompt, user_content, assistant_content from a messages dict."""
    messages = data["messages"]
    system_prompt = ""
    user_content = ""
    assistant_content = ""

    for msg in messages:
        if msg["role"] == "system":
            system_prompt = msg["content"]
        elif msg["role"] == "user":
            if user_content:
                user_content += "\n---\n"
            user_content += msg["content"]
        elif msg["role"] == "assistant":
            if assistant_content:
                assistant_content += "\n---\n"
            assistant_content += msg["content"]

    total_chars = sum(len(msg["content"]) for msg in messages)

    return {
        "system_prompt": system_prompt,
        "user_content": user_content,
        "assistant_content": assistant_content,
        "message_count": len(messages),
        "char_count": total_chars,
        "raw_json": json.dumps(data, ensure_ascii=False),
    }


def stream_jsonl(file_path: Path) -> Generator[tuple[int, str], None, None]:
    """Stream JSONL file line by line with line numbers (1-indexed)."""
    with open(file_path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            yield line_number, line


def write_jsonl(file_path: Path, items: list[str]):
    """Write a list of raw JSON strings to a JSONL file."""
    with open(file_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item.strip() + "\n")
