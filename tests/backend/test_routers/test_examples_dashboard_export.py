"""Examples, the dashboard overview, and the export: what the routers return for an uploaded file."""
import json


def _upload(client, sample_jsonl):
    with open(sample_jsonl, "rb") as f:
        return client.post("/api/datasets/upload",
                           files={"file": ("sample.jsonl", f, "application/jsonl")}).json()["dataset_id"]


def test_examples_list_the_uploaded_rows(client, sample_jsonl):
    dataset_id = _upload(client, sample_jsonl)
    r = client.get("/api/examples", params={"dataset_id": dataset_id, "page_size": 50})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_the_dashboard_overview_answers_on_an_empty_database(client):
    r = client.get("/api/dashboard/overview")
    assert r.status_code == 200, r.text


def test_the_dashboard_overview_answers_with_data(client, sample_jsonl):
    _upload(client, sample_jsonl)
    r = client.get("/api/dashboard/overview")
    assert r.status_code == 200, r.text


def test_export_writes_the_examples_and_the_file_can_be_downloaded(client, sample_jsonl):
    dataset_id = _upload(client, sample_jsonl)
    r = client.post("/api/export", json={"dataset_ids": [dataset_id], "review_status": None})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_examples"] == 3
    d = client.get(body["download_url"])
    assert d.status_code == 200
    lines = [l for l in d.text.splitlines() if l.strip()]
    assert len(lines) == 3
    assert all("messages" in json.loads(l) for l in lines)
