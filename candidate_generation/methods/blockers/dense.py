"""Dense-retrieval blocking: (1) off-the-shelf LM embeddings + kNN, (2) contrastive fine-tuning,
(3) an LSH-on-embeddings stand-in for neural LSH.
Needs: pip install sentence-transformers faiss-cpu"""
import numpy as np


def encode(model, texts, batch_size=64) -> np.ndarray:
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        convert_to_numpy=True, show_progress_bar=False).astype("float32")


def knn_candidates(emb_q, ids_q, emb_idx, ids_idx, k=10, hnsw=False) -> set:
    """For every query vector return its top-k nearest index vectors (cosine, vectors are normalised)."""
    import faiss
    d = emb_idx.shape[1]
    index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT) if hnsw else faiss.IndexFlatIP(d)
    index.add(emb_idx)
    _, nn = index.search(emb_q, min(k, len(ids_idx)))
    return {(ids_q[i], ids_idx[j]) for i, row in enumerate(nn) for j in row if j >= 0}


def dense_knn(A: dict, B: dict, model="sentence-transformers/LaBSE", k=10, batch_size=64,
              hnsw=False, both_directions=True, device=None) -> set:
    """Method 1. `model` = a model name OR an already loaded SentenceTransformer (e.g. fine-tuned)."""
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model, device=device) if isinstance(model, str) else model
    ids_a, ids_b = list(A), list(B)
    ea = encode(m, [A[i] for i in ids_a], batch_size)
    eb = encode(m, [B[i] for i in ids_b], batch_size)
    cands = knn_candidates(ea, ids_a, eb, ids_b, k, hnsw)                     # A -> B
    if both_directions:                                                        # B -> A, then union
        cands |= {(a, b) for b, a in knn_candidates(eb, ids_b, ea, ids_a, k, hnsw)}
    return cands


def finetune_contrastive(base_model: str, A: dict, B: dict, train_pairs, epochs=3,
                         batch_size=32, out_dir="blocker-model"):
    """Method 2 (APPROXIMATION of SC-Block): bi-encoder fine-tuned on known matching pairs with an
    in-batch-negatives contrastive loss. NOT the authors' exact supervised-contrastive objective."""
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from sentence_transformers.datasets import NoDuplicatesDataLoader
    model = SentenceTransformer(base_model)
    examples = [InputExample(texts=[A[a], B[b]]) for a, b in train_pairs]
    loader = NoDuplicatesDataLoader(examples, batch_size=batch_size)   # no repeated text per batch
    loss = losses.MultipleNegativesRankingLoss(model)
    model.fit(train_objectives=[(loader, loss)], epochs=epochs,
              warmup_steps=max(1, int(0.1 * len(loader) * epochs)), show_progress_bar=True)
    model.save(out_dir)
    return model


def dense_lsh(A: dict, B: dict, model, nbits=256, k=10, batch_size=64) -> set:
    """Method 3 (STAND-IN for NLSHBlock): random-hyperplane LSH codes over (fine-tuned) embeddings,
    Hamming-distance kNN. NLSHBlock itself LEARNS the hash function; this does not."""
    import faiss
    ids_a, ids_b = list(A), list(B)
    ea = encode(model, [A[i] for i in ids_a], batch_size)
    eb = encode(model, [B[i] for i in ids_b], batch_size)
    index = faiss.IndexLSH(eb.shape[1], nbits)
    index.add(eb)
    _, nn = index.search(ea, min(k, len(ids_b)))
    return {(ids_a[i], ids_b[j]) for i, row in enumerate(nn) for j in row if j >= 0}
