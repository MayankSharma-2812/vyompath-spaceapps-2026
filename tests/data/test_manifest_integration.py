"""Integration test to verify that backend/app/api/layers.py loads data/layers.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
from backend.app.api.layers import list_layers


def test_layers_endpoint_loads_manifest():
    res = asyncio.run(list_layers())
    assert res["source"] == "data/layers.json", f"Expected data/layers.json but got {res['source']}"
    assert res["count"] >= 4, f"Expected at least 4 layers, got {res['count']}"
    
    layer_ids = [lyr["id"] for lyr in res["layers"]]
    assert "mola-colorhillshade" in layer_ids
    assert "ctx-mosaic" in layer_ids
    assert "viking-mdim21" in layer_ids
    assert "mola-elevation-dem" in layer_ids
    print(f"PASSED: Backend successfully loaded {res['count']} verified NASA layers from data/layers.json!")


if __name__ == "__main__":
    test_layers_endpoint_loads_manifest()
