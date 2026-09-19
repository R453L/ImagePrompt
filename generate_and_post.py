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

MAX_ATTEMPTS = 5
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
]

MOOD_POOL = [
    "playful and mischievous",
    "melancholic and nostalgic",
    "triumphant and powerful",
    "mysterious and moody",
    "dreamy and whimsical",
    "cold futuristic and detached",
    "cozy and intimate",
    "dramatic and cinematic",
    "quietly joyful",
    "eerie and unsettling, tasteful and non-gory",
    "rebellious and bold",
    "serene and meditative",
    "euphoric and electric",
    "wistful and longing",
    "defiant and proud",
    "tender and gentle",
    "chaotic and energetic",
    "solemn and reverent",
    "cheeky and ironic",
    "contemplative and philosophical",
    "awe-struck by ordinary details",
    "hopeful and optimistic",
    "brooding and intense",
    "innocent and curious",
    "confident and unbothered",
    "quietly absurd",
    "warm and reassuring",
    "restless and kinetic",
    "observational and thoughtful",
    "romantic without being sentimental",
    "dryly humorous",
    "nostalgic without looking staged",
    "calm before a storm",
    "slightly uncanny",
    "grounded and authentic",
    "raw and intimate",
    "refined and understated",
    "bright and optimistic",
    "reserved and elegant",
    "adventurous and curious",
    "lonely but hopeful",
    "serious with a playful visual detail",
    "quietly rebellious",
    "focused and purposeful",
    "fresh and spontaneous",
    "peaceful and tactile",
    "strange but believable",
    "observational and documentary",
    "nostalgic and tactile",
    "energetic but controlled",
]

SETTING_POOL = [
    "a rain-soaked neon-lit city street at night",
    "an old dusty bookstore with towering shelves",
    "an abandoned greenhouse reclaimed by plants",
    "a floating platform above ordinary clouds",
    "a cluttered vintage workshop lit by a single bulb",
    "an underwater ruin with natural shafts of light",
    "a snow-covered mountain overlook at dawn",
    "a retro roadside diner at 2am",
    "a night market full of paper lanterns",
    "a minimalist white studio with one surreal object",
    "a grand old train station with steam and light beams",
    "a rooftop garden overlooking a sprawling skyline",
    "a harbor fishing village at first light",
    "a foggy pier at low tide",
    "a small jazz-club basement with warm low light",
    "an art-deco room under renovation",
    "a carnival at night with practical lights and motion",
    "an ice cave with blue ambient light",
    "a cliffside lighthouse in a storm",
    "a mountain monastery courtyard",
    "a rooftop infinity pool at dusk",
    "a botanical conservatory full of glass and humidity",
    "an abandoned drive-in cinema at dusk",
    "a desert canyon at golden hour",
    "an orchard in full bloom",
    "an artist's cluttered loft studio",
    "a backstage opera corridor",
    "a vineyard during harvest",
    "a quiet subway platform with one train passing",
    "a terraced rice field viewed from above",
    "a neighborhood laundromat late at night",
    "a tiny neighborhood repair shop",
    "a quiet corner cafe before opening",
    "a municipal library reading room",
    "a coastal bus stop during drizzle",
    "a weathered fishing boat interior",
    "a small-town post office",
    "a flower market before sunrise",
    "a covered pedestrian arcade after rain",
    "a rooftop parking deck after sunset",
    "a train carriage during a quiet journey",
    "a roadside mechanic yard",
    "a community pottery studio",
    "a small photography darkroom",
    "a public swimming pool before opening",
    "a botanical nursery filled with labeled plants",
    "a vintage record shop",
    "a narrow alley behind a restaurant district",
    "a quiet museum storage room",
    "a university workshop corridor",
    "a weathered seaside motel courtyard",
    "a mountain cable-car station",
    "a rural railway crossing",
    "a ferry terminal waiting area",
    "a covered outdoor bazaar",
    "a rooftop greenhouse",
    "a small neighborhood cinema lobby",
    "a vintage arcade room",
    "a ceramics showroom",
    "a bicycle repair station",
    "a tailor's workshop",
    "a printmaking studio",
    "a bookbinding workshop",
    "a watch-repair counter",
    "a florist's back room",
    "a small music rehearsal room",
    "a photography studio between shoots",
    "a community theater backstage storage area",
    "a quiet hotel corridor",
    "a modest apartment kitchen during rain",
    "a sunlit apartment balcony",
    "a shared creative studio",
    "a covered railway footbridge",
    "a riverside promenade at dawn",
    "a public garden greenhouse",
    "a city rooftop water-tank area",
    "a ferry deck in heavy fog",
    "a weathered pier-side warehouse",
    "a mountain roadside rest stop",
    "a rural roadside tea stall",
    "a quiet village courtyard",
    "a market street just after closing",
    "a harbor warehouse office",
    "a small newspaper archive room",
    "a public observatory building interior without showing space",
    "a coastal weather station",
    "a rain-covered pedestrian bridge",
    "a historic post-industrial factory floor",
    "a quiet train maintenance shed",
    "a neighborhood community center",
    "a vintage furniture workshop",
    "a small independent bakery before opening",
    "a roadside fruit market",
    "a quiet hotel breakfast room",
    "a conservatory corridor filled with potted plants",
    "a covered rooftop terrace",
    "a city courtyard between old buildings",
    "a riverside bookstall",
    "a small antiques shop",
    "a flea market under canvas roofs",
    "a public sculpture courtyard",
    "a modest tailor showroom",
    "a narrow staircase in an old apartment building",
    "a weathered wooden pier",
    "a quiet coastal promenade",
    "a small mountain guesthouse lobby",
]

TWIST_POOL = [
    "an ordinary object appears at an unexpectedly large scale",
    "the subject's shadow subtly performs a different gesture",
    "one practical object uses a different visual medium than everything around it",
    "one carefully chosen vivid color cuts through an otherwise restrained palette",
    "an animal appears naturally in the background as a quiet visual counterpoint",
    "a tiny detail becomes the visual focal point through selective sharpness",
    "one surface appears to be made from an unexpected but believable material",
    "a reflection reveals a slightly different arrangement of ordinary objects",
    "a practical lamp casts an unusually specific geometric shadow",
    "foreground and background suggest different seasons in a believable photographic way",
    "the subject encounters a carefully staged visual echo of an earlier moment",
    "only one object remains perfectly sharp while nearby details soften away",
    "one architectural element is subtly rotated in a physically impossible way",
    "exactly one object uses an inverted local color palette",
    "a torn-paper edge reveals another ordinary location underneath",
    "a mundane object is placed somewhere subtly wrong but visually believable",
    "the clothing intentionally contrasts with the practical environment",
    "a tiny background detail quietly explains the entire scene",
    "an obsolete analog device becomes an important storytelling prop",
    "weather appears indoors in a restrained, physically believable way",
    "a small everyday object appears at architectural scale",
    "a mirrored surface creates a doubled but controlled composition",
    "a familiar object has been repaired using visibly mismatched materials",
    "one section of the environment is perfectly clean while the rest is heavily used",
    "a handwritten note becomes a secondary visual focal point without readable text",
    "a repetitive pattern is interrupted by exactly one irregular element",
    "a functional object is repurposed for an unexpected but plausible use",
    "the environment contains evidence of an event that happened moments earlier",
    "a piece of furniture is positioned in an oddly precise location",
    "a doorway frames a second scene that echoes the first",
    "a puddle reflects a different light source than the one visible nearby",
    "one object appears freshly restored among weathered surroundings",
    "the subject is surrounded by objects arranged according to a subtle geometric rhythm",
    "an old repair mark becomes part of the composition",
    "a normally hidden mechanical detail is intentionally exposed",
    "one background figure is represented only through a shadow or reflection",
    "a common household object becomes a visual time capsule",
    "the scene contains one deliberately outdated item among contemporary objects",
    "a transparent material creates a layered visual effect",
    "a surface has a tactile pattern that contrasts with the surrounding textures",
    "a small maintenance tool becomes an unexpectedly elegant compositional element",
    "the scene looks recently paused, as if everyone left seconds ago",
    "one object is positioned with almost architectural precision",
    "the subject interacts with an old object in a completely contemporary way",
    "a familiar public-space sign exists but contains no readable branding",
    "one corner of the frame is deliberately quieter and emptier than the rest",
    "a subtle visual repetition links the subject's clothing to the environment",
    "an ordinary object is framed like a museum artifact",
    "a practical cable, hose, wire, or rope creates a strong compositional line",
]

CAMERA_POOL = [
    "golden-hour backlight with restrained lens flare",
    "blue-hour ambient city glow",
    "long-exposure practical light trails",
    "extreme macro with paper-thin depth of field",
    "aerial drone top-down framing",
    "tilt-shift miniature effect",
    "handheld documentary motion and natural grain",
    "medium-format square framing with creamy bokeh",
    "infrared-inspired tonal response",
    "vintage film grain with subtle light leaks",
    "wide-angle low-angle perspective",
    "85mm portrait compression with shallow depth of field",
    "high dynamic range with crisp micro-contrast",
    "soft diffused overcast lighting",
    "one hard practical light with deep shadow",
    "50mm natural perspective at eye level",
    "35mm environmental portrait framing",
    "24mm close environmental perspective",
    "70mm compressed street perspective",
    "135mm distant candid compression",
    "slightly elevated three-quarter angle",
    "low camera near floor level",
    "waist-height documentary framing",
    "over-the-shoulder environmental framing",
    "symmetrical centered framing",
    "off-center rule-of-thirds framing",
    "negative-space editorial composition",
    "tight crop with surrounding environmental clues",
    "wide establishing frame with subject clearly readable",
    "layered foreground-midground-background composition",
    "reflection-assisted framing",
    "through-doorway framing",
    "through-window framing",
    "framing through hanging objects",
    "partial foreground occlusion",
    "shallow depth with strong foreground blur",
    "deep focus from foreground to background",
    "slow-shutter candid motion",
    "freeze-frame high-speed photography",
    "subtle dutch angle for visual tension",
    "straight architectural perspective",
    "top-down tabletop perspective",
    "near-silhouette side profile framing",
    "back-of-room observational framing",
    "close portrait with environmental edge details",
    "full-body environmental portrait",
    "three-quarter portrait with visible surroundings",
    "medium shot emphasizing gesture and hands",
    "full scene with generous breathing room",
    "panoramic horizontal environmental composition",
]

SUBJECT_POOL = [
    {
        "label": "a solo person in a natural candid portrait",
        "queries": [
            "professional portrait photography person",
            "natural candid portrait photography",
            "high quality lifestyle portrait photography",
            "environmental portrait photography",
        ],
    },
    {
        "label": "a couple together in a natural candid moment",
        "queries": [
            "professional couple portrait photography",
            "candid couple photography",
            "lifestyle couple photography",
        ],
    },
    {
        "label": "a person with their pet",
        "queries": [
            "professional portrait person with dog",
            "professional portrait person with cat",
            "lifestyle person with dog",
            "lifestyle person with cat",
        ],
    },
    {
        "label": "a small family or friend group",
        "queries": [
            "professional family portrait photography",
            "candid group portrait photography",
            "lifestyle group photography",
        ],
    },
    {
        "label": "a person in an everyday candid activity",
        "queries": [
            "candid lifestyle photography person",
            "documentary candid portrait photography",
            "everyday lifestyle portrait",
        ],
    },
    {
        "label": "a person interacting with an interesting object",
        "queries": [
            "environmental portrait photography person",
            "creative lifestyle portrait",
            "documentary portrait person",
        ],
    },
    {
        "label": "a person walking through the environment",
        "queries": [
            "street portrait photography person",
            "walking candid portrait",
            "documentary street photography person",
        ],
    },
    {
        "label": "a person seated naturally within the environment",
        "queries": [
            "seated lifestyle portrait photography",
            "environmental seated portrait",
            "candid seated portrait",
        ],
    },
]


# Extra libraries give the generator even more combinations.
COLOR_STORIES = [
    "muted teal, charcoal, cream and one restrained coral accent",
    "dusty blue, warm gray, faded red and off-white",
    "forest green, clay, parchment and charcoal",
    "navy, pale cyan, concrete gray and muted orange",
    "burgundy, cream, walnut brown and slate",
    "olive, sand, faded denim and black",
    "terracotta, sage, ivory and graphite",
    "deep plum, fog gray, cream and muted yellow",
    "rust, navy, faded green and warm white",
    "cobalt, stone, charcoal and soft beige",
    "mustard, brown, cream and dark green",
    "dusty rose, brown, gray and ivory",
    "ink blue, silver gray, warm white and brick",
    "deep red, charcoal, paper white and faded blue",
    "soft lavender, graphite, cream and moss",
    "sea green, weathered wood, gray and off-white",
    "burnt orange, denim blue, cream and black",
    "dark olive, rust, concrete and parchment",
    "cool gray, electric blue and warm white",
    "warm brown, pale green and faded yellow",
]

TEXTURE_POOL = [
    "weathered paper fibers",
    "brushed metal",
    "old painted wood",
    "condensation on glass",
    "fine dust suspended in light",
    "worn leather",
    "matte ceramic",
    "rough concrete",
    "polished tile",
    "aged plaster",
    "woven cotton",
    "linen",
    "corrugated cardboard",
    "oxidized metal",
    "wet asphalt",
    "fogged glass",
    "recycled paper",
    "film grain",
    "subtle halation",
    "soft fabric fibers",
    "scratched acrylic",
    "aged newspaper",
    "paint chips",
    "ceramic glaze",
    "brushed aluminum",
]

PROP_POOL = [
    "a mechanical alarm clock",
    "a folded paper map",
    "a battered notebook",
    "a reusable metal lunch container",
    "a vintage desk fan",
    "a small analog camera",
    "a stack of handwritten index cards",
    "a repaired wooden stool",
    "a portable cassette player",
    "a ceramic mug with visible wear",
    "a brass-colored desk lamp without ornate decoration",
    "a canvas tool bag",
    "a bundle of old keys",
    "a hand mirror",
    "a folding umbrella",
    "a thermos flask",
    "a pocket flashlight",
    "a small toolbox",
    "a roll of masking tape",
    "a folded newspaper with unreadable text",
    "a fabric measuring tape",
    "a sketchbook",
    "a plant mister",
    "a spool of thread",
    "a pair of work gloves",
    "a wooden ruler",
    "a simple analog wristwatch",
    "a stack of postcards with no readable names",
    "a portable radio with no visible branding",
    "a small enamel tray",
    "a rolled diploma or certificate scroll",
    "a pair of skydiving goggles",
    "an oversized everyday object scaled for a miniature-world scene (giant spoon, giant book, giant flower)",
    "a disposable film camera",
    "a handful of scattered polaroid photos",
    "a paper boarding pass or luggage tag",
]

ACTION_POOL = [
    "adjusting a practical object with both hands",
    "pausing mid-task and looking toward a nearby sound",
    "holding an ordinary object at waist height",
    "checking a handwritten note",
    "carefully arranging several small objects",
    "leaning naturally against a work surface",
    "walking slowly through the environment",
    "looking through a window",
    "opening a drawer or cabinet",
    "repairing something small",
    "carrying a folded item",
    "sitting quietly and observing the surroundings",
    "reaching toward a shelf",
    "holding a cup or container naturally",
    "turning slightly toward the camera",
    "standing still while the environment shows motion",
    "examining a tactile surface",
    "organizing tools or materials",
    "waiting near a doorway",
    "sharing a quiet moment with the companion or pet",
    "mid-air freefall pose with arms extended, captured from an action camera angle",
    "playfully interacting with a miniature or oversized-scale object",
    "tossing a graduation cap or celebrating a milestone",
    "mid-laugh candid selfie gesture, arm extended toward the camera",
]

WARDROBE_POOL = [
    "a clean contemporary neutral outfit chosen to complement the environment",
    "practical layered clothing with subtle texture",
    "a structured jacket over a simple top",
    "a relaxed knit layer with understated accessories",
    "a crisp shirt with practical trousers",
    "a textured overshirt and simple everyday clothing",
    "a weather-appropriate coat with minimal styling",
    "a simple monochrome outfit with one muted accent",
    "casual workwear with realistic fabric creases",
    "a refined everyday outfit without visible logos",
    "a vintage-inspired outfit using generic period details",
    "a contemporary utility outfit without branding",
    "soft casual clothing suited to a quiet indoor scene",
    "weathered practical clothing appropriate to an outdoor setting",
    "a clean editorial outfit with restrained accessories",
]

DETAIL_POOL = [
    "realistic fabric creases and natural folds",
    "subtle skin texture without beauty-filter smoothing",
    "small signs of everyday wear",
    "authentic environmental imperfections",
    "slightly uneven handmade surfaces",
    "natural dust and moisture",
    "believable object wear and repair marks",
    "subtle reflections on glass and metal",
    "fine atmospheric haze",
    "tiny practical details that reward close inspection",
    "realistic fingerprints or smudges on selected surfaces",
    "natural hair strands without changing identity",
    "accurate contact shadows",
    "physically plausible material response",
    "restrained depth haze between foreground and background",
]


# ============================================================
# ENV / STATE HELPERS
# ============================================================

def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"::error::Missing required secret/env var: {name}")
        sys.exit(1)
    return value


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
                if isinstance(state, dict):
                    state.setdefault("recent", [])
                    state.setdefault("used_signatures", [])
                    state.setdefault("last_id", 0)
                    return state
        except Exception as exc:
            print(f"State load warning: {exc}")

    return {
        "recent": [],
        "used_signatures": [],
        "last_id": 0,
    }


def save_state(state: dict) -> None:
    directory = os.path.dirname(STATE_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def next_id(state: dict) -> int:
    return int(state.get("last_id", 0)) + 1


def fingerprint_components(
    medium: str,
    mood: str,
    setting: str,
    twist: str,
    camera: str,
    subject: str,
    color: str,
    texture: str,
    prop: str,
    action: str,
    wardrobe: str,
    fusion_medium: str = "",
) -> str:
    raw = "||".join([
        medium, mood, setting, twist, camera, subject,
        color, texture, prop, action, wardrobe, fusion_medium
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


FUSION_CHANCE = 0.4  # how often two mediums get forcibly fused into one hybrid style


def choose_unique_ingredients(state: dict):
    used = set(state.get("used_signatures", []))

    # Try many random combinations. With the current library sizes this
    # will almost always find a fresh combination immediately.
    for _ in range(100):
        subject = random.choice(SUBJECT_POOL)
        medium = random.choice(MEDIUM_POOL)
        fusion_medium = ""
        if random.random() < FUSION_CHANCE:
            candidates = [m for m in MEDIUM_POOL if m != medium]
            fusion_medium = random.choice(candidates)

        values = {
            "medium": medium,
            "mood": random.choice(MOOD_POOL),
            "setting": random.choice(SETTING_POOL),
            "twist": random.choice(TWIST_POOL),
            "camera": random.choice(CAMERA_POOL),
            "subject": subject["label"],
            "color": random.choice(COLOR_STORIES),
            "texture": random.choice(TEXTURE_POOL),
            "prop": random.choice(PROP_POOL),
            "action": random.choice(ACTION_POOL),
            "wardrobe": random.choice(WARDROBE_POOL),
            "fusion_medium": fusion_medium,
        }

        signature = fingerprint_components(**values)

        if signature not in used:
            return values, subject, signature

    # Extremely unlikely fallback: change one component until fresh.
    values = {
        "medium": random.choice(MEDIUM_POOL),
        "mood": random.choice(MOOD_POOL),
        "setting": random.choice(SETTING_POOL),
        "twist": random.choice(TWIST_POOL),
        "camera": random.choice(CAMERA_POOL),
        "subject": random.choice(SUBJECT_POOL)["label"],
        "color": random.choice(COLOR_STORIES),
        "texture": random.choice(TEXTURE_POOL),
        "prop": random.choice(PROP_POOL),
        "action": random.choice(ACTION_POOL),
        "wardrobe": random.choice(WARDROBE_POOL),
        "fusion_medium": "",
    }
    signature = fingerprint_components(**values)
    return values, next(
        s for s in SUBJECT_POOL if s["label"] == values["subject"]
    ), signature


# ============================================================
# OPENROUTER
# ============================================================

def get_free_models(api_key: str) -> list:
    response = requests.get(
        f"{OPENROUTER_API}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    models = response.json().get("data", [])
    free = []

    for model in models:
        pricing = model.get("pricing", {})

        try:
            prompt_cost = float(pricing.get("prompt", "1") or "1")
            completion_cost = float(pricing.get("completion", "1") or "1")
        except (TypeError, ValueError):
            continue

        if prompt_cost == 0 and completion_cost == 0:
            model_id = model.get("id")
            if model_id:
                free.append(model_id)

    def size_tier(model_id: str) -> int:
        name = model_id.lower()

        if any(k in name for k in (
            "mini", "lite", "nano", "tiny", "small",
            "1b", "2b", "3b", "4b", "7b"
        )):
            return 2

        if any(k in name for k in (
            "large", "super", "ultra", "max", "pro",
            "xl", "70b", "72b", "90b", "120b", "405b"
        )):
            return 0

        return 1

    tiers = {0: [], 1: [], 2: []}

    for model_id in free:
        tiers[size_tier(model_id)].append(model_id)

    for tier in tiers.values():
        random.shuffle(tier)

    return tiers[0] + tiers[1] + tiers[2]


def has_markers(markers: list):
    def validator(text: str) -> bool:
        return all(
            re.search(
                rf"===\s*{re.escape(marker)}\s*===",
                text,
                flags=re.IGNORECASE,
            )
            for marker in markers
        )

    return validator


def call_openrouter(
    api_key: str,
    free_models: list,
    messages: list,
    max_tokens: int = 2000,
    validator=None,
) -> str:

    last_error = None

    for model_id in free_models:
        try:
            response = requests.post(
                f"{OPENROUTER_API}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 1.0,
                },
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code != 200:
                last_error = (
                    f"{model_id} -> HTTP {response.status_code}: "
                    f"{response.text[:250]}"
                )
                continue

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            if not content or not content.strip():
                last_error = f"{model_id} -> empty response"
                continue

            content = content.strip()

            if validator and not validator(content):
                last_error = f"{model_id} -> validation failed"
                print(f"Skipping {model_id}: {last_error}")
                continue

            print(f"Used free model: {model_id}")
            return content

        except Exception as exc:
            last_error = f"{model_id} -> {exc}"

    raise RuntimeError(
        f"All free OpenRouter models failed. Last error: {last_error}"
    )


# ============================================================
# GENERATION PROMPT
# ============================================================

GEN_MARKERS = [
    "HOOK",
    "PROMPT",
    "APP",
    "THEME_USED",
    "CAPTION",
]


def build_generation_messages(
    recent_summaries: list,
    ingredients: dict,
) -> list:

    recent_block = (
        "\n".join(f"- {item}" for item in recent_summaries)
        if recent_summaries else "(none yet)"
    )

    fusion_medium = ingredients.get("fusion_medium", "")
    if fusion_medium:
        fusion_block = f"""
STYLE-FUSION REQUIREMENT (mandatory for this generation):
You have been given TWO medium/technique sparks instead of one:
  MEDIUM A: {ingredients["medium"]}
  MEDIUM B: {fusion_medium}
Do NOT just pick one or alternate between them. Genuinely FUSE them into
ONE coherent hybrid visual technique that could not be described by
either alone — invent how they combine (e.g. how a photographic base
interacts with an illustrated/textural layer, or how one technique's
characteristic marks/materials appear inside the other's structure).
This fused hybrid is the primary "medium" for this prompt.
"""
    else:
        fusion_block = ""

    system = f"""
You are an elite commercial AI-image prompt creative director.

Your task is to invent ONE original, highly detailed, production-quality
image-generation prompt for a user who will upload their own reference
photo together with your prompt.

{HARD_RULE}

ABSOLUTE DEMOGRAPHIC RULE:
Never infer or specify the reference person's gender, age, ethnicity,
race, nationality or other demographic identity. Use neutral language such
as "the person from the reference image", "they", or "their".

ABSOLUTE IMAGE-CONTENT BRAND RULE:
Do not place real celebrities, public figures, trademarked brands, logos,
sports teams, movie characters, musicians, franchises, magazine names or
other protected real-world branding inside the generated image.

AI TOOL NAMES ARE ALLOWED:
GPT Image, ChatGPT Images, Midjourney, DALL-E, Gemini, Nano Banana,
Stable Diffusion and similar AI generation tools may be named in APP and
CAPTION.

PROMPT QUALITY:
- Extremely detailed.
- Commercial-quality.
- Copy-paste ready.
- No markdown.
- No placeholders.
- No fake citations.
- No explanations.
- Include composition.
- Include camera/lens.
- Include lighting.
- Include color treatment.
- Include materials/textures.
- Include wardrobe where appropriate.
- Include pose/action.
- Include mood.
- Include aspect ratio.
- Include a concise negative-prompt section.
- Keep the face and identity lock explicit and prominent.

IMPORTANT CREATIVE DIRECTION:
The following ingredients are a starting point, not a script. Combine them
naturally. Add specific grounded details. Avoid generic "epic", "magical",
"ethereal" filler.

MEDIUM:
{ingredients["medium"]}
{fusion_block}
MOOD:
{ingredients["mood"]}

SETTING:
{ingredients["setting"]}

UNEXPECTED TWIST:
{ingredients["twist"]}

CAMERA:
{ingredients["camera"]}

SUBJECT:
{ingredients["subject"]}

COLOR STORY:
{ingredients["color"]}

TEXTURE:
{ingredients["texture"]}

KEY PROP:
{ingredients["prop"]}

ACTION:
{ingredients["action"]}

WARDROBE:
{ingredients["wardrobe"]}

RECENT CONCEPTS TO AVOID:
{recent_block}

BANNED CLICHES:
- cosmic or celestial imagery unless the required setting genuinely
  requires a night sky or space environment
- generic glowing particles, sparkle ribbons, magical portals or fantasy
  energy
- giant shells or spiral glass carriages
- floating glowing musical instruments
- generic gold/amber luxury
- palace or ballroom fantasy interiors
- red-curtain theater clichés
- endless spiral staircases
- generic "epic cinematic fantasy" filler
- random unrelated fantasy worlds
- long-exposure light-trail swirls/streaks used as a generic "awe" or
  "epic" backdrop effect, especially inside a grand, decayed, or
  under-construction ornate building (marble halls, gilded ceilings,
  crumbling opulent architecture) — this exact combination has already
  been massively overused by this system
- sparkling/glowing dust or confetti particles floating around the
  subject for a generic "magical moment" effect
- treat "make it feel epic/awe-inspiring" as a trap: express awe through
  a specific, grounded, unusual detail instead of scale + glow + ruins

The setting must genuinely match the supplied setting.
The subject must genuinely match the supplied subject.
The twist must be visible or meaningfully represented.
Do not simply list the ingredients. Turn them into one coherent visual idea.

CAPTION RULES:
The caption must:
- be 1 or 2 sentences
- sound casual and human
- contain 1 to 3 emojis
- naturally mention the recommended AI tool
- never use I, we, my, our, or us
- never say "full prompt"
- never include a URL
- never use an em dash
- never use a double hyphen

OUTPUT EXACTLY THIS FORMAT:

===HOOK===
short punchy hook, maximum 8 words

===PROMPT===
full copy-paste-ready prompt

===APP===
one short AI tool recommendation

===THEME_USED===
short theme label

===CAPTION===
casual social caption
"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "Create one completely new image prompt now."},
    ]


def parse_delimited(text: str, markers: list) -> dict:
    text = text.strip()

    text = re.sub(r"^```[a-zA-Z0-9_-]*", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    positions = []

    for marker in markers:
        match = re.search(
            rf"===\s*{re.escape(marker)}\s*===",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            positions.append(
                (match.start(), match.end(), marker.lower())
            )

    if not positions:
        raise ValueError("No known output markers found.")

    positions.sort(key=lambda item: item[0])

    result = {}

    for index, (start, end, name) in enumerate(positions):
        value_end = (
            positions[index + 1][0]
            if index + 1 < len(positions)
            else len(text)
        )

        result[name] = text[end:value_end].strip()

    missing = [
        marker for marker in markers
        if not result.get(marker.lower())
    ]

    if missing:
        raise ValueError(f"Missing fields: {missing}")

    return result


# ============================================================
# STAGE 2 REVIEW
# ============================================================

REVIEW_MARKERS = ["VERDICT", "REASON"]


def build_review_messages(
    candidate: dict,
    recent_summaries: list,
    ingredients: dict,
) -> list:

    recent_block = (
        "\n".join(f"- {item}" for item in recent_summaries)
        if recent_summaries else "(none yet)"
    )

    system = f"""
You are the final quality gate for a public AI-image prompt channel.

Review the candidate strictly.

APPROVE only if ALL requirements pass.

1. The image prompt contains an explicit, strong face/identity lock.
2. The exact reference person's face must remain preserved.
3. No gender, age, ethnicity, race, nationality or demographic assumption
   about the reference person appears in the prompt.
4. The prompt is professional, coherent and copy-ready.
5. It contains composition, lighting, camera, style, mood and negative
   prompt guidance.
6. The supplied setting is genuinely represented.
7. The supplied subject type is genuinely represented.
8. The supplied twist is meaningfully visible.
9. The concept is not a near-duplicate of recent concepts.
10. No real celebrity, public figure, trademarked brand, logo, franchise,
    movie character or sports team appears as image content.
11. AI tool names are allowed in APP/CAPTION.
12. No cosmic/celestial cliché unless the required setting itself requires
    it.
13. No generic magical sparkles, glowing portals or fantasy filler.
14. No generic palace/ballroom/theater/opulent-gold cliché.
14b. No long-exposure light-trail swirl/streak effect used as a generic
     "epic/awe" backdrop, especially inside a grand, decayed, or
     under-construction ornate building — automatic REVISE if present.
14c. No glowing/sparkling dust or confetti floating around the subject
     as a generic "magical moment" effect — automatic REVISE if present.
15. Caption sounds human and casual.
16. Caption has at least one emoji.
17. Caption naturally recommends an AI tool.
18. Caption does not use I, we, my, our, us.
19. Caption does not contain "full prompt".
20. Caption has no URL.
21. Caption has no em dash and no double hyphen.

REQUIRED SETTING:
{ingredients["setting"]}

REQUIRED SUBJECT:
{ingredients["subject"]}

CANDIDATE HOOK:
{candidate.get("hook", "")}

CANDIDATE PROMPT:
{candidate.get("prompt", "")}

CANDIDATE APP:
{candidate.get("app", "")}

CANDIDATE THEME:
{candidate.get("theme_used", "")}

CANDIDATE CAPTION:
{candidate.get("caption", "")}

RECENT CONCEPTS:
{recent_block}

Return ONLY:

===VERDICT===
APPROVE or REVISE

===REASON===
one short sentence
"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "Perform the final review now."},
    ]


# ============================================================
# IMAGE SOURCES
# ============================================================

def fetch_from_pexels(api_key: str, query: str):
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": api_key},
        params={
            "query": query,
            "per_page": 15,
            "orientation": "portrait",
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    photos = response.json().get("photos", [])

    if not photos:
        raise RuntimeError("Pexels returned no results.")

    photo = random.choice(photos[:min(8, len(photos))])
    image_url = photo["src"]["large"]

    image = requests.get(image_url, timeout=REQUEST_TIMEOUT)
    image.raise_for_status()

    return image.content, "Pexels"


def fetch_from_pixabay(api_key: str, query: str):
    def _search(editors_choice: bool):
        params = {
            "key": api_key,
            "q": query,
            "image_type": "photo",
            "orientation": "vertical",
            "category": "people",
            "per_page": 20,
            "order": "popular",
        }
        if editors_choice:
            params["editors_choice"] = "true"
        response = requests.get("https://pixabay.com/api/", params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json().get("hits", [])

    hits = _search(editors_choice=True)
    if not hits:
        hits = _search(editors_choice=False)

    if not hits:
        raise RuntimeError("Pixabay returned no results.")

    hit = random.choice(hits[:min(8, len(hits))])
    image_url = hit["largeImageURL"]

    image = requests.get(image_url, timeout=REQUEST_TIMEOUT)
    image.raise_for_status()

    return image.content, "Pixabay"


def fetch_from_unsplash(api_key: str, query: str):
    response = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {api_key}"},
        params={
            "query": query,
            "per_page": 20,
            "orientation": "portrait",
            "order_by": "relevant",
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    results = response.json().get("results", [])

    if not results:
        raise RuntimeError("Unsplash returned no results.")

    result = random.choice(results[:min(8, len(results))])
    image_url = result["urls"]["regular"]

    image = requests.get(image_url, timeout=REQUEST_TIMEOUT)
    image.raise_for_status()

    return image.content, "Unsplash"


def fetch_base_image(
    pexels_key: str,
    pixabay_key: str,
    unsplash_key: str,
    queries: list,
):
    query = random.choice(queries)

    sources = [
        (fetch_from_pexels, pexels_key),
        (fetch_from_pixabay, pixabay_key),
        (fetch_from_unsplash, unsplash_key),
    ]

    for function, key in sources:
        try:
            return function(key, query)
        except Exception as exc:
            print(
                f"Image source failed: {function.__name__}, "
                f"query={query!r}, error={exc}"
            )

    raise RuntimeError("All base-image sources failed.")


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


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def safe_truncate_html(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:max(0, limit - 1)] + "…"


def telegram_send_photo(
    token: str,
    chat_id: str,
    image_bytes: bytes,
    caption_html: str,
):
    response = requests.post(
        TELEGRAM_API.format(token=token, method="sendPhoto"),
        data={
            "chat_id": chat_id,
            "caption": caption_html,
            "parse_mode": "HTML",
        },
        files={
            "photo": ("base.jpg", image_bytes),
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()


def telegram_send_message(
    token: str,
    chat_id: str,
    text_html: str,
):
    response = requests.post(
        TELEGRAM_API.format(token=token, method="sendMessage"),
        data={
            "chat_id": chat_id,
            "text": text_html,
            "parse_mode": "HTML",
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()


# ============================================================
# MAIN
# ============================================================

def main():
    tg_token = env("TELEGRAM_BOT_TOKEN")
    tg_chat = env("TELEGRAM_CHAT_ID")

    openrouter_key = env("OPENROUTER_API_KEY")

    pexels_key = env("PEXELS_API_KEY")
    pixabay_key = env("PIXABAY_API_KEY")
    unsplash_key = env("UNSPLASH_ACCESS_KEY")

    state = load_state()

    recent_summaries = [
        item.get("summary", "")
        for item in state.get("recent", [])
        if item.get("summary")
    ][-RECENT_KEEP:]

    used_signatures = set(state.get("used_signatures", []))

    free_models = get_free_models(openrouter_key)

    if not free_models:
        print("::error::No free OpenRouter models currently available.")
        sys.exit(1)

    print(f"Found {len(free_models)} free OpenRouter models.")
    print(
        f"Stored unique ingredient combinations: "
        f"{len(used_signatures)}"
    )

    approved = None
    approved_subject = None
    approved_signature = None
    approved_ingredients = None

    for attempt in range(1, MAX_ATTEMPTS + 1):

        ingredients, subject, signature = choose_unique_ingredients(state)

        # A second guard in case the state was modified while running.
        if signature in used_signatures:
            continue

        print(
            f"\nAttempt {attempt}\n"
            f"  medium: {ingredients['medium']}\n"
            f"  fusion_medium: {ingredients.get('fusion_medium') or '(none)'}\n"
            f"  mood: {ingredients['mood']}\n"
            f"  setting: {ingredients['setting']}\n"
            f"  twist: {ingredients['twist']}\n"
            f"  camera: {ingredients['camera']}\n"
            f"  subject: {ingredients['subject']}"
        )

        try:
            generated_raw = call_openrouter(
                openrouter_key,
                free_models,
                build_generation_messages(
                    recent_summaries,
                    ingredients,
                ),
                max_tokens=4000,
                validator=has_markers(GEN_MARKERS),
            )

            candidate = parse_delimited(
                generated_raw,
                GEN_MARKERS,
            )

            review_raw = call_openrouter(
                openrouter_key,
                free_models,
                build_review_messages(
                    candidate,
                    recent_summaries,
                    ingredients,
                ),
                max_tokens=1200,
                validator=has_markers(REVIEW_MARKERS),
            )

            review = parse_delimited(
                review_raw,
                REVIEW_MARKERS,
            )

        except Exception as exc:
            print(f"Attempt {attempt} failed: {exc}")
            continue

        verdict = review.get("verdict", "").strip().upper()

        if verdict.startswith("APPROVE"):
            approved = candidate
            approved_subject = subject
            approved_signature = signature
            approved_ingredients = ingredients
            break

        print(
            f"Rejected by reviewer: "
            f"{review.get('reason', 'no reason')}"
        )

    if not approved:
        print(
            "No prompt passed review this hour. "
            "Skipping post safely."
        )
        return

    # --------------------------------------------------------
    # BASE IMAGE
    # --------------------------------------------------------

    try:
        image_bytes, image_source = fetch_base_image(
            pexels_key,
            pixabay_key,
            unsplash_key,
            approved_subject["queries"],
        )
    except Exception as exc:
        print(
            f"::error::Could not fetch base image. "
            f"Skipping post: {exc}"
        )
        return

    # --------------------------------------------------------
    # PREPARE TELEGRAM CONTENT
    # --------------------------------------------------------

    prompt_id = next_id(state)

    hook = approved.get("hook", "").strip()
    prompt_text = approved.get("prompt", "").strip()
    app_rec = approved.get("app", "").strip()
    theme_used = approved.get("theme_used", "").strip()
    caption_raw = approved.get("caption", "").strip()

    hook_html = escape_html(hook)
    app_html = escape_html(app_rec)
    prompt_html = escape_html(prompt_text)

    paste_url = create_paste_link(prompt_text)
    if paste_url:
        social_caption_raw = f"{caption_raw}\n\nFull prompt here: {paste_url}"
    else:
        social_caption_raw = caption_raw
    caption_html_raw = escape_html(social_caption_raw)

    # Image caption stays short.
    photo_caption = safe_truncate_html(
        f"<b>{hook_html}</b>\n#Prompt{prompt_id:04d}",
        TELEGRAM_MAX_CAPTION_LEN,
    )

    # Prompt message.
    prompt_header = (
        f"#Prompt{prompt_id:04d} | "
        f"Best on: {app_html}\n\n"
    )

    prompt_budget = (
        TELEGRAM_MAX_MESSAGE_LEN
        - len(prompt_header)
        - len("<code></code>")
        - 20
    )

    if len(prompt_html) > prompt_budget:
        prompt_html = (
            prompt_html[:max(0, prompt_budget - 1)]
            + "…"
        )

    prompt_message = (
        f"{prompt_header}"
        f"<code>{prompt_html}</code>"
    )

    # Social caption message.
    social_header = (
        f"#Prompt{prompt_id:04d} social caption "
        f"(tap to copy, ready for X/Twitter):\n\n"
    )

    social_budget = (
        TELEGRAM_MAX_MESSAGE_LEN
        - len(social_header)
        - len("<code></code>")
        - 20
    )

    if len(caption_html_raw) > social_budget:
        caption_html_raw = (
            caption_html_raw[:max(0, social_budget - 1)]
            + "…"
        )

    social_message = (
        f"{social_header}"
        f"<code>{caption_html_raw}</code>"
    )

    # --------------------------------------------------------
    # TELEGRAM DELIVERY
    # --------------------------------------------------------

    try:
        telegram_send_photo(
            tg_token,
            tg_chat,
            image_bytes,
            photo_caption,
        )

        telegram_send_message(
            tg_token,
            tg_chat,
            prompt_message,
        )

        telegram_send_message(
            tg_token,
            tg_chat,
            social_message,
        )

    except Exception as exc:
        print(
            f"::error::Telegram delivery failed for "
            f"#Prompt{prompt_id:04d}: {exc}"
        )
        return

    # --------------------------------------------------------
    # STATE UPDATE
    # --------------------------------------------------------

    # Only mark the combination as used AFTER successful posting.
    used_signatures.add(approved_signature)

    signatures = list(used_signatures)

    # Keep bounded state forever.
    if len(signatures) > USED_SIGNATURE_KEEP:
        signatures = signatures[-USED_SIGNATURE_KEEP:]

    state["used_signatures"] = signatures

    recent = state.get("recent", [])

    recent.append({
        "id": prompt_id,
        "summary": (
            f"[{theme_used}] "
            f"{hook}"
        ).strip(),
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "signature": approved_signature,
        "ingredients": {
            "medium": approved_ingredients["medium"],
            "fusion_medium": approved_ingredients.get("fusion_medium", ""),
            "mood": approved_ingredients["mood"],
            "setting": approved_ingredients["setting"],
            "twist": approved_ingredients["twist"],
            "camera": approved_ingredients["camera"],
            "subject": approved_ingredients["subject"],
        },
        "image_source": image_source,
    })

    state["recent"] = recent[-RECENT_KEEP:]
    state["last_id"] = prompt_id

    save_state(state)

    print(
        f"Posted #Prompt{prompt_id:04d}. "
        f"Image source: {image_source}. "
        f"Stored signatures: {len(state['used_signatures'])}"
    )


if __name__ == "__main__":
    main()
