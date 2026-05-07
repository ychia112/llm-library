"""
Embedding-based re-clustering of all library sessions.
Uses UMAP for dimensionality reduction and HDBSCAN for clustering,
then asks the LLM to name each cluster once.
"""
import json
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llmlib.storage.db import LibraryDB


def _deserialize_embedding(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def _name_clusters_batch(
    clusters_reps: list[list[dict]],
    tagger,
) -> list[tuple[str, str]] | None:
    """
    Send ONE LLM call to name all clusters.
    clusters_reps: list of lists of {"title": ..., "summary": ...} dicts (up to 5 per cluster).
    Returns list of (topic, sub_topic) tuples, or None if parsing fails or length mismatches.
    """
    n = len(clusters_reps)
    cluster_lines = []
    for i, reps in enumerate(clusters_reps):
        titles = "\n".join(f'- "{r["title"]}"' for r in reps)
        cluster_lines.append(f"[{i}]\n{titles}")

    system_prompt = (
        "You name topic clusters for a personal knowledge library. "
        "For each cluster, assign a concise topic (2-4 words) and sub_topic (2-4 words). "
        "Return ONLY a JSON array, one object per cluster, in the same order."
    )
    user_msg = (
        f"Name these {n} clusters:\n\n"
        + "\n\n".join(cluster_lines)
        + '\n\nReply with JSON array:\n[{"topic": "...", "sub_topic": "..."}, ...]'
    )

    try:
        chat_model = getattr(tagger, "model", None)
        response = tagger.chat(system_prompt, user_msg, model=chat_model)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else parts[0]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
        if not isinstance(data, list) or len(data) != n:
            return None
        results = []
        for item in data:
            topic = str(item.get("topic", "General")).strip() or "General"
            sub_topic = str(item.get("sub_topic", "General")).strip() or "General"
            results.append((topic, sub_topic))
        return results
    except Exception:
        return None


def retopicize(
    db: "LibraryDB",
    tagger,
    target_topics: int = 15,
    dry_run: bool = False,
) -> dict:
    """
    Re-cluster all sessions using their embeddings.

    Args:
        db: open LibraryDB instance
        tagger: any tagger with .chat() method
        target_topics: hint for desired number of top-level topics (default 15)
        dry_run: if True, print assignments without writing to DB

    Returns:
        dict with keys: total, clusters_found, noise_count, assignments (list of dicts)
    """
    from llmlib.llm.tree import (
        assign_knowledge_tree,
        assign_knowledge_tree_batch,
        _fallback_single,
        _format_tree_for_prompt,
    )

    all_sessions = db.list_sessions(limit=100_000)
    if not all_sessions:
        return {"total": 0, "clusters_found": 0, "noise_count": 0, "assignments": []}

    session_by_id = {s.id: s for s in all_sessions}

    # Small dataset: skip UMAP/HDBSCAN, use batch assignment directly
    if len(all_sessions) < 10:
        topic_assignments = assign_knowledge_tree_batch(all_sessions, tagger, db)
        assignments = []
        updates = []
        for session, (topic, sub_topic) in zip(all_sessions, topic_assignments):
            assignments.append({"id": session.id, "title": session.title, "topic": topic, "sub_topic": sub_topic})
            updates.append((topic, sub_topic, session.id))
        if not dry_run:
            with db.conn:
                db.conn.executemany("UPDATE sessions SET topic = ?, sub_topic = ? WHERE id = ?", updates)
        return {"total": len(all_sessions), "clusters_found": 0, "noise_count": 0, "assignments": assignments}

    # Load embeddings from session_vectors (rowid lookup per session)
    embedded_data: list[tuple[str, list[float]]] = []
    for session in all_sessions:
        if session.embedding_id is None:
            continue
        vec_row = db.conn.execute(
            "SELECT embedding FROM session_vectors WHERE rowid = ?", (session.embedding_id,)
        ).fetchone()
        if vec_row is None:
            continue
        embedded_data.append((session.id, _deserialize_embedding(bytes(vec_row[0]))))

    # No embeddings at all — fall back to batch assignment for everything
    if not embedded_data:
        topic_assignments = assign_knowledge_tree_batch(all_sessions, tagger, db)
        assignments = []
        updates = []
        for session, (topic, sub_topic) in zip(all_sessions, topic_assignments):
            assignments.append({"id": session.id, "title": session.title, "topic": topic, "sub_topic": sub_topic})
            updates.append((topic, sub_topic, session.id))
        if not dry_run:
            with db.conn:
                db.conn.executemany("UPDATE sessions SET topic = ?, sub_topic = ? WHERE id = ?", updates)
        return {"total": len(all_sessions), "clusters_found": 0, "noise_count": len(all_sessions), "assignments": assignments}

    # UMAP + HDBSCAN — imports inside function so cluster extra is optional
    import numpy as np
    import umap as umap_mod
    import hdbscan as hdbscan_mod

    session_ids = [sid for sid, _ in embedded_data]
    embeddings_matrix = np.array([emb for _, emb in embedded_data])
    n = len(embeddings_matrix)

    reducer = umap_mod.UMAP(
        n_components=5,
        n_neighbors=min(15, n - 1),
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    reduced = reducer.fit_transform(embeddings_matrix)

    min_cluster_size = max(2, n // (target_topics * 2))
    clusterer = hdbscan_mod.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(reduced)

    # Group by cluster label
    cluster_map: dict[int, list[tuple[str, object]]] = {}
    noise_session_ids: list[str] = []

    for idx, (sid, lbl) in enumerate(zip(session_ids, labels.tolist())):
        if lbl == -1:
            noise_session_ids.append(sid)
        else:
            cluster_map.setdefault(lbl, []).append((sid, reduced[idx]))

    cluster_label_order = sorted(cluster_map.keys())
    n_clusters = len(cluster_label_order)

    # Pick up to 5 representative sessions per cluster (closest to centroid in reduced space)
    cluster_rep_sids: list[str] = []
    clusters_reps: list[list[dict]] = []

    for lbl in cluster_label_order:
        members = cluster_map[lbl]
        centroid = np.mean([emb for _, emb in members], axis=0)
        sorted_members = sorted(members, key=lambda x: float(np.linalg.norm(x[1] - centroid)))
        cluster_rep_sids.append(sorted_members[0][0])
        reps = []
        for sid, _ in sorted_members[:5]:
            s = session_by_id.get(sid)
            if s:
                reps.append({"title": s.title, "summary": s.summary or ""})
        clusters_reps.append(reps)

    # Name all clusters in ONE LLM call
    tree = db.get_knowledge_tree()
    tree_text = _format_tree_for_prompt(tree)

    cluster_names = _name_clusters_batch(clusters_reps, tagger)

    if cluster_names is None:
        # Fallback: name each cluster via its centroid-closest representative session
        cluster_names = []
        for rep_sid in cluster_rep_sids:
            rep_session = session_by_id.get(rep_sid)
            if rep_session:
                topic, sub_topic = _fallback_single(rep_session, tagger, tree_text)
            else:
                topic, sub_topic = "General", "General"
            cluster_names.append((topic, sub_topic))

    label_to_name: dict[int, tuple[str, str]] = {
        lbl: cluster_names[i] for i, lbl in enumerate(cluster_label_order)
    }

    assignments: list[dict] = []
    updates: list[tuple] = []

    # Clustered sessions
    for sid, lbl in zip(session_ids, labels.tolist()):
        if lbl == -1:
            continue
        topic, sub_topic = label_to_name[lbl]
        s = session_by_id.get(sid)
        assignments.append({"id": sid, "title": s.title if s else sid, "topic": topic, "sub_topic": sub_topic})
        updates.append((topic, sub_topic, sid))

    # Noise sessions — classify individually (outliers don't belong to any cluster)
    noise_count = len(noise_session_ids)
    for sid in noise_session_ids:
        s = session_by_id.get(sid)
        if s:
            topic, sub_topic = assign_knowledge_tree(s, tagger, db)
        else:
            topic, sub_topic = "General", "General"
        assignments.append({"id": sid, "title": s.title if s else sid, "topic": topic, "sub_topic": sub_topic})
        updates.append((topic, sub_topic, sid))

    # Sessions with no embedding — assign "General"/"General"
    embedded_set = set(session_ids)
    for s in all_sessions:
        if s.id not in embedded_set:
            assignments.append({"id": s.id, "title": s.title, "topic": "General", "sub_topic": "General"})
            updates.append(("General", "General", s.id))

    if not dry_run:
        with db.conn:
            db.conn.executemany(
                "UPDATE sessions SET topic = ?, sub_topic = ? WHERE id = ?",
                updates,
            )

    return {
        "total": len(all_sessions),
        "clusters_found": n_clusters,
        "noise_count": noise_count,
        "assignments": assignments,
    }
