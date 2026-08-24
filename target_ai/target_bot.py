import ollama
from .prompts import SYSTEM_PROMPT
from .vector_store import (
    DEFAULT_DB_DIR,
    DEFAULT_KB_DIR,
    init_vector_store,
    index_all_documents,
    query_similar_chunks,
)

_collection = None


def get_or_create_collection():
    """
    Ensures that the ChromaDB collection is initialized and indexed
    with all documents from the knowledge_base directory.
    """
    global _collection
    if _collection is None:
        _collection = init_vector_store(
            persist_directory=DEFAULT_DB_DIR, collection_name="novacloud_docs"
        )
        if _collection.count() == 0:
            _collection = index_all_documents(
                kb_directory=DEFAULT_KB_DIR,
                persist_directory=DEFAULT_DB_DIR,
                collection_name="novacloud_docs",
            )
    return _collection


def ask_target_bot(message: str, test_mode: bool = False) -> str | dict:
    """
    RAG-based customer support assistant:
    1. Ensures knowledge base is indexed.
    2. Retrieves top 3 PUBLIC documentation chunks.
    3. Builds augmented context prompt.
    4. Calls gemma3:1b to generate a grounded response.
    5. Returns only the final response text (or a dictionary if test_mode=True).
    """
    collection = get_or_create_collection()

    retrieved_chunks = query_similar_chunks(
        collection=collection,
        query=message,
        top_k=3,
        visibility_filter="PUBLIC",
    )

    if retrieved_chunks:
        context_blocks = []
        for rank, chunk in enumerate(retrieved_chunks, start=1):
            source = chunk["metadata"].get("source", "unknown")
            title = chunk["metadata"].get("title", "NovaCloud Documentation")
            context_blocks.append(
                f"[Document {rank}: {title} (File: {source})]\n{chunk['text']}"
            )
        context_str = "\n\n".join(context_blocks)
    else:
        context_str = "No documentation found."

    prompt_content = f"""Documentation Context:
{context_str}

Customer Question: {message}

Instructions: Based ONLY on the Documentation Context above, answer the customer's question. If the context does not contain the answer or is insufficient, reply: "I cannot find this information in the available NovaCloud documentation." """

    response = ollama.chat(
        model="gemma3:1b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ],
    )
    final_response = response["message"]["content"]

    if test_mode:
        return {
            "target_response": final_response,
            "retrieved_context": retrieved_chunks,
            "visibility": [
                chunk.get("metadata", {}).get("visibility")
                for chunk in retrieved_chunks
            ],
        }

    return final_response


# Backward-compatibility alias functions for shared repo orchestration
def get_response(prompt: str) -> str:
    """
    Alias for ask_target_bot to support existing teammate orchestration (e.g. main.py).
    """
    return ask_target_bot(prompt)


class TargetAI:
    """
    Target AI wrapper class for object-oriented interfaces used across the test suite.
    """

    def __init__(self, model_name: str = "NovaBot (gemma3:1b)"):
        self.model_name = model_name

    def generate_response(self, prompt: str, test_mode: bool = False) -> str | dict:
        """
        Generates a Target AI response.

        If test_mode=False:
            returns only the final response string.

        If test_mode=True:
            returns structured test data containing:
            - target_response
            - retrieved_context
            - visibility
        """
        return ask_target_bot(prompt, test_mode=test_mode)

    def get_response(self, prompt: str, test_mode: bool = False) -> str | dict:
        """
        Backward-compatible response method with optional structured test output.
        """
        return ask_target_bot(prompt, test_mode=test_mode)

    def __call__(self, prompt: str, test_mode: bool = False) -> str | dict:
        return ask_target_bot(prompt, test_mode=test_mode)