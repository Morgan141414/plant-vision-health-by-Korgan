"""Optional local ML engines for PlantVision AI.

The package deliberately has no hard dependency on PyTorch.  Importing the API
service must remain lightweight; model loading is explicit and local-only.
"""

from .classifier import PlantClassification, PlantClassifier

__all__ = ["PlantClassification", "PlantClassifier"]
