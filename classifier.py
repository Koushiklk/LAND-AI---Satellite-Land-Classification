"""
LAND AI - Classification module
----------------------------------
This ships with a MockClassifier so the whole app is runnable and
demoable the moment you unzip it - with no dataset or trained model
required.

WHEN YOUR DATASET / TRAINED MODEL IS READY:
  1. Put your model file(s) in the models/ folder.
  2. Implement a class with the same interface as MockClassifier below
     (a `.predict(aoi_coords, location_name)` method returning a
     {class_name: percentage} dict that sums to ~100).
  3. In app.py, change:
         classifier = MockClassifier()
     to:
         classifier = YourRealClassifier()

That's the entire integration point - nothing else in the app needs to
change, since routes only ever call `classifier.predict(...)`.
"""

import hashlib
import random

from config import Config
from gis_utils import polygon_area_km2


class MockClassifier:
    """
    Produces believable, *repeatable* land-cover percentages for a given
    AOI (same polygon -> same result every time, like a real model would),
    without needing any imagery, dataset, or trained weights.

    Replace this with your real CNN / Random Forest / etc. once trained.
    """

    def __init__(self, class_names=None):
        self.class_names = class_names or list(Config.LAND_CLASSES.keys())

    def _seed_from_coords(self, aoi_coords):
        raw = ";".join(f"{lat:.5f},{lng:.5f}" for lat, lng in aoi_coords)
        return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2**32)

    def predict(self, aoi_coords, location_name=""):
        seed = self._seed_from_coords(aoi_coords)
        rng = random.Random(seed)

        # random-but-repeatable weights, then normalize to sum to 100
        raw_weights = [rng.uniform(1, 10) for _ in self.class_names]
        total = sum(raw_weights)
        percentages = {
            cls: round(w / total * 100, 1)
            for cls, w in zip(self.class_names, raw_weights)
        }

        # fix rounding drift so it sums exactly to 100.0
        drift = round(100 - sum(percentages.values()), 1)
        top_class = max(percentages, key=percentages.get)
        percentages[top_class] = round(percentages[top_class] + drift, 1)

        return {
            "percentages": percentages,
            "area_km2": round(polygon_area_km2(aoi_coords), 3),
            "dominant_class": max(percentages, key=percentages.get),
            "seed": seed,  # reused to make the polygon grid match these percentages
        }
