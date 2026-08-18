import os
import yaml


def parse_markdown_file(file_path: str) -> dict:
    """
    Reads a markdown file, parses YAML frontmatter enclosed by '---',
    and returns a dictionary with metadata and body content.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    metadata = {}
    content = raw_text

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1].strip()
            content = parts[2].strip()
            if frontmatter_text:
                parsed_meta = yaml.safe_load(frontmatter_text)
                if isinstance(parsed_meta, dict):
                    metadata = parsed_meta

    return {"metadata": metadata, "content": content}


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Splits text into overlapping chunks of approximately chunk_size characters.
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)
    step = max(1, chunk_size - overlap)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start += step

    return chunks


def load_and_chunk_document(
    file_path: str, chunk_size: int = 500, overlap: int = 100
) -> list[dict]:
    """
    Loads a markdown file, parses frontmatter metadata, and returns a list of
    chunk objects with metadata attached.
    """
    parsed = parse_markdown_file(file_path)
    metadata = parsed["metadata"]
    content = parsed["content"]
    chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)

    filename = os.path.basename(file_path)
    base_id = os.path.splitext(filename)[0]

    chunk_objects = []
    for idx, chunk_str in enumerate(chunks):
        chunk_meta = {
            "source": filename,
            "title": metadata.get("title", filename),
            "visibility": metadata.get("visibility", "PUBLIC"),
            "category": metadata.get("category", "general"),
            "chunk_index": idx,
        }
        chunk_objects.append(
            {
                "id": f"{base_id}_chunk_{idx}",
                "text": chunk_str,
                "metadata": chunk_meta,
            }
        )

    return chunk_objects
