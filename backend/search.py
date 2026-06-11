"""
search.py — Búsqueda híbrida con Cross-Encoder re-ranking
BM25 + Vectorial + RRF + Cross-Encoder multilingüe = máxima precisión
"""

import pickle
import pathlib
from typing import List, Dict, Any, Optional

import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from utils import tokenize

# ─── Configuración ──────────────────────────────────────────────────────────
BASE_DIR        = pathlib.Path(__file__).parent
CHROMA_DIR      = str(BASE_DIR / "chroma_db")
BM25_PATH       = str(BASE_DIR / "bm25_index.pkl")
COLLECTION      = "candidatos_docs"
EMBED_MODEL     = "paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_MODEL  = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # Multilingüe ES+EN
K_RRF           = 60
N_CANDIDATES    = 15   # Candidatos antes del re-ranking (40 era demasiado lento en CPU)
TOP_K_DEFAULT   = 6    # Resultados finales


class HybridSearch:
    def __init__(self):
        print("🔍 Cargando motor de búsqueda...")

        # Modelo de embeddings (bi-encoder)
        self.model = SentenceTransformer(EMBED_MODEL)

        # Cross-encoder para re-ranking de alta precisión
        print("   🎯 Cargando cross-encoder multilingüe...")
        print("      (primera vez: descarga ~67MB, luego queda en caché)")
        self.reranker = CrossEncoder(RERANKER_MODEL)
        print("   ✅ Cross-encoder listo")

        # ChromaDB
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = client.get_collection(COLLECTION)

        # BM25 + metadata
        with open(BM25_PATH, "rb") as f:
            data = pickle.load(f)
        self.bm25     = data["bm25"]
        self.metadata = data["metadata"]

        total = self.collection.count()
        cands = sum(1 for m in self.metadata if m["tipo"] == "candidato")
        refs  = sum(1 for m in self.metadata if m["tipo"] == "referencia")
        print(f"   ✅ {total} fragmentos listos "
              f"({cands} candidatos | {refs} referencia)\n")

    def search(
        self,
        query: str,
        top_k: int = TOP_K_DEFAULT,
        candidato: Optional[str] = None,
        tipo: Optional[str] = None,
        categoria: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda en 4 etapas:
        1. BM25: top N_CANDIDATES por palabras clave
        2. Vectorial: top N_CANDIDATES por similitud semántica
        3. RRF: fusión de rankings
        4. Cross-encoder: re-ranking de precisión sobre los top 40
        """
        n = min(N_CANDIDATES, self.collection.count())

        # ── 1. BM25 ───────────────────────────────────────────────────────
        tokens      = tokenize(query)
        bm25_scores = self.bm25.get_scores(tokens)

        bm25_ranked = [
            (idx, bm25_scores[idx])
            for idx, m in enumerate(self.metadata)
            if (not candidato or m.get("candidato")    == candidato)
            and (not tipo      or m.get("tipo")         == tipo)
            and (not categoria or m.get("categoria_fc") == categoria)
        ]
        bm25_ranked.sort(key=lambda x: x[1], reverse=True)
        bm25_ranks: Dict[str, int] = {
            self.metadata[idx]["id"]: rank
            for rank, (idx, _) in enumerate(bm25_ranked[:n])
        }

        # ── 2. Búsqueda vectorial ─────────────────────────────────────────
        conds = []
        if candidato: conds.append({"candidato":    {"$eq": candidato}})
        if tipo:      conds.append({"tipo":         {"$eq": tipo}})
        if categoria: conds.append({"categoria_fc": {"$eq": categoria}})
        if   len(conds) == 1: where_filter = conds[0]
        elif len(conds) >  1: where_filter = {"$and": conds}
        else:                 where_filter = None

        query_emb = self.model.encode([query], normalize_embeddings=True)[0].tolist()
        vec_res   = self.collection.query(
            query_embeddings=[query_emb],
            n_results=n,
            where=where_filter,
            include=["metadatas", "distances"],
        )
        vector_ranks: Dict[str, int] = {
            doc_id: rank
            for rank, doc_id in enumerate(vec_res["ids"][0])
        }

        # ── 3. RRF Fusion ─────────────────────────────────────────────────
        all_ids = set(bm25_ranks) | set(vector_ranks)
        rrf: Dict[str, float] = {
            doc_id: (
                1 / (K_RRF + bm25_ranks.get(doc_id,  n)) +
                1 / (K_RRF + vector_ranks.get(doc_id, n))
            )
            for doc_id in all_ids
        }
        fused_ids = sorted(rrf, key=rrf.get, reverse=True)[:N_CANDIDATES]

        # ── 4. Cross-Encoder Re-Ranking ───────────────────────────────────
        meta_index = {m["id"]: m for m in self.metadata}

        # Construir pares (query, texto) para el cross-encoder
        candidates = [cid for cid in fused_ids if cid in meta_index]
        if not candidates:
            return []

        pairs  = [(query, meta_index[cid]["text"]) for cid in candidates]
        scores = self.reranker.predict(pairs, show_progress_bar=False)

        # Ordenar por score del cross-encoder (más preciso que RRF)
        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )

        # Construir resultados finales
        results = []
        for cid, score in ranked[:top_k]:
            if cid not in meta_index:
                continue
            m = meta_index[cid]
            results.append({
                "id":                 cid,
                "text":               m["text"],
                "title":              m["title"],
                "source":             m["source"],
                "tipo":               m["tipo"],
                "candidato":          m["candidato"],
                "lang":               m["lang"],
                "categoria_fc":       m.get("categoria_fc", ""),
                "candidato_afectado": m.get("candidato_afectado", ""),
                "veredicto":          m.get("veredicto", ""),
                "score":              round(float(score), 4),
            })

        return results
