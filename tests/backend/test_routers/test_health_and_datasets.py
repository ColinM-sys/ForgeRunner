"""The health check, and the datasets router: upload, list, get, delete, and the refusals."""


def test_health_answers_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "ForgeRunner"}


def test_upload_counts_good_and_bad_lines(client, sample_jsonl):
    with open(sample_jsonl, "rb") as f:
        r = client.post("/api/datasets/upload", files={"file": ("sample.jsonl", f, "application/jsonl")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid_lines"] == 3
    assert body["invalid_lines"] == 1
    assert body["filename"] == "sample.jsonl"


def test_upload_refuses_a_file_that_is_not_jsonl(client):
    r = client.post("/api/datasets/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_a_dataset_can_be_listed_fetched_and_deleted(client, sample_jsonl):
    with open(sample_jsonl, "rb") as f:
        dataset_id = client.post("/api/datasets/upload",
                                 files={"file": ("sample.jsonl", f, "application/jsonl")}).json()["dataset_id"]
    listed = client.get("/api/datasets").json()
    assert [d["id"] for d in listed] == [dataset_id]
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 200
    assert client.delete(f"/api/datasets/{dataset_id}").status_code in (200, 204)
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 404


def test_an_unknown_dataset_is_404(client):
    assert client.get("/api/datasets/does-not-exist").status_code == 404


def test_an_empty_database_lists_no_datasets(client):
    assert client.get("/api/datasets").json() == []
