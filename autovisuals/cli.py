"""
AutoVisuals CLI front-end.

Commands:
    autovisuals generate
    autovisuals discord
    autovisuals download
    autovisuals gallery
    autovisuals pipeline
    autovisuals status

All defaults (providers, paths, idle timeout, etc.) are defined HERE so
the helper modules stay simple.
"""

import os
import time
import argparse
from pathlib import Path


from .get_mj_prompt import main as generate_main
from .send_to_discord import (
    _get_project_root,
    get_latest_prompt_file,
    send_prompt_file,
    send_to_discord as send_single_prompt,
)
from .mj_download import run_downloader
from .gallery import build_gallery
from .get_meta import generate_stock_metadata


PROJECT_ROOT = _get_project_root()
DEFAULT_EXPORT_DIR = "/mnt/c/Users/xilu/Downloads/autovisuals_export"
DEFAULT_THEME_CSV = "autovisuals/data/adobe_cat.csv"
DEFAULT_OUT_PROMPT = "prompt"
DEFAULT_DOWNLOAD_DIR = "mj_downloads"
DEFAULT_GALLERY_HTML = "mj_gallery.html"
DEFAULT_IDLE_SECONDS = 180  # 3 minutes default idle timeout


# ------------------------------------------------------------------
# Helpers for prompt paths
# ------------------------------------------------------------------


def get_prompt_root() -> Path:
    return PROJECT_ROOT / DEFAULT_OUT_PROMPT


def get_latest_date() -> str:
    root = get_prompt_root()
    if not root.exists():
        raise FileNotFoundError("No prompt directory found.")
    dates = sorted(p.name for p in root.iterdir() if p.is_dir())
    if not dates:
        raise FileNotFoundError("No date folders under prompt/.")
    return dates[-1]


def get_categories_for_date(date: str) -> list[str]:
    date_dir = get_prompt_root() / date
    if not date_dir.exists():
        return []
    return sorted(p.name for p in date_dir.iterdir() if p.is_dir())


def get_prompt_file_for(date: str, category_slug: str) -> Path:
    """
    Prefer prompt.new.txt (prompts from the latest run only).
    Fall back to prompt.txt for backwards compatibility.
    """
    base_dir = get_prompt_root() / date / category_slug
    latest = base_dir / "prompt.new.txt"
    if latest.exists():
        return latest

    path = base_dir / "prompt.txt"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file for {date}/{category_slug}")
    return path


# ------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autovisuals",
        description="AutoVisuals – automatic prompt & gallery pipeline.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # generate
    gen = subparsers.add_parser("generate", help="Generate prompts + metadata.")
    gen.add_argument(
        "-p",
        "--provider",
        default="openai",
        help="chatbot provider, choose openai by default, anthropic, gemini, llama, or deepseek.",
    )
    gen.add_argument(
        "-l",
        "--list",
        default=DEFAULT_THEME_CSV,
        help="list of visuals list, choose autovisuals/data/adobe_cat.csv by default or others.",
    )
    gen.add_argument(
        "-m",
        "--mode",
        default="r",
        help="mode to generate prompts by themes, choose r(weighted random) by default or m(manual).",
    )
    gen.add_argument(
        "-t",
        "--title",
        default="r",
        help="title mode to generate titles for prompts, choose r(weighted random) by default or m(manual).",
    )
    gen.add_argument(
        "-d",
        "--records",
        type=int,
        default=5,
        help="number of prompts for each theme and title, 5 by default.",
    )
    gen.add_argument(
        "-r",
        "--repeat",
        type=int,
        default=2,
        help="number of times to repeat each prompt for diversity, 2 by default.",
    )
    gen.add_argument(
        "-o",
        "--out",
        default=DEFAULT_OUT_PROMPT,
        help="prompt output directory, prompt/<date>/<theme> by default.",
    )

    # discord
    dis = subparsers.add_parser("discord", help="Send prompts to Discord webhook.")
    dis.add_argument(
        "-w",
        "--webhook",
        help="webhook URL, need to export it as environment variable.",
    )
    dis.add_argument(
        "--category", help="specific category slug to send, true by default."
    )
    dis.add_argument(
        "--all-categories",
        action="store_true",
        help="send prompts for all categories for latest date, true by default.",
    )

    # download
    dl = subparsers.add_parser("download", help="Download Midjourney images.")
    dl.add_argument(
        "-t",
        "--token",
        help="discord bot token, need to export it as environment variable.",
    )
    dl.add_argument(
        "-c",
        "--channel-id",
        type=int,
        help="discord channel id, need to export it as environment variable.",
    )
    dl.add_argument(
        "-o",
        "--out",
        default=DEFAULT_DOWNLOAD_DIR,
        help="images download directory, mj_downloads/<date>/<theme> by default.",
    )
    dl.add_argument(
        "--limit",
        type=int,
        default=None,
        help="stop after N images, no limit by default.",
    )
    dl.add_argument(
        "--idle-seconds",
        type=int,
        default=DEFAULT_IDLE_SECONDS,
        help=f"downloader idle timeout in seconds to proccess gallery, {DEFAULT_IDLE_SECONDS} by default.",
    )

    # gallery
    gal = subparsers.add_parser("gallery", help="Build HTML gallery.")
    gal.add_argument(
        "--download-dir",
        default=DEFAULT_DOWNLOAD_DIR,
        help="images download directory, mj_downloads/<date>/<theme> by default.",
    )
    gal.add_argument(
        "--prompt-dir",
        default=DEFAULT_OUT_PROMPT,
        help="prompt output directory, prompt/<date>/<theme> by default.",
    )
    gal.add_argument(
        "--out",
        default=DEFAULT_GALLERY_HTML,
        help="gallery file output directory, mj_gallery.html by default.",
    )

    # pipeline
    pipe = subparsers.add_parser(
        "pipeline",
        help="Full pipeline: generate → send → download → gallery.",
    )

    # generation
    pipe.add_argument(
        "-p",
        "--provider",
        default="openai",
        help="chatbot provider, choose openai by default, anthropic, gemini, llama, or deepseek.",
    )
    pipe.add_argument(
        "-l",
        "--list",
        default=DEFAULT_THEME_CSV,
        help="list of visuals list, choose autovisuals/data/adobe_cat.csv by default or others.",
    )
    pipe.add_argument(
        "-m",
        "--mode",
        default="r",
        help="mode to generate prompts by themes, choose r(weighted random) by default or m(manual).",
    )
    pipe.add_argument(
        "-t",
        "--title",
        default="r",
        help="title mode to generate titles for prompts, choose r(weighted random) by default or m(manual).",
    )
    pipe.add_argument(
        "-d",
        "--records",
        type=int,
        default=10,
        help="number of prompts for each theme and title, 5 by default.",
    )
    pipe.add_argument(
        "-r",
        "--repeat",
        type=int,
        default=2,
        help="number of times to repeat each prompt for diversity, 2 by default.",
    )
    pipe.add_argument(
        "-o",
        "--out",
        default=DEFAULT_OUT_PROMPT,
        help="prompt output directory, prompt/<date>/<theme> by default.",
    )

    # discord
    pipe.add_argument(
        "-w",
        "--webhook",
        help="webhook URL, need to export it as environment variable.",
    )

    # download + gallery
    pipe.add_argument(
        "--download-dir",
        default=DEFAULT_DOWNLOAD_DIR,
        help="images download directory, mj_downloads/<date>/<theme> by default.",
    )
    pipe.add_argument(
        "--gallery-out",
        default=DEFAULT_GALLERY_HTML,
        help="gallery file output directory, mj_gallery.html by default.",
    )
    pipe.add_argument(
        "--idle-seconds",
        type=int,
        default=DEFAULT_IDLE_SECONDS,
        help=f"downloader idle timeout in seconds to proccess gallery, {DEFAULT_IDLE_SECONDS} by default.",
    )
    pipe.add_argument(
        "-U",
        "--upscale",
        choices=["n", "y"],
        default="n",
        help="optional upscaling step after download (y = RealESRGAN, default: n).",
    )
    pipe.add_argument(
        "--export-dir",
        default=DEFAULT_EXPORT_DIR,
        help="export root for upscaled images (absolute path, "
        "e.g. /mnt/c/Users/xilu/Downloads/autovisuals_export).",
    )

    # status
    status = subparsers.add_parser(
        "status",
        help="show a tidy summary of prompts + images per date/category.",
    )
    status.add_argument(
        "--prompt-dir",
        default=DEFAULT_OUT_PROMPT,
        help="root folder for prompt data (default: prompt).",
    )
    status.add_argument(
        "--download-dir",
        default=DEFAULT_DOWNLOAD_DIR,
        help="root folder for downloaded images (default: mj_downloads).",
    )
    status.add_argument(
        "--date",
        help="only show this YYYY-MM-DD date (default: all dates found under prompt/).",
    )

    # meta
    meta = subparsers.add_parser(
        "meta",
        help="Generate Adobe/Shutterstock/Freepik metadata CSVs from downloads + prompt meta.",
    )
    meta.add_argument(
        "-d",
        "--date",
        default="latest",
        help="Date folder (YYYY-MM-DD). If omitted or 'latest', use the latest date in mj_downloads.",
    )
    meta.add_argument(
        "--download-dir",
        default=DEFAULT_DOWNLOAD_DIR,  # whatever constant you already use
        help="root folder for downloaded images (default: mj_downloads).",
    )
    meta.add_argument(
        "--prompt-dir",
        default=DEFAULT_OUT_PROMPT,
        help="root folder for prompt data (default: prompt).",
    )
    meta.add_argument(
        "-o",
        "--out-dir",
        default="meta",
        help="output root folder for stock CSVs (relative to project root).",
    )

    return parser


# ------------------------------------------------------------------
# Status helper
# ------------------------------------------------------------------


def run_status(prompt_dir: str, download_dir: str, only_date: str | None):
    prompt_root = PROJECT_ROOT / prompt_dir
    download_root = PROJECT_ROOT / download_dir

    if not prompt_root.exists():
        print(f"prompt root not found: {prompt_root}")
        return

    dates = sorted(p.name for p in prompt_root.iterdir() if p.is_dir())
    if not dates:
        print(f"no date folders under {prompt_root}")
        return

    if only_date:
        if only_date not in dates:
            print(f"date {only_date!r} not found under {prompt_root}")
            return
        dates = [only_date]

    print(f"Project root  : {PROJECT_ROOT}")
    print(f"Prompt root   : {prompt_root}")
    print(f"Download root : {download_root}")
    print()

    header = f"{'DATE':<12} {'CATEGORY':<20} {'PROMPTS':>8} {'IMAGES':>8}"
    print(header)
    print("-" * len(header))

    total_prompts = 0
    total_images = 0

    img_exts = {".png", ".jpg", ".jpeg", ".webp"}

    for date in dates:
        date_dir = prompt_root / date
        cats = sorted(p.name for p in date_dir.iterdir() if p.is_dir())
        if not cats:
            continue

        for cat in cats:
            cat_dir = date_dir / cat
            prompt_file = cat_dir / "prompt.txt"

            # count prompts by non-empty lines
            prompts_count = 0
            if prompt_file.exists():
                for line in prompt_file.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        prompts_count += 1

            # count image files in download tree
            images_count = 0
            img_dir = download_root / date / cat
            if img_dir.exists():
                for f in img_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in img_exts:
                        images_count += 1

            total_prompts += prompts_count
            total_images += images_count

            print(f"{date:<12} {cat:<20.20} {prompts_count:>8} {images_count:>8}")

    print("-" * len(header))
    print(f"{'TOTAL':<12} {'':<20} {total_prompts:>8} {total_images:>8}")


# ------------------------------------------------------------------
# Main dispatch
# ------------------------------------------------------------------


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        generate_main(
            provider=args.provider,
            list_arg=args.list,
            mode=args.mode,
            title_mode=args.title,
            n=args.records,
            repeat=args.repeat,
            out_arg=args.out,
        )

    elif args.command == "discord":
        webhook = args.webhook or os.environ.get("WEBHOOK_URL")
        if not webhook:
            raise ValueError("Provide --webhook or set WEBHOOK_URL env variable.")

        latest_date = get_latest_date()
        cats = get_categories_for_date(latest_date)

        print(f"Latest date: {latest_date}")
        print(f"Available categories: {cats}")

        if args.all_categories:
            print("Sending ALL categories...")
            for cat in cats:
                pf = get_prompt_file_for(latest_date, cat)
                print(f"→ {cat}")
                send_prompt_file(pf, webhook)
            return

        if args.category:
            if args.category not in cats:
                raise ValueError(f"Category {args.category!r} not found.")
            pf = get_prompt_file_for(latest_date, args.category)
            print(f"→ {args.category}")
            send_prompt_file(pf, webhook)
            return

        print("No category specified, sending latest category (fallback).")
        pf = get_latest_prompt_file()
        send_prompt_file(pf, webhook)

    elif args.command == "download":
        idle = (
            args.idle_seconds if args.idle_seconds and args.idle_seconds > 0 else None
        )
        run_downloader(
            token=args.token,
            channel_id=args.channel_id,
            download_dir=args.out,
            limit=args.limit,
            idle_seconds=idle,
        )

    elif args.command == "gallery":
        out = build_gallery(
            download_root=args.download_dir,
            prompt_root=args.prompt_dir,
            out_file=args.out,
        )
        print(f"Gallery written to: {out}")

    elif args.command == "pipeline":
        # record start time so we can detect "new" prompts + downloads
        pipeline_start = time.time()

        # 1. generate
        print("Step 1/4: Generating prompts + metadata...")
        generate_main(
            provider=args.provider,
            list_arg=args.list,
            mode=args.mode,
            title_mode=args.title,
            n=args.records,
            repeat=args.repeat,
            out_arg=args.out,
        )

        # 2. send to discord – ONLY most recent new prompts (by mtime)
        print("\nStep 2/4: Sending prompts to Discord...")
        webhook = args.webhook or os.environ.get("WEBHOOK_URL")
        if not webhook:
            raise ValueError("Provide --webhook or set WEBHOOK_URL for pipeline.")

        latest_date = get_latest_date()
        cats = get_categories_for_date(latest_date)
        if not cats:
            raise RuntimeError(f"No categories found under prompt/{latest_date}/")

        print(f"Using date        : {latest_date}")
        print(f"All categories    : {cats}")

        # find categories whose prompt.txt was modified in THIS run
        prompt_root = get_prompt_root() / latest_date
        new_cats: list[str] = []
        for cat in cats:
            pf = prompt_root / cat / "prompt.txt"
            if pf.exists():
                mtime = pf.stat().st_mtime
                if mtime >= pipeline_start:
                    new_cats.append(cat)

        if not new_cats:
            # fallback: treat the latest category as "most recent"
            new_cats = [cats[-1]]

        print(f"New categories to send (most recent): {new_cats}")

        total_prompts = 0
        for cat in new_cats:
            pf = get_prompt_file_for(latest_date, cat)
            print(f"→ sending {cat}")
            for line in pf.read_text(encoding="utf-8").splitlines():
                msg = line.strip()
                if not msg:
                    continue
                send_single_prompt(msg, webhook)
                total_prompts += 1

        print(f"Total prompts sent: {total_prompts}")
        if total_prompts == 0:
            print("No prompts, aborting pipeline after step 2.")
            return

        # 3. download – MJ → mj_downloads
        print("\nStep 3/4: Downloading images from Discord...")
        print(
            f"Downloader will auto-stop after {args.idle_seconds}s of inactivity "
            "(controlled by --idle-seconds)."
        )
        idle = (
            args.idle_seconds if args.idle_seconds and args.idle_seconds > 0 else None
        )
        run_downloader(
            token=None,  # DISCORD_BOT_TOKEN env
            channel_id=None,  # MJ_CHANNEL_ID env
            download_dir=args.download_dir,
            limit=None,
            idle_seconds=idle,
        )

        # 3b. OPTIONAL upscaling – ONLY most recent generated downloads
        final_download_root = args.download_dir  # default: original downloads

        # if you already added --upscale / --export-dir, keep this guard;
        # otherwise you can remove the 'getattr' and condition.
        if getattr(args, "upscale", "n") == "y":
            print("\nStep 3b: Upscaling images with RealESRGAN (most recent only)...")

            from .upscale import run_realesrgan

            raw_root = Path(args.download_dir)
            if not raw_root.is_absolute():
                raw_root = PROJECT_ROOT / raw_root

            export_root = Path(
                getattr(
                    args, "export_dir", "/mnt/c/Users/xilu/Downloads/autovisuals_export"
                )
            )
            export_root.mkdir(parents=True, exist_ok=True)

            img_exts = {".png", ".jpg", ".jpeg", ".webp"}

            date_export_dir = export_root / latest_date
            date_export_dir.mkdir(parents=True, exist_ok=True)

            new_images: list[Path] = []

            # only scan categories whose prompts we just sent
            for cat in new_cats:
                src_cat_dir = raw_root / latest_date / cat
                if not src_cat_dir.exists():
                    continue

                for p in src_cat_dir.iterdir():
                    if not (p.is_file() and p.suffix.lower() in img_exts):
                        continue
                    if p.stat().st_mtime >= pipeline_start:
                        new_images.append((cat, p))

            if not new_images:
                print("[upscale] no new images found for this run; skipping upscaling.")
            else:
                # group by category, so export structure stays date/category/...
                by_cat: dict[str, list[Path]] = {}
                for cat, img in new_images:
                    by_cat.setdefault(cat, []).append(img)

                for cat, imgs in by_cat.items():
                    out_cat_dir = date_export_dir / cat
                    out_cat_dir.mkdir(parents=True, exist_ok=True)
                    print(f"[upscale] category {cat}: {len(imgs)} new image(s)")
                    run_realesrgan(
                        input_images=imgs,
                        output_dir=out_cat_dir,
                    )

                # gallery should use the export folder when upscaling is enabled
                final_download_root = export_root

        # 4. gallery
        print("\nStep 4/4: Building gallery...")
        gallery_path = build_gallery(
            download_root=final_download_root,
            prompt_root=args.out,
            out_file=args.gallery_out,
        )
        print(f"Pipeline complete. Gallery written to: {gallery_path}")

    elif args.command == "status":
        run_status(
            prompt_dir=args.prompt_dir,
            download_dir=args.download_dir,
            only_date=args.date,
        )

    elif args.command == "meta":
        generate_stock_metadata(
            date_str=args.date,
            download_root=args.download_dir,
            prompt_root=args.prompt_dir,
            out_root=args.out_dir,
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
