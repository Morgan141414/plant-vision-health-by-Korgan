import numpy as np

from app.ml.classifier import PlantClassifier


def test_classifier_reports_missing_local_assets_without_guessing(tmp_path):
    result = PlantClassifier(
        model_path=tmp_path / "species.pt",
        labels_path=tmp_path / "species_labels.txt",
    ).classify(np.zeros((20, 20, 3), dtype=np.uint8))

    assert result.name == "unavailable"
    assert result.confidence is None
    assert result.mode == "unavailable"
    assert result.reason == "local model or labels file not found"
