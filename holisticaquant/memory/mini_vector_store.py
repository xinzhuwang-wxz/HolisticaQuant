"""
Mini vector store for financial insights.

This module provides a lightweight embedding + persistence layer using sqlite3.
Designed to work within limited environment (no heavy external vector DB dependencies).
"""

from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import Iterable, List, Tuple, Optional

import numpy as np
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore

EMBED_DIM = 768


class MiniVectorStore:
    """A tiny vector store based on sqlite + sentence-transformers embedding."""

    def __init__(
        self,
        db_path: Path,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers 未安装，无法启用向量记忆。请运行 `pip install sentence-transformers`。"
            )
        self.db_path = db_path
        self.model_name = model_name
        self._ensure_dir()
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_table()
        self.model = None

    def _ensure_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def _init_table(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT,
                content TEXT,
                metadata TEXT,
                timestamp TEXT,
                embedding BLOB
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON insights(timestamp)")
        self.conn.commit()

    def _load_model(self):
        if self.model is not None:
            return
        if SentenceTransformer is None:
            raise RuntimeError(
                "SentenceTransformer not available. Please install sentence-transformers."
            )
        self.model = SentenceTransformer(self.model_name)

    def _embed(self, texts: Iterable[str]) -> np.ndarray:
        self._load_model()
        assert self.model is not None
        embeddings = self.model.encode(
            list(texts), normalize_embeddings=True, convert_to_numpy=True
        )
        return embeddings.astype(np.float32)

    def add(
        self,
        insight_type: str,
        content: str,
        metadata: dict,
        timestamp: str,
    ) -> int:
        """Save an insight with embedding."""
        embedding = self._embed([content])[0]
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO insights (insight_type, content, metadata, timestamp, embedding)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                insight_type,
                content,
                json.dumps(metadata, ensure_ascii=False),
                timestamp,
                embedding.tobytes(),
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        insight_type: Optional[str] = None,
    ) -> List[Tuple[int, str, str, dict, str, float]]:
        """Cosine similarity search."""
        embedding = self._embed([query])[0]
        cur = self.conn.cursor()
        if insight_type:
            cur.execute(
                "SELECT id, insight_type, content, metadata, timestamp, embedding FROM insights WHERE insight_type=?",
                (insight_type,),
            )
        else:
            cur.execute("SELECT id, insight_type, content, metadata, timestamp, embedding FROM insights")
        rows = cur.fetchall()
        if not rows:
            return []
        ids, types, contents, metadatas, timestamps, embeddings = zip(*rows)
        embedding_matrix = np.vstack(
            [np.frombuffer(e, dtype=np.float32) for e in embeddings]
        )
        scores = np.dot(embedding_matrix, embedding)
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_idx:
            score = float(scores[idx])
            results.append(
                (
                    ids[idx],
                    types[idx],
                    contents[idx],
                    json.loads(metadatas[idx]),
                    timestamps[idx],
                    score,
                )
            )
        return results

    def delete_older_than(self, cutoff_iso: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM insights WHERE timestamp < ?", (cutoff_iso,))
        self.conn.commit()

    def delete_ids(self, ids: Iterable[int]):
        cur = self.conn.cursor()
        cur.executemany("DELETE FROM insights WHERE id = ?", [(i,) for i in ids])
        self.conn.commit()

    def fetch_all(self) -> List[Tuple[int, str, str, dict, str]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, insight_type, content, metadata, timestamp FROM insights ORDER BY timestamp ASC"
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            vector_id, insight_type, content, metadata, timestamp = row
            try:
                metadata_obj = json.loads(metadata)
            except Exception:
                metadata_obj = {}
            results.append((vector_id, insight_type, content, metadata_obj, timestamp))
        return results


__all__ = ["MiniVectorStore"]

