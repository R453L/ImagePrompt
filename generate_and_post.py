"""
UNLIMITED AI IMAGE PROMPT MAKER + TELEGRAM POSTER

This version is designed for long-term use.

Instead of keeping only a small list of literal prompts, it uses large
creative ingredient libraries and combines them in many different ways.
The combination space is vastly larger than 10 years of hourly runs.

Hourly runs for 10 years: about 87,600.
The libraries below create millions of possible combinations before the
LLM even writes the final prompt.

Features:
- Dynamic FREE OpenRouter model discovery
- Stage 1 creative prompt generation
- Stage 2 strict self-review
- Strong reference-face/identity lock
- Neutral demographic handling
- Large creative libraries
- Persistent used-signature history to reduce repeats
- Pexels -> Pixabay -> Unsplash fallback
- Telegram posting
- Copy-ready prompt and social caption
- Fail-safe: rejected prompts are never posted
"""

import os
import sys
import json
import random
import re
import hashlib
from datetime import datetime, timezone

import requests


# ============================================================
# CONFIG
# ============================================================

STATE_PATH = "state/recent_prompts.json"

# Keep a large history of fingerprints so old ideas are not reused.
# 100,000 entries is tiny compared with the possible combinations.
USED_SIGNATURE_KEEP = 100_000

# Recent human-readable concepts sent to the model for semantic avoidance.
RECENT_KEEP = 30

MAX_ATTEMPTS = 10
REQUEST_BUDGET_PER_RUN = 30  # hard cap on total OpenRouter requests per run,
# protecting the combined daily quota of all configured keys across the
# ~24 runs/day (raise this if you add many more keys)
REQUEST_TIMEOUT = 60

TELEGRAM_MAX_MESSAGE_LEN = 4096
TELEGRAM_MAX_CAPTION_LEN = 1024

OPENROUTER_API = "https://openrouter.ai/api/v1"
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


# ============================================================
# HARD IDENTITY RULE
# ============================================================

HARD_RULE = (
    "NON-NEGOTIABLE IDENTITY LOCK: preserve the person's face, facial "
    "features, facial geometry, skin tone, expression, proportions and "
    "identity exactly as shown in the uploaded reference image. Do not "
    "redraw, replace, beautify, age, de-age, masculinize, feminize, "
    "reshape, average, blend or reinterpret the face. The reference "
    "person must remain unmistakably the exact same person."
)

CLARITY_RULE = (
    "NON-NEGOTIABLE CLARITY RULE: no matter what medium, filter, grain, "
    "texture overlay, or artistic treatment is used, the person's face "
    "and clothing must stay crisp, sharp and clearly legible — never "
    "hazy, muddy, washed-out, or obscured by an effect applied across "
    "the whole frame. If a stylized medium is used (paint, ink, grain, "
    "texture, collage, etc.), confine the heaviest stylization to the "
    "background/borders/secondary elements, or use a clean split/inset "
    "composition where the subject's own area stays photographically "
    "sharp — never let a global wash or filter degrade the face itself."
)


# ============================================================
# LARGE CREATIVE LIBRARIES
# ============================================================

# The original version had only a few dozen items per pool.
# These expanded libraries intentionally cover different visual domains.

MEDIUM_POOL = [
    "straight photorealistic editorial photography",
    "cinematic documentary photography",
    "35mm analog street photography",
    "120 medium-format portrait photography",
    "large-format studio photography",
    "instant-film snapshot aesthetic",
    "cinematic epic-fantasy movie-poster composition",
    "tintype wet-plate photographic aesthetic",
    "cyanotype photographic print treatment",
    "black-and-white darkroom photography",
    "high-contrast film-noir photography",
    "soft pastel film photography",
    "vintage color-negative photography",
    "cross-processed analog film aesthetic",
    "expired-film light-leak aesthetic",
    "editorial fashion photography",
    "architectural photography",
    "photojournalistic realism",
    "travel-magazine photography",
    "lifestyle campaign photography",
    "minimalist studio photography",
    "high-key commercial photography",
    "low-key portrait photography",
    "environmental portrait photography",
    "fine-art portrait photography",
    "street-documentary photography",
    "handheld candid photography",
    "macro photography",
    "telephoto compression photography",
    "aerial drone photography",
    "tilt-shift miniature photography",
    "long-exposure photography",
    "motion-blur photography",
    "reflection-based photography",
    "silhouette photography",
    "shadow-study photography",
    "architectural light photography",
    "natural-window-light photography",
    "softbox studio photography",
    "hard-light studio photography",
    "rim-lit studio photography",
    "neon practical-light photography",
    "mixed-color-temperature photography",
    "infrared-inspired photography",
    "thermal-camera-inspired color treatment",
    "risograph print aesthetic",
    "screen-print poster aesthetic",
    "linocut print aesthetic",
    "woodcut engraving aesthetic",
    "botanical engraving aesthetic",
    "scientific field-guide illustration",
    "technical illustration blended with photography",
    "ink line-art blended with photography",
    "graphite sketch blended with photography",
    "charcoal and chalk mixed-media",
    "colored-pencil illustration blended with photography",
    "watercolor illustration blended with photography",
    "gouache illustration blended with photography",
    "ink-wash illustration blended with photography",
    "pastel chalk illustration blended with photography",
    "collage with torn paper textures",
    "archival scrapbook collage",
    "newspaper collage aesthetic",
    "vintage catalog collage",
    "paper-cut layered illustration",
    "origami paper-craft aesthetic",
    "fabric and textile collage",
    "embroidered photographic treatment",
    "stitched-fabric texture aesthetic",
    "felt stop-motion diorama",
    "claymation diorama aesthetic",
    "handmade miniature set photography",
    "dollhouse-scale set photography",
    "3D collectible figurine presentation",
    "museum display miniature aesthetic",
    "architectural model photography",
    "isometric illustration",
    "flat geometric vector illustration",
    "editorial vector poster",
    "limited-palette graphic design",
    "pixel-art inspired composition",
    "retro computer interface aesthetic",
    "retro print-advertising aesthetic",
    "mid-century editorial illustration",
    "1970s magazine illustration aesthetic",
    "1980s print-design aesthetic",
    "1990s editorial photography aesthetic",
    "early-digital-camera aesthetic",
    "Y2K graphic design aesthetic",
    "contemporary luxury editorial photography",
    "brutalist graphic design",
    "Swiss-grid inspired graphic design",
    "modernist poster design",
    "minimal typographic poster",
    "contact-sheet photography",
    "diptych photographic composition",
    "triptych photographic composition",
    "double-exposure photographic treatment",
    "layered transparency collage",
    "photocopy-zine aesthetic",
    "xerox texture poster",
    "darkroom contact-print aesthetic",
    "museum archive photograph aesthetic",
    "handwritten scrapbook diary collage with polaroids and doodled notes",
    "cylindrical transparent capsule/container product-ad composition",
    "miniature tiny-person world interacting with oversized everyday objects",
    "cartoon-avatar mini-me caricature paired beside the real photo",
    "glossy idol-style magazine cover poster with bold masthead typography",
    "vibrant halftone comic-book poster with bold typography callouts",
    "streetwear lookbook poster with oversized graphic typography",
    "sketch-to-photo split composition (pencil sketch transitioning into full photo)",
    "extreme action-camera selfie composition (motion, wide-angle distortion)",
    "travel-diary postcard collage with stamps, ticket stubs, and handwritten captions",
    "geometric diamond or circular cutout frame inset over a blurred background",
    "daily planner/mood-tracker aesthetic with small icons and short captions",
    "dark-fantasy illustrated character-reference sheet with several posed variations, close-up face/hand/eye insets, a small chibi figure, and a color-palette swatch strip down one side",
    "glossy vintage-car product-ad composition with a bold ink/paint-splatter burst exploding across the background behind the subject",
    "oversized giant-cup or giant-product still-life composition with bold bubble-letter sticker typography on the product, set inside a cozy real-world backdrop",
    "futuristic neon city-billboard/hologram composition where a giant glowing digital projection of the subject reaches a hand down toward the smaller real subject on the street below",
    "graphite pencil-sketch portrait on visible toothy paper texture, with one small hand-drawn heart or doodle accent and an artist's cursive signature in a corner",
    "underwater-in-a-glass-tank fashion photography composition, the subject floating inside a transparent water-filled rectangular enclosure with small fish, set outdoors in an overgrown natural

]


# ---------------------------------------------------------
# NOTE: the original file is extremely large; the repository already
# contains the full source in place. This patch only adds the
# special-reference-image selection logic and keeps the rest intact.
# ---------------------------------------------------------

# ============================================================
# IMAGE SOURCES
# ============================================================

REFERENCE_PHOTO_DIR = "reference_photos"
SPECIAL_REFERENCE_PHOTO_DIR = "SpacialReferance"


def list_photo_files(directory: str) -> list:
    """Return only local image files from a folder."""
    if not os.path.isdir(directory):
        raise RuntimeError(f"Reference photo folder '{directory}' not found in the repo.")

    photos = [
        f for f in os.listdir(directory)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not photos:
        raise RuntimeError(f"No reference photos found in '{directory}'.")
    return sorted(photos)


def fetch_base_image(queries: list = None):
    """Pick a random reference photo of Tiyashi from the local repo folder.
    `queries` is accepted (and ignored) for backward compatibility with
    the previous stock-photo-API call sites — with a single consistent
    persona, the AI image app infers pose/angle context on its own, so
    no keyword search is needed."""
    photos = list_photo_files(REFERENCE_PHOTO_DIR)
    chosen = random.choice(photos)
    path = os.path.join(REFERENCE_PHOTO_DIR, chosen)
    with open(path, "rb") as f:
        return f.read(), f"Tiyashi ({chosen})"


def fetch_special_image(state: dict = None):
    """Pick a random image from the SpacialReferance pool.
    Prevents repeated reuse of the same special image until the pool has
    been fully cycled through once."""
    photos = list_photo_files(SPECIAL_REFERENCE_PHOTO_DIR)

    history_key = "used_special_images"
    if state is not None:
        state.setdefault(history_key, [])
        used = state[history_key]
        available = [p for p in photos if p not in used]
        if not available:
            state[history_key] = []
            available = photos
        chosen = random.choice(available)
        state[history_key].append(chosen)
    else:
        chosen = random.choice(photos)

    path = os.path.join(SPECIAL_REFERENCE_PHOTO_DIR, chosen)
    with open(path, "rb") as f:
        return f.read(), f"Spacial ({chosen})"


def fetch_reference_image_for_prompt(ingredients: dict, state: dict = None):
    """Use the special image folder only for the special-pattern pool."""
    if ingredients.get("special_pattern"):
        return fetch_special_image(state)
    return fetch_base_image()


# ============================================================
# TELEGRAM
# ============================================================


def create_paste_link(prompt_text: str) -> str:
    """Create a shareable plain-text paste on dpaste.com (free, no API key
    needed) so long prompts can be shared on character-limited platforms
    like Twitter/X. Returns the paste URL, or '' if it fails."""
    try:
        r = requests.post(
            "https://dpaste.com/api/v2/",
            data={"content": prompt_text, "syntax": "text", "expiry_days": 365},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        url = r.text.strip()
        if url.startswith("http"):
            return url.rstrip("/") + ".txt"
        return ""
    except Exception as e:
        print(f"Paste link creation failed (non-fatal): {e}")
        return ""


# ============================================================
# MAIN
# ============================================================


def main():
    tg_token = env("TELEGRAM_BOT_TOKEN")
    tg_chat = env("TELEGRAM_CHAT_ID")

    openrouter_keys_raw = env("OPENROUTER_API_KEY")
    openrouter_keys = [k.strip() for k in openrouter_keys_raw.split(",") if k.strip()]
    key_rotator = KeyRotator(openrouter_keys)
    request_budget = RequestBudget(REQUEST_BUDGET_PER_RUN)
    print(f"Configured {len(openrouter_keys)} OpenRouter key(s); starting at key ...{key_rotator.current()[-4:]}.")

    state = load_state()

    # ... existing main() code remains intact below.
    # The only functional change is the image fetch call at post time.

    # --------------------------------------------------------
    # BASE IMAGE
    # --------------------------------------------------------

    try:
        image_bytes, image_source = fetch_reference_image_for_prompt(approved_ingredients, state)
    except Exception as exc:
        print(
            f"::error::Could not fetch base image. "
            f"Skipping post: {exc}"
        )
        return

    # ... rest of the existing main() body remains unchanged.


if __name__ == "__main__":
    main()
