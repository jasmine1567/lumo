#!/usr/bin/env python3
"""Generate a square focus map from unmodified MLIT N03-2026 Kyushu coordinates.

Only clipping to the viewport and coordinate projection are performed. No geometry
simplification, AI completion, or manually traced coastline is used.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from urllib.request import urlretrieve
import geopandas as gpd
from shapely.geometry import box
from shapely.ops import transform, unary_union
from pyproj import CRS, Transformer
from PIL import Image, ImageDraw, ImageFont

SOURCE = "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/N03-20260101_59_GML.zip"
ROOT = Path(__file__).resolve().parents[1]
WIDTH = HEIGHT = 1000
SCALE = 2
CENTER_LAT, CENTER_LON = 32.088, 131.15
HALF_HEIGHT = 92000.0
HALF_WIDTH = HALF_HEIGHT * WIDTH / HEIGHT
projection = CRS.from_proj4(
    f"+proj=aeqd +lat_0={CENTER_LAT} +lon_0={CENTER_LON} +datum=WGS84 +units=m +no_defs"
)
project = Transformer.from_crs("EPSG:6668", projection, always_xy=True).transform
unproject = Transformer.from_crs(projection, "EPSG:6668", always_xy=True).transform

def px(x, y):
    return ((x + HALF_WIDTH) * WIDTH / (2 * HALF_WIDTH) * SCALE,
            (HALF_HEIGHT - y) * HEIGHT / (2 * HALF_HEIGHT) * SCALE)

def polys(g):
    if g.geom_type == "Polygon":
        yield g
    elif hasattr(g, "geoms"):
        for part in g.geoms:
            yield from polys(part)

def run():
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        archive = tmp / "N03.zip"
        print("Downloading official N03 Kyushu data", flush=True)
        urlretrieve(SOURCE, archive)
        with ZipFile(archive) as z:
            for name in z.namelist():
                if name.endswith((".shp", ".shx", ".dbf", ".prj", ".cpg")):
                    z.extract(name, tmp)
        pref = gpd.read_file(tmp / "N03-20260101_59_prefecture.shp")
        pref = pref[pref.intersects(box(129.5, 31.0, 132.9, 33.0))]
        by_pref = {}
        for name, geom in zip(pref.N03_001, pref.geometry):
            if geom is not None and not geom.is_empty:
                by_pref.setdefault(name, []).append(transform(project, geom))
        muni = gpd.read_file(tmp / "N03-20260101_59.shp")
        city = [transform(project, g) for g in muni[muni.N03_007 == "45202"].geometry]
        assert len(city) == 1, "N03_007 45202 must identify exactly one polygon"

        BG = "#FAF8F4"
        OTHER = "#EEEAE4"
        MIYAZAKI = "#E9D3AC"
        CITY = "#B8862B"
        BORDER = "#C9C0B1"
        CITY_BORDER = "#8A601D"
        canvas = Image.new("RGB", (WIDTH*SCALE, HEIGHT*SCALE), BG)
        draw = ImageDraw.Draw(canvas)

        def fill_geom(g, colour):
            for p in polys(g):
                draw.polygon([px(x,y) for x,y in p.exterior.coords], fill=colour)
                for inner in p.interiors:
                    draw.polygon([px(x,y) for x,y in inner.coords], fill=BG)

        for prefecture, gg in by_pref.items():
            if prefecture != "宮崎県":
                for g in gg:
                    fill_geom(g, OTHER)
        for g in by_pref.get("宮崎県", []):
            fill_geom(g, MIYAZAKI)
        for g in city:
            fill_geom(g, CITY)

        # Dissolve only shared internal municipal edges, preserving source vertices.
        for gg in by_pref.values():
            for p in polys(unary_union(gg)):
                for ring in [p.exterior, *p.interiors]:
                    coords = [px(x,y) for x,y in ring.coords]
                    if len(coords) > 1:
                        draw.line(coords+[coords[0]], fill=BORDER, width=2*SCALE, joint="curve")
        for g in city:
            for p in polys(g):
                coords = [px(x,y) for x,y in p.exterior.coords]
                draw.line(coords+[coords[0]], fill=CITY_BORDER, width=3*SCALE, joint="curve")

        f_dir = Path("/usr/share/fonts/opentype/noto")
        f_regular = f_dir / "NotoSansCJK-Regular.ttc"
        f_bold = f_dir / "NotoSansCJK-Bold.ttc"
        assert f_regular.is_file(), "Install fonts-noto-cjk on runner"
        regular = ImageFont.truetype(str(f_regular), 31*SCALE)
        medium = ImageFont.truetype(str(f_bold), 32*SCALE)
        bold = ImageFont.truetype(str(f_bold), 40*SCALE)

        def label(txt, lon, lat, kind="regular"):
            x,y = px(*project(lon,lat))
            font = bold if kind == "city" else medium if kind == "pref" else regular
            color = "#FFFFFF" if kind == "city" else "#403B33" if kind == "pref" else "#807668"
            bounds = draw.textbbox((0,0), txt, font=font)
            x -= (bounds[2]-bounds[0])/2
            y -= (bounds[3]-bounds[1])/2
            draw.text((x,y), txt, fill=color, font=font,
                      stroke_width=(1 if kind == "city" else 2)*SCALE,
                      stroke_fill=CITY if kind == "city" else BG)

        label("宮崎県",131.49,32.21,"pref")
        label("鹿児島県",130.53,31.59)
        label("熊本県",130.61,32.39)
        label("大分県",131.68,32.68)
        interior = unary_union(city).representative_point()
        lon,lat = unproject(interior.x, interior.y)
        label("都城市",lon,lat,"city")

        # Web PNG: retain source geometry during rendering; palette is lossless colour indexing
        resized = canvas.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        quantized = resized.quantize(colors=48, method=Image.Quantize.MEDIANCUT,
                                     dither=Image.Dither.NONE)
        target = ROOT / "images" / "area-map-focus.png"
        target.parent.mkdir(exist_ok=True)
        quantized.save(target, optimize=True, compress_level=9)
        print(f"Created {target}: {target.stat().st_size} bytes", flush=True)

if __name__ == "__main__":
    run()
