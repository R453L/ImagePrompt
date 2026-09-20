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

# The audience strongly prefers bold, obviously-crafted/artistic results
# over results that just look like an ordinary real photo. These items
# still look essentially like a normal photograph (grain/color/lighting
# treatments aside) — everything else in MEDIUM_POOL is treated as the
# "crazy/stylized" bucket and gets picked far more often (see MEDIUM_STYLE_BIAS).
REALISTIC_MEDIUM_ITEMS = {
    "straight photorealistic editorial photography",
    "cinematic documentary photography",
    "35mm analog street photography",
    "120 medium-format portrait photography",
    "large-format studio photography",
    "instant-film snapshot aesthetic",
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
    "contemporary luxury editorial photography",
    "contact-sheet photography",
    "extreme action-camera selfie composition (motion, wide-angle distortion)",
}

REALISTIC_MEDIUM_POOL = [m for m in MEDIUM_POOL if m in REALISTIC_MEDIUM_ITEMS]
STYLIZED_MEDIUM_POOL = [m for m in MEDIUM_POOL if m not in REALISTIC_MEDIUM_ITEMS]

# Fraction of the time the wild/stylized bucket gets picked instead of
# a grounded realistic-photo medium.
MEDIUM_STYLE_BIAS = 0.75

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

# Generic (no real-brand/holiday-name) seasonal/occasion flavor, keyed by
# UTC month number. When the current month has entries, there's a boosted
# chance (SEASONAL_CHANCE) the setting comes from here instead of the
# regular SETTING_POOL — keeps content feeling timely without hardcoding
# a specific year, so this stays relevant indefinitely, just update the
# lists occasionally to match whatever is actually trending that season.
SEASONAL_POOL = {
    1: ["a fresh-start morning with crisp winter light",
        "a quiet snowy street at dawn"],
    2: ["a soft romantic pastel-lit indoor scene",
        "a cozy candlelit evening setting"],
    3: ["a fresh spring garden just starting to bloom",
        "a light rain-washed street with new green leaves"],
    4: ["a blooming orchard in full spring color",
        "a pastel spring market street"],
    5: ["a sunlit spring rooftop with fresh flowers",
        "a breezy garden party setting"],
    6: ["a bright beach or poolside scene at high summer",
        "a golden late-afternoon summer picnic"],
    7: ["a vivid summer festival or street-fair energy",
        "a sun-drenched summer road trip stop"],
    8: ["a warm late-summer harvest field",
        "a sun-faded end-of-summer beach evening"],
    9: ["a cozy back-to-routine autumn coffee-shop moment",
        "a warm-toned early-autumn park with turning leaves"],
    10: ["a pumpkin-lit, tastefully spooky autumn evening (no gore, just mood)",
         "a foggy autumn orchard at dusk"],
    11: ["a warm-toned gathering around a harvest table",
         "a cozy indoor scene with autumn leaves and soft lamps"],
    12: ["a cozy winter-holiday living room lit with warm string lights",
         "a snowy evening street glowing with warm shop windows"],
}
SEASONAL_CHANCE = 0.25  # how often an in-season setting wins over the regular pool


def get_seasonal_settings() -> list:
    month = datetime.now(timezone.utc).month
    return SEASONAL_POOL.get(month, [])


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
    "a vast salt-flat mirror reflecting the entire sky",
    "a glowing bioluminescent shoreline at night",
    "an endless lavender field stretching to the horizon",
    "a narrow red-rock slot canyon with beams of light cutting through",
    "a symmetrical alpine lake perfectly mirroring the mountains",
    "a rolling sea of desert dunes at golden hour",
    "a glowing ice-cave interior with blue light filtering through",
    "a cliffside infinity pool overlooking the ocean",
    "a colorful hillside town of stacked pastel houses",
    "a dense bamboo forest with light filtering through the stalks",
    "a floating lantern festival reflected on still water",
    "a underground crystal cavern glittering with mineral formations",
    "a terraced hillside of vividly colored tulip fields",
    "a vast canyon overlook at sunrise with layered rock strata",
    "a turquoise glacial river winding through a valley",
    "a fog-covered pine forest at first light",
    "white terraced mineral hot-spring pools cascading down a hillside (Pamukkale-style)",
    "an alien-looking island landscape with umbrella-shaped dragon's-blood trees",
    "striped rainbow-colored sandstone mountains",
    "a cave ceiling glowing like a starry night sky from thousands of tiny bioluminescent lights",
    "a coastline of thousands of interlocking hexagonal basalt columns",
    "a small colorful mineral-crusted geyser continuously spouting water",
    "a massive glowing crater burning continuously in the desert at night",
    "a striking red-orange alkaline salt lake",
    "floating limestone pillar peaks shrouded in mist",
    "a lake covered edge to edge in blooming pink lotus flowers",
    "cave-carved fairy-chimney rock formations with colorful hot-air balloons drifting overhead at sunrise",
    "a mosque interior where stained glass casts rainbow light across the floor at dawn",
    "a hillside blanketed entirely in pink cherry blossoms",
    "a frozen lake with turquoise crystal ice formations",
    "three volcanic crater lakes of totally different colors side by side",
    "limestone karst islands rising from emerald-green water",
    "ancient stone temple stupas wrapped in pre-dawn mist",
    "a stone arch bridge whose reflection in still water forms a perfect circle",
    "an overgrown green tunnel formed by trees arching over an old train track",
    "terraced turquoise lakes connected by cascading waterfalls",
    "ancient monasteries perched atop towering rock pillars",
    "a waterfall framed by dark hexagonal basalt columns",
    "an entire hillside town painted in every shade of blue",
    "a shipwreck resting on a secluded beach beneath towering limestone cliffs",
    "a sea cave formed entirely from hexagonal basalt columns",
    "intricate palace architecture with reflecting pools and manicured gardens",
    "a hot spring with rainbow-colored mineral rings",
    "rolling dunes of pure white gypsum sand",
    "swirling red-orange sandstone rock formations like frozen waves",
    "a natural pool beneath a collapsed limestone grotto ceiling",
    "a secret beach inside a collapsed sea-cave skylight",
    "a deep natural sinkhole pool with tree roots hanging into turquoise water",
    "a turquoise waterfall cutting through a red desert canyon",
    "a cave glittering with giant crystal formations",
    "a swirling blue marble cave rising from a glacial lake",
    "a vast wall of hundreds of cascading waterfalls side by side",
    "alien-looking dry desert terrain resembling another planet's surface",
    "a striped, multicolored mineral mountainside",
    "a green desert oasis ringed by towering sand dunes",
    "white sand dunes dotted with turquoise rainwater lagoons",
    "a river running in natural bands of red, yellow, green and blue",
    "blackened dead trees standing in a white clay pan against orange dunes",
    "volcanic terrain in sulfur-yellow and acid-green tones",
    "massive smooth granite boulders scattered across a beach",
    "a forest of razor-sharp limestone spires",
    "towering blood-red sand dunes",
    "a permanently bubblegum-pink lake",
    "a giant rock formation shaped like a cresting ocean wave",
    "a fjord with waterfalls cascading down steep green cliffs",
    "a beach of pure white silica sand against calm turquoise water",
    "dramatic volcanic peaks surrounding a crystal-clear lagoon",
    "a towering natural limestone sea cave",
    "a multicolored illuminated limestone cavern",
    "milky-blue geothermal spa waters surrounded by volcanic rock",
    "a plain of thousands of ancient temples emerging from morning mist",
    "a giant perfectly circular deep-blue sinkhole in open ocean",
    "dramatic granite spire mountains above a turquoise glacial lake",
    "thousands of perfectly cone-shaped grassy hills stretching to the horizon",
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


INGREDIENT_COOLDOWN_DAYS = 120  # how long an ingredient value stays de-prioritized
INGREDIENT_MIN_WEIGHT = 0.15    # never fully blocked — evergreen concepts can resurface


def weighted_choice(pool: list, last_used: dict):
    """Pick from `pool` with recently-used items temporarily de-prioritized
    (not removed) — weight recovers linearly back to 1.0 over
    INGREDIENT_COOLDOWN_DAYS, so a concept can resurface months later
    with a fresh angle instead of being permanently retired."""
    now = datetime.now(timezone.utc)
    weights = []
    for item in pool:
        last_iso = last_used.get(item)
        if not last_iso:
            weights.append(1.0)
            continue
        try:
            last_dt = datetime.fromisoformat(last_iso)
        except ValueError:
            weights.append(1.0)
            continue
        days_ago = (now - last_dt).total_seconds() / 86400
        if days_ago >= INGREDIENT_COOLDOWN_DAYS:
            weights.append(1.0)
        else:
            fraction = days_ago / INGREDIENT_COOLDOWN_DAYS
            weights.append(INGREDIENT_MIN_WEIGHT + (1.0 - INGREDIENT_MIN_WEIGHT) * fraction)
    return random.choices(pool, weights=weights, k=1)[0]


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
    last_used = state.get("ingredient_last_used", {})

    # Try many random combinations. With the current library sizes this
    # will almost always find a fresh combination immediately.
    for _ in range(100):
        subject = random.choice(SUBJECT_POOL)
        medium_bucket = STYLIZED_MEDIUM_POOL if random.random() < MEDIUM_STYLE_BIAS else REALISTIC_MEDIUM_POOL
        medium = weighted_choice(medium_bucket, last_used)
        fusion_medium = ""
        if random.random() < FUSION_CHANCE:
            candidates = [m for m in MEDIUM_POOL if m != medium]
            fusion_medium = weighted_choice(candidates, last_used)

        seasonal_options = get_seasonal_settings()
        if seasonal_options and random.random() < SEASONAL_CHANCE:
            setting_value = weighted_choice(seasonal_options, last_used)
        else:
            setting_value = weighted_choice(SETTING_POOL, last_used)

        values = {
            "medium": medium,
            "mood": weighted_choice(MOOD_POOL, last_used),
            "setting": setting_value,
            "twist": weighted_choice(TWIST_POOL, last_used),
            "camera": weighted_choice(CAMERA_POOL, last_used),
            "subject": subject["label"],
            "color": weighted_choice(COLOR_STORIES, last_used),
            "texture": weighted_choice(TEXTURE_POOL, last_used),
            "prop": weighted_choice(PROP_POOL, last_used),
            "action": weighted_choice(ACTION_POOL, last_used),
            "wardrobe": weighted_choice(WARDROBE_POOL, last_used),
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
    max_models_to_try: int = 6,
) -> str:

    last_error = None

    candidate_pool = free_models[:max_models_to_try * 2] or free_models
    models_to_try = random.sample(
        candidate_pool, min(max_models_to_try, len(candidate_pool))
    )

    for model_id in models_to_try:
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
- sound casual and human — like a real person typed it fast on their
  phone, not like polished ad copy
- contain 1 to 3 emojis
- naturally mention the recommended AI tool
- never use I, we, my, our, or us
- never say "full prompt"
- never include a URL
- never use an em dash
- never use a double hyphen
- AVOID these AI-writing tells: overly literary/poetic phrasing (e.g.
  "just enough to feel like", "a quiet little dream", "there's something
  about"), semicolon-style clause-stacking, perfectly balanced sentence
  structure, and generic hype adjectives (stunning, breathtaking,
  incredible, mesmerizing). Real people write shorter, blunter, slightly
  messy reactions.
- prefer plain, punchy, slightly imperfect phrasing and contractions
  (e.g. "this one's kinda unreal", "not gonna lie this slaps", "obsessed
  with how this turned out") over descriptive scene-painting
- end with 2 to 4 relevant, high-traffic discovery hashtags (e.g. a mix
  of broad ones like #AIart #AIphotography #AIgenerated and one tied to
  the specific AI tool named in APP, like #GPTImage2 or #Midjourney) —
  hashtags are separate from the sentence, space-separated, no commas

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

REVIEW_MARKERS = ["VERDICT", "WOW_SCORE", "REASON"]


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
21b. Caption ends with 2 to 4 relevant discovery hashtags (space
     separated) — REVISE if hashtags are missing.
21c. Caption does NOT sound AI-generated: no overly literary/poetic
     phrasing, no semicolon clause-stacking, no generic hype adjectives
     (stunning, breathtaking, incredible, mesmerizing) — REVISE if it
     reads like polished ad copy instead of a real person's quick post.
22. WOW-FACTOR: score how scroll-stopping, share-worthy and visually
    exciting the resulting image would be, from 1 (bland/forgettable,
    technically fine but nobody would stop scrolling) to 10 (genuinely
    exciting, distinctive, the kind of result people screenshot and
    share). A technically correct but safe/generic prompt should score
    low here even if it passes every other rule. APPROVE requires a
    wow-factor of 7 or higher — REVISE if it scores 6 or below, and say
    why in the reason.

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

===WOW_SCORE===
a single number from 1 to 10

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

REFERENCE_PHOTO_DIR = "reference_photos"


def fetch_base_image(queries: list = None):
    """Pick a random reference photo of Tiyashi from the local repo folder.
    `queries` is accepted (and ignored) for backward compatibility with
    the previous stock-photo-API call sites — with a single consistent
    persona, the AI image app infers pose/angle context on its own, so
    no keyword search is needed."""
    if not os.path.isdir(REFERENCE_PHOTO_DIR):
        raise RuntimeError(
            f"Reference photo folder '{REFERENCE_PHOTO_DIR}' not found in the repo."
        )

    photos = [
        f for f in os.listdir(REFERENCE_PHOTO_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not photos:
        raise RuntimeError(f"No reference photos found in '{REFERENCE_PHOTO_DIR}'.")

    chosen = random.choice(photos)
    path = os.path.join(REFERENCE_PHOTO_DIR, chosen)
    with open(path, "rb") as f:
        return f.read(), f"Tiyashi ({chosen})"


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

    openrouter_keys_raw = env("OPENROUTER_API_KEY")
    openrouter_keys = [k.strip() for k in openrouter_keys_raw.split(",") if k.strip()]
    openrouter_key = random.choice(openrouter_keys)
    print(f"Using 1 of {len(openrouter_keys)} configured OpenRouter key(s) for this run.")

    # Stock-photo APIs (Pexels/Pixabay/Unsplash) are no longer used —
    # base images now come from the local Tiyashi reference photo set.

    state = load_state()

    # Guard against double-posting: if the native GitHub schedule and the
    # external cron-job.org backup trigger both fire in the same hour,
    # only the first one should actually post. A manual "Run workflow"
    # click (workflow_dispatch) is always exempt, so testing/updating
    # never has to wait out this cooldown.
    trigger_event = os.environ.get("GITHUB_EVENT_NAME", "")
    if trigger_event == "workflow_dispatch":
        print("Manually triggered (workflow_dispatch) — skipping the duplicate-post cooldown check.")
    else:
        MIN_MINUTES_BETWEEN_POSTS = 50
        recent_list = state.get("recent", [])
        if recent_list:
            last_posted_at = recent_list[-1].get("posted_at")
            if last_posted_at:
                try:
                    last_dt = datetime.fromisoformat(last_posted_at)
                    minutes_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
                    if minutes_since < MIN_MINUTES_BETWEEN_POSTS:
                        print(
                            f"Last post was only {minutes_since:.1f} minutes ago "
                            f"(< {MIN_MINUTES_BETWEEN_POSTS} min) — skipping to avoid a duplicate post."
                        )
                        return
                except ValueError:
                    pass

    recent_summaries = [
        item.get("summary", "")
        for item in state.get("recent", [])
        if item.get("summary")
    ][-RECENT_KEEP:]

    used_signatures = set(state.get("used_signatures", []))

    free_models = []
    key_order = [openrouter_key] + [k for k in openrouter_keys if k != openrouter_key]
    for key_attempt in key_order:
        try:
            free_models = get_free_models(key_attempt)
            openrouter_key = key_attempt
            break
        except Exception as exc:
            print(f"OpenRouter key ending in ...{key_attempt[-4:]} failed to list models: {exc}")
            continue

    if not free_models:
        print("::error::No free OpenRouter models currently available (all configured keys failed).")
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
        try:
            wow_score = int(re.search(r"\d+", review.get("wow_score", "0")).group())
        except (AttributeError, ValueError):
            wow_score = 0

        print(f"Verdict: {verdict} | wow_score: {wow_score}")

        if verdict.startswith("APPROVE") and wow_score >= 7:
            approved = candidate
            approved_subject = subject
            approved_signature = signature
            approved_ingredients = ingredients
            break

        if verdict.startswith("APPROVE") and wow_score < 7:
            print(f"Reviewer approved but wow_score too low ({wow_score}/10) — treating as REVISE.")
            continue

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
        image_bytes, image_source = fetch_base_image()
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
        social_caption_raw = f"{caption_raw}\n\nFull prompt link: {paste_url}"
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

    now_iso = datetime.now(timezone.utc).isoformat()
    ingredient_last_used = state.get("ingredient_last_used", {})
    for key in ("medium", "mood", "setting", "twist", "camera",
                "color", "texture", "prop", "action", "wardrobe"):
        value = approved_ingredients.get(key)
        if value:
            ingredient_last_used[value] = now_iso
    fusion_value = approved_ingredients.get("fusion_medium")
    if fusion_value:
        ingredient_last_used[fusion_value] = now_iso
    state["ingredient_last_used"] = ingredient_last_used

    save_state(state)

    print(
        f"Posted #Prompt{prompt_id:04d}. "
        f"Image source: {image_source}. "
        f"Stored signatures: {len(state['used_signatures'])}"
    )


if __name__ == "__main__":
    main()
