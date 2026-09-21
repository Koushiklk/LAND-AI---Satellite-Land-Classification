"""
LAND AI - GIS utilities
-------------------------
Deliberately dependency-free (pure Python) so the project runs with
nothing but Flask installed. If you install GeoPandas / Shapely /
Rasterio / Fiona / PyProj (already listed in requirements.txt), you can
swap these simple implementations for their more robust equivalents -
the function signatures below are the seam to do that.

Coordinates are handled as (lat, lng) pairs throughout, matching what
Leaflet sends from the browser.
"""

import math


# ---------------- area ----------------

def polygon_area_km2(coords):
    """
    Approximate geodesic area of a lat/lng polygon using an equirectangular
    projection (accurate enough for city/district-sized AOIs). coords is a
    list of (lat, lng) tuples, not necessarily closed.
    """
    if len(coords) < 3:
        return 0.0

    R = 6371.0  # Earth radius, km
    lat0 = sum(c[0] for c in coords) / len(coords)
    lat0_rad = math.radians(lat0)

    # project to a local flat x/y plane in km
    pts = []
    for lat, lng in coords:
        x = math.radians(lng) * R * math.cos(lat0_rad)
        y = math.radians(lat) * R
        pts.append((x, y))

    # shoelace formula
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _signed_area_xy(points):
    """Signed shoelace area of (x, y) points. Positive = counter-clockwise."""
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def ensure_ccw(points):
    """Return `points` re-ordered counter-clockwise if needed. The clipping
    algorithm below assumes a CCW clip polygon; a hand-drawn AOI can come in
    either winding order depending on how the user drew it, so this must be
    called on it before clipping."""
    if _signed_area_xy(points) < 0:
        return list(reversed(points))
    return points


def polygon_bounds(coords):
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return min(lats), min(lngs), max(lats), max(lngs)  # south, west, north, east


# ---------------- clipping (Sutherland-Hodgman) ----------------

def _inside(pt, edge_start, edge_end):
    x, y = pt
    x1, y1 = edge_start
    x2, y2 = edge_end
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1) >= 0


def _intersect(p1, p2, edge_start, edge_end):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = edge_start
    x4, y4 = edge_end
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return p2
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def clip_polygon(subject, clip_poly):
    """Clip `subject` polygon against convex-or-concave `clip_poly` (Sutherland-Hodgman).
    Both are lists of (x, y) tuples. Works well for our roughly-convex,
    hand-drawn AOIs and grid squares."""
    output = subject
    cn = len(clip_poly)
    for i in range(cn):
        if not output:
            break
        edge_start = clip_poly[i]
        edge_end = clip_poly[(i + 1) % cn]
        input_list = output
        output = []
        if not input_list:
            continue
        s = input_list[-1]
        for e in input_list:
            if _inside(e, edge_start, edge_end):
                if not _inside(s, edge_start, edge_end):
                    output.append(_intersect(s, e, edge_start, edge_end))
                output.append(e)
            elif _inside(s, edge_start, edge_end):
                output.append(_intersect(s, e, edge_start, edge_end))
            s = e
    return output


# ---------------- grid + classification -> polygons ----------------

def make_classified_grid(aoi_coords, class_weights, grid_size=8, seed=0):
    """
    Build a grid of cells covering the AOI's bounding box, clip each cell
    to the AOI polygon, and assign each a land-cover class using the given
    {class_name: weight_percent} distribution.

    Returns a list of dicts: {"class": str, "color": str, "ring": [(lat,lng), ...]}
    This is the "raster classification -> vector polygons" step, done in a
    simplified, dependency-free way. Swap for rasterio.features.shapes()
    once you have a real classified raster from your model.
    """
    import random as _random
    rng = _random.Random(seed)

    south, west, north, east = polygon_bounds(aoi_coords)
    # work in (lng, lat) == (x, y) for the clipper; normalize winding order
    # since a hand-drawn AOI can come in either direction.
    aoi_xy = ensure_ccw([(lng, lat) for lat, lng in aoi_coords])

    classes = list(class_weights.keys())
    weights = list(class_weights.values())

    dx = (east - west) / grid_size
    dy = (north - south) / grid_size

    cells = []
    for i in range(grid_size):
        for j in range(grid_size):
            x0 = west + i * dx
            x1 = x0 + dx
            y0 = south + j * dy
            y1 = y0 + dy
            cell_xy = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

            clipped = clip_polygon(cell_xy, aoi_xy)
            if len(clipped) < 3:
                continue  # cell lies outside the AOI

            land_class = rng.choices(classes, weights=weights, k=1)[0]
            ring = [(lat, lng) for lng, lat in clipped]
            cells.append({
                "class": land_class,
                "ring": ring,
            })
    return cells


def cells_to_geojson(cells, class_colors, properties_extra=None):
    features = []
    for cell in cells:
        # GeoJSON wants [lng, lat] and a CLOSED ring
        ring = [[lng, lat] for lat, lng in cell["ring"]]
        if ring[0] != ring[-1]:
            ring.append(ring[0])

        props = {
            "land_class": cell["class"],
            "color": class_colors.get(cell["class"], "#888888"),
        }
        if properties_extra:
            props.update(properties_extra)

        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
        })

    return {"type": "FeatureCollection", "features": features}


def aoi_to_geojson(aoi_coords, properties=None):
    ring = [[lng, lat] for lat, lng in aoi_coords]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }
