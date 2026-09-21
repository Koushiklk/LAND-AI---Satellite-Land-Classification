"""
LAND AI - Satellite imagery plug-in point
--------------------------------------------
This project currently classifies purely from the drawn area's geometry
(see classifier.py -> MockClassifier), so no imagery download is required
to demo the full workflow.

When you're ready to fetch REAL satellite imagery for the selected AOI
(step 3 in the workflow), implement `fetch_image(aoi_coords)` below using
a provider such as:

  - Sentinel Hub          https://www.sentinel-hub.com/
  - Google Earth Engine   https://earthengine.google.com/
  - Planet Labs           https://www.planet.com/
  - NASA/USGS Landsat     https://earthexplorer.usgs.gov/

Typical steps inside fetch_image():
  1. Compute the bounding box of aoi_coords.
  2. Call the provider's API for the most recent, least-cloudy scene
     covering that bbox (most providers accept a bbox + date range +
     max cloud cover %).
  3. Download/clip the raster to the AOI and save it under
     Config.SATELLITE_CACHE_DIR.
  4. Return the local file path (and pass that path into your real
     classifier in classifier.py instead of the AOI-only mock).

Then in app.py's /api/classify route, call:
    image_path = fetch_image(aoi_coords)
    result = classifier.predict(image_path, aoi_coords, location_name)
and update classifier.py's `predict()` signature to accept the image.
"""

from config import Config


def fetch_image(aoi_coords):
    raise NotImplementedError(
        "Plug in a real satellite imagery provider here (see module docstring)."
    )
