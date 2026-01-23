from __future__ import annotations

"""
autovisuals.get_meta

Generate stock metadata CSVs for:
  - Adobe Stock
  - Shutterstock
  - Freepik

based on:
  - mj_downloads/YYYY-MM-DD/<category>/* image files
  - prompt/YYYY-MM-DD/<category>/meta.json  (from get_mj_prompt.py)

Each Midjourney prompt typically generates multiple images from the same
base metadata record. This module adds an extra diversification layer so
that *each individual image* gets slightly different:

  - Title
  - Keywords (order / emphasis)
  - Description

to reduce "similar content" rejections on stock platforms.
"""

import argparse
import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Paths / project root
# ---------------------------------------------------------------------------


def _get_project_root() -> Path:
    """Return project root (parent of the autovisuals/ package)."""
    here = Path(__file__).resolve().parent  # autovisuals/
    return here.parent  # AutoVisuals/


PROJECT_ROOT = _get_project_root()

# Defaults are *directories*, relative to project root if not absolute
DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "mj_downloads"
DEFAULT_OUT_PROMPT = PROJECT_ROOT / "prompt"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "meta"


# ---------------------------------------------------------------------------
# Category mapping (Adobe / Shutterstock codes)
# ---------------------------------------------------------------------------


@dataclass
class CategoryMap:
    """Mapping of category names to Adobe codes and platform categories."""

    adobe_cat: str
    adobe_code: int
    shutterstock_cat: str


def load_category_mapping(data_root: Path | None = None) -> Dict[str, CategoryMap]:
    """
    Load cat_map.csv and build a mapping of adobe_cat -> CategoryMap.

    CSV format (autovisuals/data/cat_map.csv):

        adobe_cat,adobe_code,shutterstock_cat
        animals,5,Animals/Wildlife
        ...

    If the file is missing, an empty mapping is returned and we fall back
    to sensible defaults.
    """
    if data_root is None:
        data_root = PROJECT_ROOT / "autovisuals" / "data"

    cat_map_path = data_root / "cat_map.csv"
    mapping: Dict[str, CategoryMap] = {}

    if not cat_map_path.exists():
        logging.warning("Category mapping file not found: %s", cat_map_path)
        return mapping

    try:
        with cat_map_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                adobe_cat = (row.get("adobe_cat") or "").strip()
                if not adobe_cat:
                    continue
                try:
                    adobe_code = int(row.get("adobe_code") or 0)
                except ValueError:
                    adobe_code = 0
                shutter_cat = (row.get("shutterstock_cat") or "").strip()
                mapping[adobe_cat] = CategoryMap(
                    adobe_cat=adobe_cat,
                    adobe_code=adobe_code,
                    shutterstock_cat=shutter_cat,
                )
    except Exception as e:  # defensive
        logging.warning("Error loading category mapping: %s", e)

    return mapping


# ---------------------------------------------------------------------------
# Slug helpers (must match mj_download.py behaviour)
# ---------------------------------------------------------------------------


def slugify_title(title: str) -> str:
    """
    Slugify a title in the same way mj_download.py does for filenames.
    """
    if not title:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9\-]+", "_", title).strip("_")
    return slug


def extract_title_slug_from_filename(stem: str) -> str:
    """
    Given an image stem like:
        "golden_sunrise_over_misty_mountains_0003_02"
    return:
        "golden_sunrise_over_misty_mountains"

    If no numeric suffix is present, return the stem as-is.
    """
    m = re.match(r"(.+)_\d{4}(?:_\d{2})?$", stem)
    if m:
        return m.group(1)
    return stem


def split_filename_group_and_variant(filename: str) -> Tuple[str, int]:
    """
    Split an image filename into (group_key, variant_index).

    Example filenames:

        Minimal_Winter_Night_Landscape_in_Snowfall_0003_01.png
        Minimal_Winter_Night_Landscape_in_Snowfall_0003_02-standard-scale-6_00x.jpeg

    Both should resolve to the same group_key and different variant indices.
    """
    stem = Path(filename).stem

    # Strip one or more Topaz-style suffixes if present, e.g.:
    #   "..._0003_01-standard-scale-6_00x"
    #   "..._0003_01-standard-scale-6_00x-standard-scale-4_00x"
    core = re.sub(r"(?:-standard-scale-[0-9_x]+)+$", "", stem)

    # Match "..._0003_01"
    m = re.match(r"(.+)_\d{4}_(\d{2})$", core)
    if m:
        group_key = m.group(1)
        variant = int(m.group(2))
        return group_key, variant

    # Match "..._0003"
    m2 = re.match(r"(.+)_\d{4}$", core)
    if m2:
        group_key = m2.group(1)
        return group_key, 1

    # Fallback: whole stem as group, variant 1
    return core, 1


def find_latest_date_dir(root: Path) -> str:
    """
    Find the latest YYYY-MM-DD directory name under root.
    """
    candidates: List[str] = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        name = p.name
        try:
            _ = date.fromisoformat(name)
            candidates.append(name)
        except ValueError:
            continue

    if not candidates:
        raise FileNotFoundError(f"No dated subdirectories found under {root}")

    return sorted(candidates)[-1]


# ---------------------------------------------------------------------------
# Loading meta.json from prompt/
# ---------------------------------------------------------------------------


def load_category_meta(
    prompt_root: Path, date_str: str, category: str
) -> Tuple[Dict[str, dict], Optional[dict]]:
    """
    Load meta.json for a single category and build:
        slug -> record

    Returns (mapping, default_record)
    """
    cat_dir = prompt_root / date_str / category
    meta_path = cat_dir / "meta.json"
    mapping: Dict[str, dict] = {}
    default_rec: Optional[dict] = None

    if not meta_path.exists():
        return mapping, default_rec

    try:
        records = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning("Could not read meta.json for %s/%s: %s", date_str, category, e)
        return mapping, default_rec

    if not isinstance(records, list):
        logging.warning("meta.json for %s/%s is not a list", date_str, category)
        return mapping, default_rec

    for rec in records:
        if not isinstance(rec, dict):
            continue
        title = str(rec.get("title", "")).strip()
        if not title:
            title = str(rec.get("theme", "")).strip()
        slug = slugify_title(title) or category
        if slug not in mapping:
            mapping[slug] = rec
        if default_rec is None:
            default_rec = rec

    return mapping, default_rec


# ---------------------------------------------------------------------------
# Keyword / text helpers with per-image diversification
# ---------------------------------------------------------------------------


def _normalize_base_keywords(raw_kw) -> List[str]:
    """
    Normalise a keywords field from meta.json into a clean list of strings.
    """
    if isinstance(raw_kw, list):
        kws = [str(k or "").strip() for k in raw_kw]
    elif isinstance(raw_kw, str):
        kws = [p.strip() for p in raw_kw.split(",") if p.strip()]
    else:
        kws = []

    # De-duplicate while preserving order
    seen = set()
    out: List[str] = []
    for k in kws:
        low = k.lower()
        if not low:
            continue
        if low in seen:
            continue
        seen.add(low)
        # normalise "generative ai" spelling
        if low == "generative ai":
            out.append("generative AI")
        else:
            out.append(k)
    return out


def join_keywords(rec: dict, filename: str | None = None) -> str:
    """
    Turn rec['keywords'] into a comma-separated string.

    If a filename is provided, apply a deterministic rotation based on the
    variant index embedded in the filename so that each image from the same
    prompt has slightly different keyword ordering / emphasis.
    """
    base_list = _normalize_base_keywords(rec.get("keywords", []))

    if not base_list:
        return ""

    if filename is not None:
        _group, variant = split_filename_group_and_variant(filename)
        if variant > 1 and len(base_list) > 1:
            shift = (variant - 1) % len(base_list)
            base_list = base_list[shift:] + base_list[:shift]

    return ", ".join(base_list)


def trim_description(text: str, max_chars: int = 200) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    trimmed = text[: max_chars - 1].rstrip()
    return trimmed + "…"


def clean_prompt_for_freepik(prompt: str) -> str:
    """
    Remove '/imagine prompt:' and MJ technical flags/id from the prompt.
    """
    if not prompt:
        return ""
    txt = prompt.strip()

    # Drop leading /imagine prompt variants
    for p in [
        "/imagine prompt:",
        "/imagine prompt",
        "imagine prompt:",
        "imagine prompt",
    ]:
        if txt.lower().startswith(p):
            txt = txt[len(p) :].strip()
            break

    # Remove our ID tags like [av:abcd1234]
    txt = re.sub(r"\[av:[^\]]+\]", "", txt).strip()

    # Remove everything from the first MJ flag onwards (e.g. --v 7 --ar 16:9 ...)
    txt = re.sub(r"\s--v\s+\d+.*$", "", txt).strip()

    return txt


# ---------------------------------------------------------------------------
# Per-image diversification: theme-type helpers
# ---------------------------------------------------------------------------


ANIMAL_WORDS = [
    "cat",
    "dog",
    "fox",
    "deer",
    "antelope",
    "lion",
    "tiger",
    "bear",
    "wolf",
    "horse",
    "zebra",
    "giraffe",
    "elephant",
    "leopard",
    "cheetah",
    "monkey",
    "gorilla",
    "panda",
    "kangaroo",
    "whale",
    "dolphin",
    "shark",
    "eagle",
    "owl",
    "penguin",
    "bird",
    "wildlife",
]

BUILDING_WORDS = [
    "building",
    "tower",
    "skyscraper",
    "architecture",
    "city",
    "cityscape",
    "urban",
]
TECH_WORDS = ["tech", "technology", "circuit", "chip", "data", "server", "digital"]
GRAPHIC_WORDS = [
    "background",
    "pattern",
    "texture",
    "graphic",
    "abstract",
    "copy space",
]
LANDSCAPE_WORDS = [
    "landscape",
    "mountain",
    "hill",
    "hillside",
    "valley",
    "river",
    "forest",
    "meadow",
]

USE_CASE_PHRASES = [
    "creative layout",
    "modern design",
    "branding projects",
    "poster design",
    "web banner",
    "print template",
    "editorial layout",
    "marketing materials",
]


def infer_theme_type(rec: dict, category: str) -> str:
    """
    Guess a coarse theme type based on meta + directory category.
    Used to pick different title/description templates.
    """
    text_bits = [
        str(rec.get("title", "")),
        str(rec.get("theme", "")),
        str(rec.get("description", "")),
        " ".join(_normalize_base_keywords(rec.get("keywords", []))),
        category,
    ]
    text = " ".join(text_bits).lower()

    def has_any(words):
        return any(w in text for w in words)

    is_winter = "winter" in text or "snow" in text or "snowfall" in text
    is_night = "night" in text or "moonlit" in text or "dark sky" in text

    if has_any(ANIMAL_WORDS):
        return "animals"
    if has_any(BUILDING_WORDS):
        return "architecture"
    if has_any(TECH_WORDS):
        return "technology"
    if has_any(GRAPHIC_WORDS):
        return "graphic"
    if has_any(LANDSCAPE_WORDS) or "landscape" in category:
        if is_winter and is_night:
            return "winter_night_landscape"
        if is_winter:
            return "winter_landscape"
        return "landscape"

    # fallback by category name
    if "animal" in category:
        return "animals"
    if "build" in category or "arch" in category:
        return "architecture"
    if "tech" in category:
        return "technology"
    if "graphic" in category or "background" in category or "texture" in category:
        return "graphic"

    return "generic"


# ---------------------------------------------------------------------------
# Per-image diversification of title / description
# ---------------------------------------------------------------------------


def diversify_title_for_filename(rec: dict, category: str, filename: str) -> str:
    """
    Per-image title with templates chosen by inferred theme type + variant index.
    No category prefix like 'Graphic Resources:'.
    """
    base_title = (
        str(rec.get("title", "")).strip()
        or str(rec.get("theme", "")).strip()
        or category
    )
    base_title = base_title.rstrip(" .")

    theme_type = infer_theme_type(rec, category)

    # Different template pools per theme type
    if theme_type == "winter_night_landscape":
        templates = [
            "{title} on a quiet winter night",
            "Minimal {title} in gentle snowfall",
            "{title} under a dark winter sky",
            "Serene {title} with falling snow",
        ]
    elif theme_type in ("landscape", "winter_landscape"):
        templates = [
            "{title} scenic landscape",
            "Minimal {title} for creative layout",
            "{title} landscape with copy space",
            "Serene {title} outdoor scene",
        ]
    elif theme_type == "animals":
        templates = [
            "{title} wildlife scene",
            "Close-up {title} in natural habitat",
            "{title} in the wild",
            "{title} for wildlife projects",
        ]
    elif theme_type == "architecture":
        templates = [
            "{title} city architecture view",
            "Modern {title} building scene",
            "{title} urban skyline composition",
            "{title} for architectural layout",
        ]
    elif theme_type == "technology":
        templates = [
            "{title} technology background",
            "Minimal {title} tech layout",
            "{title} for digital projects",
            "Clean {title} tech scene",
        ]
    elif theme_type == "graphic":
        templates = [
            "{title} graphic background",
            "Minimal {title} with copy space",
            "{title} texture for layouts",
            "Clean {title} abstract scene",
        ]
    else:  # generic
        templates = [
            "{title}",
            "{title} for creative layout",
            "Minimal {title} composition",
            "Clean {title} scene",
        ]

    _group, variant = split_filename_group_and_variant(filename)
    idx = (variant - 1) % len(templates)
    pattern = templates[idx]

    title = pattern.format(title=base_title).strip()
    title = trim_description(title, max_chars=200)
    return title


def diversify_description_for_filename(
    rec: dict, category: str, filename: str, title: str | None = None
) -> str:
    """
    Short, natural, per-image description.
    Template pool depends on inferred theme type + variant index.
    """
    base_desc = str(rec.get("description", "")).strip()
    if not base_desc:
        base_desc = (
            str(rec.get("title", "")).strip()
            or str(rec.get("theme", "")).strip()
            or category
        )

    subject = (title or base_desc or category).strip().rstrip(".")
    subject_lower = subject[0].lower() + subject[1:] if subject else "scene"

    theme_type = infer_theme_type(rec, category)
    _group, variant = split_filename_group_and_variant(filename)

    if theme_type == "winter_night_landscape":
        templates = [
            "A minimal {subject} captured on a quiet winter night with gentle snowfall.",
            "A serene {subject} under a dark sky, with clean snow and a calm winter mood.",
            "A tranquil {subject} scene showing fresh snow falling on a quiet hillside.",
            "A peaceful {subject} landscape in winter, ideal for seasonal creative projects.",
        ]
    elif theme_type in ("landscape", "winter_landscape"):
        templates = [
            "A serene {subject} landscape with natural light and clear details.",
            "A minimal {subject} outdoor scene designed with space for copy.",
            "A calm {subject} view, ideal for travel or nature-themed layouts.",
            "A clean {subject} composition with balanced scenery and open sky.",
        ]
    elif theme_type == "animals":
        templates = [
            "A detailed {subject} wildlife scene captured in natural light.",
            "A minimal {subject} composition with clear focus on the animal.",
            "A tranquil {subject} view in a natural habitat with soft background.",
            "A clean {subject} image ideal for wildlife and nature projects.",
        ]
    elif theme_type == "architecture":
        templates = [
            "A clean {subject} architecture scene with modern lines and clear sky.",
            "A detailed {subject} city view designed for urban design projects.",
            "A minimal {subject} composition showing building shapes and structure.",
            "A modern {subject} image with balanced perspective and copy space.",
        ]
    elif theme_type == "technology":
        templates = [
            "A clean {subject} technology scene with sharp details and modern feel.",
            "A minimal {subject} layout designed for digital and tech projects.",
            "A detailed {subject} background with clear lines and space for copy.",
            "A modern {subject} image ideal for data, IT, and innovation topics.",
        ]
    elif theme_type == "graphic":
        templates = [
            "A minimal {subject} background with clear structure and copy space.",
            "A clean {subject} texture designed for posters and layouts.",
            "A simple {subject} graphic with balanced composition.",
            "A modern {subject} wallpaper style image for creative projects.",
        ]
    else:  # generic
        templates = [
            "A clean {subject} captured in natural light, ideal for stock photography.",
            "A minimal {subject} composition designed for modern visual projects.",
            "A serene {subject} scene with space for copy in creative layouts.",
            "A detailed {subject} image suitable for a wide range of uses.",
        ]

    idx = (variant - 1) % len(templates)
    tpl = templates[idx]

    desc = tpl.format(subject=subject_lower)
    desc = trim_description(desc, max_chars=200)
    return desc


# ---------------------------------------------------------------------------
# Row builders for each platform
# ---------------------------------------------------------------------------


def convert_filename_extension(
    filename: str, new_ext: str = "-standard-scale-4_00x.jpeg"
) -> str:
    """
    Convert filename extension to the specified format.

    We keep the stem (which includes title + numeric suffix) and just
    replace the extension/suffix used by Topaz or MJ.
    """
    path = Path(filename)
    return path.stem + new_ext


def make_adobe_row(
    filename: str, rec: dict, category: str, cat_map: Dict[str, CategoryMap]
) -> dict:
    """
    Build one Adobe Stock CSV row with per-image diversified title/keywords.
    """
    filename_out = convert_filename_extension(filename)

    # Diversified title & keywords per image
    title = diversify_title_for_filename(rec, category, filename)
    keywords = join_keywords(rec, filename=filename)

    # Get Adobe code from mapping
    cm = cat_map.get(category) or CategoryMap(category, 0, "")
    adobe_code = cm.adobe_code

    return {
        "Filename": filename_out,
        "Title": title,
        "Keywords": keywords,
        "Category": adobe_code,
        "Releases": "",
    }


def make_shutterstock_row(
    filename: str, rec: dict, category: str, cat_map: Dict[str, CategoryMap]
) -> dict:
    """
    Build one Shutterstock CSV row with per-image diversified description/keywords.
    """
    filename_out = convert_filename_extension(filename)

    # Use diversified description and keywords
    title_for_desc = diversify_title_for_filename(rec, category, filename)
    desc = diversify_description_for_filename(rec, category, filename, title_for_desc)
    keywords = join_keywords(rec, filename=filename)

    # Map adobe category name -> shutterstock category (fallback to category)
    cm = cat_map.get(category) or CategoryMap(category, 0, category)
    shutter_cat = cm.shutterstock_cat or category

    return {
        "Filename": filename_out,
        "Description": desc,
        "Keywords": keywords,
        "Categories": shutter_cat,
        "Editorial": "no",
        "Mature content": "no",
        "illustration": "no",
    }


def make_freepik_row(filename: str, rec: dict, category: str) -> dict:
    """
    Build one Freepik CSV row with per-image diversified title/keywords.
    """
    filename_out = convert_filename_extension(filename)
    title = diversify_title_for_filename(rec, category, filename)
    keywords = join_keywords(rec, filename=filename)
    prompt = clean_prompt_for_freepik(str(rec.get("prompt", "")).strip())

    return {
        "File name": filename_out,
        "Title": title,
        "Keywords": keywords,
        "Prompt": prompt,
        "Model": "Midjourney v7",
    }


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------


def generate_stock_metadata(
    date_str: Optional[str] = None,
    download_root: Path | str = DEFAULT_DOWNLOAD_DIR,
    prompt_root: Path | str = DEFAULT_OUT_PROMPT,
    out_root: Path | str = DEFAULT_OUT_ROOT,
) -> Path:
    """
    Generate three CSV files under:

        out_root/<date_str>/
            adobe_meta.csv
            shutterstock_meta.csv
            freepik_meta.csv

    based on all images under:

        download_root/<date_str>/<category>/*

    and metadata from:

        prompt_root/<date_str>/<category>/meta.json
    """
    # Normalise roots
    if not isinstance(download_root, Path):
        download_root = PROJECT_ROOT / str(download_root)
    if not isinstance(prompt_root, Path):
        prompt_root = PROJECT_ROOT / str(prompt_root)
    if not isinstance(out_root, Path):
        out_root = PROJECT_ROOT / str(out_root)

    download_root = download_root.resolve()
    prompt_root = prompt_root.resolve()
    out_root = out_root.resolve()

    if date_str in (None, "", "latest"):
        date_str = find_latest_date_dir(download_root)

    day_dir = download_root / date_str
    if not day_dir.exists():
        raise FileNotFoundError(
            f"Download directory for {date_str} not found: {day_dir}"
        )

    logging.info("Generating stock metadata for date %s", date_str)
    logging.info("Download root: %s", day_dir)
    logging.info("Prompt root  : %s", prompt_root)

    cat_map = load_category_mapping()

    adobe_rows: List[dict] = []
    shutter_rows: List[dict] = []
    freepik_rows: List[dict] = []

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

    # Iterate categories under download_root/<date_str>/
    for cat_dir in sorted(p for p in day_dir.iterdir() if p.is_dir()):
        category = cat_dir.name

        # Load meta.json mapping for this category
        meta_map, default_rec = load_category_meta(prompt_root, date_str, category)

        # One base record per *title slug*, but we will diversify per image later
        for img_path in sorted(cat_dir.iterdir()):
            if img_path.suffix.lower() not in image_exts:
                continue

            stem = img_path.stem
            title_slug = extract_title_slug_from_filename(stem)

            rec = meta_map.get(title_slug) or default_rec or {}
            filename = img_path.name

            adobe_rows.append(make_adobe_row(filename, rec, category, cat_map))
            shutter_rows.append(make_shutterstock_row(filename, rec, category, cat_map))
            freepik_rows.append(make_freepik_row(filename, rec, category))

    if not adobe_rows:
        raise RuntimeError(f"No image files found under {day_dir}")

    out_dir = out_root / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_csv(path: Path, fieldnames: List[str], rows: List[dict]):
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        logging.info("Wrote %s (%d rows)", path, len(rows))

    # Write CSVs
    adobe_path = out_dir / "adobe_meta.csv"
    shutter_path = out_dir / "shutterstock_meta.csv"
    freepik_path = out_dir / "freepik_meta.csv"

    write_csv(
        adobe_path,
        ["Filename", "Title", "Keywords", "Category", "Releases"],
        adobe_rows,
    )
    write_csv(
        shutter_path,
        [
            "Filename",
            "Description",
            "Keywords",
            "Categories",
            "Editorial",
            "Mature content",
            "illustration",
        ],
        shutter_rows,
    )
    write_csv(
        freepik_path,
        ["File name", "Title", "Keywords", "Prompt", "Model"],
        freepik_rows,
    )

    return out_dir


# ---------------------------------------------------------------------------
# CLI entry-point (optional)
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate Adobe/Shutterstock/Freepik metadata CSVs from downloads + prompt meta."
    )
    p.add_argument(
        "-d",
        "--date",
        default="latest",
        help="Date folder (YYYY-MM-DD). If omitted or 'latest', use the latest date in mj_downloads.",
    )
    p.add_argument(
        "--download-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help="Root folder for downloaded images (default: mj_downloads).",
    )
    p.add_argument(
        "--prompt-dir",
        default=str(DEFAULT_OUT_PROMPT),
        help="Root folder for prompt metadata (default: prompt).",
    )
    p.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_ROOT),
        help="Output root folder for CSVs (default: meta).",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    out_dir = generate_stock_metadata(
        date_str=args.date,
        download_root=Path(args.download_dir),
        prompt_root=Path(args.prompt_dir),
        out_root=Path(args.out_dir),
    )
    print(f"Wrote metadata CSVs to: {out_dir}")


if __name__ == "__main__":
    main()
