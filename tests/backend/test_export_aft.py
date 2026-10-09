"""The 'for Auto Fine Tuner' export: exactly {"messages": [...]} per line, and the file round-trips into the trainer.

The sample has a row that carries an extra key (metadata): the raw export keeps it, the Auto Fine Tuner export drops it.
The round trip runs auto-fine-tuner's own importer when its repo is on this PC, and is skipped otherwise.
"""
import json
import os
from pathlib import Path

import pytest

MESSAGES_ROWS = [
    {"messages": [{"role": "system", "content": "Be brief."},
                  {"role": "user", "content": "What is the refund window?"},
                  {"role": "assistant", "content": "Refunds are accepted within 30 days."}],
     "metadata": {"source": "faq", "review_status": "approved"}},
    {"messages": [{"role": "user", "content": "¿Cuánto cuesta el plan?"},
                  {"role": "assistant", "content": "Depende del plan."}]},
]


@pytest.fixture
def metadata_jsonl(tmp_path):
    path = tmp_path / "meta.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in MESSAGES_ROWS) + "\n", encoding="utf-8")
    return path


def _upload(client, path):
    with open(path, "rb") as f:
        return client.post("/api/datasets/upload", files={"file": ("meta.jsonl", f, "application/jsonl")}).json()


def _export_and_download(client, dataset_id, export_format=None):
    body = {"dataset_ids": [dataset_id], "review_status": None}
    if export_format is not None:
        body["format"] = export_format
    r = client.post("/api/export", json=body)
    assert r.status_code == 200, r.text
    d = client.get(r.json()["download_url"])
    assert d.status_code == 200
    return r.json(), [json.loads(l) for l in d.text.splitlines() if l.strip()]


def test_the_aft_export_is_exactly_the_messages_object_per_line(client, metadata_jsonl):
    dataset_id = _upload(client, metadata_jsonl)["dataset_id"]
    summary, rows = _export_and_download(client, dataset_id, "aft")
    assert summary["filename"].startswith("aft_")
    assert summary["total_examples"] == 2
    assert all(set(row) == {"messages"} for row in rows), rows
    assert [row["messages"] for row in rows] == [r["messages"] for r in MESSAGES_ROWS]


def test_the_raw_export_is_unchanged_and_still_keeps_the_other_keys(client, metadata_jsonl):
    dataset_id = _upload(client, metadata_jsonl)["dataset_id"]
    _, default_rows = _export_and_download(client, dataset_id)
    _, raw_rows = _export_and_download(client, dataset_id, "raw")
    assert default_rows == raw_rows
    assert "metadata" in raw_rows[0]


def test_an_unknown_format_is_refused(client, metadata_jsonl):
    dataset_id = _upload(client, metadata_jsonl)["dataset_id"]
    r = client.post("/api/export", json={"dataset_ids": [dataset_id], "review_status": None, "format": "csv"})
    assert r.status_code == 422


def test_the_round_trip_loads_in_auto_fine_tuners_importer(client, metadata_jsonl, tmp_path):
    aft_path = Path(os.environ.get("AFT_PATH", Path.home() / "Documents" / "GitHub" / "auto-fine-tuner"))
    importer = aft_path / "src" / "forgerunner_agent" / "import_forgerunner.py"
    if not importer.exists():
        pytest.skip("auto-fine-tuner is not on this PC")
    import importlib.util
    spec = importlib.util.spec_from_file_location("aft_import", importer)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    dataset_id = _upload(client, metadata_jsonl)["dataset_id"]
    export = client.post("/api/export", json={"dataset_ids": [dataset_id], "review_status": None, "format": "aft"}).json()
    src = tmp_path / "export.jsonl"
    src.write_bytes(client.get(export["download_url"]).content)
    dest = tmp_path / "training_data.jsonl"
    report = mod.convert(str(src), str(dest))
    assert report["rows"] == 2 and report["extra_keys"] == {}
    back = [json.loads(l)["messages"] for l in dest.read_text(encoding="utf-8").splitlines()]
    assert back == [r["messages"] for r in MESSAGES_ROWS]
