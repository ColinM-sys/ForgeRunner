"""The review routes over HTTP. POST /batch is a static path; it must not be taken for the single-review route /{example_id}.

Evidence: master declared /batch after /{example_id}, so POST /api/review/batch was read as an example id and answered 404.
"""
import json


def _upload_two(client, tmp_path):
    path = tmp_path / "two.jsonl"
    rows = [{"messages": [{"role": "user", "content": f"question {i}"},
                          {"role": "assistant", "content": f"answer {i}"}]} for i in range(2)]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    with open(path, "rb") as f:
        dataset_id = client.post("/api/datasets/upload",
                                 files={"file": ("two.jsonl", f, "application/jsonl")}).json()["dataset_id"]
    items = client.get("/api/examples", params={"dataset_id": dataset_id}).json()["items"]
    return [it["id"] for it in items]


def test_a_batch_review_over_http_reviews_every_id(client, tmp_path):
    """FAIL-FIRST on master: POST /api/review/batch is answered 404 by the single-review route."""
    ids = _upload_two(client, tmp_path)
    r = client.post("/api/review/batch", json={"example_ids": ids, "action": "approved"})
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 2
    for example_id in ids:
        detail = client.get(f"/api/examples/{example_id}").json()
        assert detail["review_status"] == "approved", detail


def test_a_single_review_still_reaches_the_single_route(client, tmp_path):
    """Control: the dynamic route still takes an example id."""
    ids = _upload_two(client, tmp_path)
    r = client.post(f"/api/review/{ids[0]}", json={"action": "rejected"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "reviewed" and r.json()["example_id"] == ids[0]
    assert client.get(f"/api/examples/{ids[0]}").json()["review_status"] == "rejected"
