# models/

Drop your trained model file(s) here (e.g. `land_classifier.h5`,
`land_classifier.pkl`, `land_classifier.pt`).

The app currently uses `MockClassifier` (see `classifier.py`) so it runs
without any model or dataset. Once you've trained a model on your own
dataset:

1. Save the trained model into this folder.
2. Add a new class in `classifier.py` that loads it and implements
   `.predict(aoi_coords, location_name)` returning a
   `{"percentages": {...}, "area_km2": ..., "dominant_class": ..., "seed": ...}`
   dict, matching `MockClassifier`'s output shape.
3. In `app.py`, swap `classifier = MockClassifier()` for your new class.

No other file needs to change.
