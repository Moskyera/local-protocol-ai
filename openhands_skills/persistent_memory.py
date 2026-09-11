"""
Persistent Memory - Docker + Windows Friendly (Chroma + JSON Fallback)
"""
import os
import json
from datetime import datetime
from logger import log

class PersistentMemory:
    def __init__(self):
        # Cross-platform: use project-relative memory dir (works on Windows + Docker)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.memory_dir = os.path.join(base_dir, "memory", "openhands")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Προσπάθεια ChromaDB
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            db_path = os.path.join(self.memory_dir, "vector_db")
            os.makedirs(db_path, exist_ok=True)
            
            self.client = chromadb.PersistentClient(path=db_path, settings=chromadb.Settings(anonymized_telemetry=False))
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            self.collection = self.client.get_or_create_collection(
                name="openhands_memory",
                embedding_function=self.embedding_function
            )
            self.use_chroma = True
            log.success("✅ Chroma Vector DB initialized successfully")
        except Exception as e:
            log.warning(f"⚠️ ChromaDB not available ({e}). Using JSON fallback.")
            self.use_chroma = False
            self.json_file = os.path.join(self.memory_dir, "vector_db.json")
            if not os.path.exists(self.json_file):
                with open(self.json_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
            log.success("✅ JSON fallback Vector DB ready")

    def store(self, text: str, metadata: dict = None):
        if metadata is None:
            metadata = {"timestamp": datetime.now().isoformat()}
        
        if self.use_chroma:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[f"mem_{datetime.now().timestamp()}"]
            )
        else:
            # JSON fallback
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data.append({"text": text, **metadata})
                with open(self.json_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except:
                pass
        return "Knowledge stored successfully"

    def store_learning(self, task: str, reflection: str):
        text = f"Task: {task}\nReflection: {reflection}"
        metadata = {"type": "learning", "task": task}
        return self.store(text, metadata)

    # ------------------------------------------------------------------ #
    # READING. These two did not exist.
    #
    # Nine call sites across the repo call retrieve() and
    # retrieve_relevant_evolution() — evaluation_harness and every hacash /
    # finance expert — each wrapped in `try/except ... or ""`. So every expert
    # that claims to consult what the system has learned received an empty
    # string, silently, forever. Measured: 324 documents stored, zero readable,
    # because the class offered no way to read at all.
    # ------------------------------------------------------------------ #

    def _json_all(self):
        try:
            with open(self.json_file, "r", encoding="utf-8") as f:
                return json.load(f) or []
        except Exception:
            return []

    def retrieve(self, limit: int = 5, metadata_filter: dict = None) -> list:
        """Most recent stored items, optionally filtered by metadata.

        Returns a list of {"text": ..., "metadata": {...}} — newest first.
        """
        limit = max(1, int(limit or 5))
        if self.use_chroma:
            try:
                where = metadata_filter or None
                got = self.collection.get(where=where, include=["documents", "metadatas"])
                docs = got.get("documents") or []
                metas = got.get("metadatas") or []
                rows = [{"text": d, "metadata": m or {}}
                        for d, m in zip(docs, metas)]
                rows.sort(key=lambda r: str(r["metadata"].get("timestamp", "")),
                          reverse=True)
                return rows[:limit]
            except Exception as e:
                log.warning(f"persistent_memory.retrieve failed: {e}")
                return []
        rows = self._json_all()
        if metadata_filter:
            rows = [r for r in rows
                    if all(r.get(k) == v for k, v in metadata_filter.items())]
        rows.sort(key=lambda r: str(r.get("timestamp", "")), reverse=True)
        return [{"text": r.get("text", ""),
                 "metadata": {k: v for k, v in r.items() if k != "text"}}
                for r in rows[:limit]]

    def retrieve_relevant(self, query: str, max_results: int = 3) -> list:
        """Semantically closest stored items to `query`."""
        max_results = max(1, int(max_results or 3))
        if not (query or "").strip():
            return []
        if self.use_chroma:
            try:
                got = self.collection.query(query_texts=[query],
                                            n_results=max_results,
                                            include=["documents", "metadatas"])
                docs = (got.get("documents") or [[]])[0]
                metas = (got.get("metadatas") or [[]])[0]
                return [{"text": d, "metadata": m or {}}
                        for d, m in zip(docs, metas)]
            except Exception as e:
                log.warning(f"persistent_memory.retrieve_relevant failed: {e}")
                return []
        # JSON fallback: word overlap is crude but honest, and beats nothing.
        terms = {w for w in (query or "").lower().split() if len(w) > 3}
        scored = []
        for r in self._json_all():
            txt = str(r.get("text", ""))
            hits = sum(1 for t in terms if t in txt.lower())
            if hits:
                scored.append((hits, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"text": r.get("text", ""),
                 "metadata": {k: v for k, v in r.items() if k != "text"}}
                for _, r in scored[:max_results]]

    def retrieve_relevant_evolution(self, query: str, max_results: int = 3) -> str:
        """The shape the eight expert modules already call: plain text, or "".

        They do `past = persistent_memory.retrieve_relevant_evolution(...) or ""`
        and paste the result into a prompt, so a string is what they need.
        """
        rows = self.retrieve_relevant(query, max_results)
        if not rows:
            return ""
        out = []
        for r in rows:
            when = str(r["metadata"].get("timestamp", ""))[:10]
            out.append(f"- [{when}] {r['text'][:400]}")
        return "\n".join(out)


persistent_memory = PersistentMemory()