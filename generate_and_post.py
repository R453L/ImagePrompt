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
    "underwater-in-a-glass-tank fashion photography composition, the subject floating inside a transparent water-filled rectangular enclosure with small fish, set outdoors in an overgrown natural or ruined setting",
    "richly bejeweled bohemian/gypsy-style portrait with layered tasseled necklaces, coin and shell ornaments, braided hair woven with charms, against a deep jewel-toned draped-fabric backdrop",
    "personalized line-art wall-mural illustration blended with the real photo, the sketched version of the subject drawn on the wall behind them in the same pose, with a cursive first-name caption and small doodled stars/clouds/moon",
    "fine colored-pencil illustration portrait with flowers braided through the hair and one arm extended toward the viewer in a warm inviting gesture",
    "extreme fisheye selfie-lens composition inside an architectural space (spiral staircase, tunnel, dome) with several cloned poses of the same subject arranged at different points around the curved space",
    "romantic sunlit colonnade multi-panel composition (a soft blended diptych/triptych of the same scene) featuring a flowing gown and an armful of flowers",
    "old-world glamour café portrait with a wide-brim hat, long gloves and a sheer scarf, moody warm vintage color grading and a blurred period-style street or interior background",
    "grayscale double-exposure portrait treatment where a large soft monochrome version of the subject's face is layered behind a sharp color foreground portrait, with faint handwritten-script texture and scattered flower petals",
    "vintage photo-booth wall-of-weathered-picture-frames grid composition, a grid of small framed close-up expression shots surrounding one larger cropped pose, decorated with hand-drawn comic-style speech-bubble captions, stars and camera doodles",
    "watercolor double-exposure travel composition blending a large soft close-up portrait above a full-body scene walking through a scenic landscape below, framed by loose paint-splatter edges and a few floating leaf details",
    "black-and-white manga/comic-panel wall-backdrop grid of stylized illustrated portrait panels behind a real color full-body photo, with a few panels containing short handwritten motivational captions",
    "ornate gilded fantasy poster composition built around a large antique clock face, the subject walking through a glowing portal doorway at the clock's center toward a smaller version of themselves, with a personalized cursive name logotype and tagline at the bottom",
    "colored-pencil sketchbook diary-page composition with visible spiral binding down one edge, several small illustrated portrait panels of the subject in different outfits/poses, and pink handwritten doodled captions and hashtags scattered between them",
    "golden-hour double-exposure composition blending a large soft close-up profile portrait wearing sunglasses above a wide sunset landscape scene below, framed by loose warm paint-splatter edges and a few birds in the sky",
    "faded ghost-silhouette double-exposure studio portrait, a soft translucent enlarged repeat of the same pose looming directly behind the sharp foreground portrait",
    "regal Egyptian-goddess art nouveau portrait with an ornate gold sunburst backdrop, symmetrical temple pillars, and jeweled ceremonial regalia",
    "meme-style UFO-abduction action composite, a bright tractor beam pulling a flailing figure upward from a chaotic city street with debris flying",
    "moody reflection portrait on a glossy black surface, the subject leaning forward so a sharp mirror-image reflection fills the lower half of the frame",
    "cinematic movie-poster montage composition with multiple overlapping close-up and full-body poses, warm backlit glow, technical diagrams and props in the background, and a bold wordmark logotype at the bottom",
    "paparazzi crowd walk-through composition, the subject striding confidently down a street lined with photographers and raised cameras, with a handwritten-style title caption in a corner",
    "surreal hand-sculpted clay/ceramic diorama portrait, the subject rendered as a glazed clay figure surrounded by matching clay sculptures of a sun, stars, open books, and a giant sculpted head",
    "opulent monogram-patterned luxury fashion portrait, a tailored monogram suit with an oversized bow, round tinted sunglasses, and a matching handbag, seated on a tufted velvet settee against a patterned wallpaper",
    "sun-faded analog film street portrait with a digital timestamp burned into the corner of the frame, warm golden-hour color cast and visible film grain",
    "infographic-style personal style guide layout, the subject's photo beside a grid of color swatches, palette names, and small outfit-idea photo thumbnails, laid out like a lifestyle infographic card",
    "clean seamless-white studio fashion portrait, a monochrome all-white outfit against a bright white backdrop with soft directional shadow",
    "infographic-style face/makeup analysis layout, the subject's selfie beside circular close-up insets of individual features, a color-swatch palette strip, and a numbered step-by-step routine row",
    "graphite pencil portrait sketch on paper with one garment area rendered in vivid colored pencil that drips and bleeds off the bottom edge of the page, shown resting on a dark surface beside loose pencils",
    "playful selfie beside a half-finished painting on an easel, the canvas showing a chibi/cartoon caricature of the same subject mid-brushstroke, both faces spattered with paint",
    "gallery-style selfie beside a row of large framed pencil-portrait artworks on an exposed brick wall, the subject's hand resting on one frame as if presenting it",
    "oversized mural of the subject painted on a weathered wall, one painted giant hand offering a tiny painted cartoon character down to the real, smaller-scale subject standing at the base of the mural reaching up",
    "serene deity-style fantasy painting, the subject rendered as a flowing-robed celestial figure with an ornate crown, standing on a lotus blossom above ocean waves with a glowing halo and distant pagodas",
    "watercolor bust-and-sketch double composition, a soft color watercolor figure seated in the foreground beside a much larger monochrome pencil-sketch version of their own face bleeding into a splattered background",
    "street-art heart-hands composition, a large painted mural portrait of the subject on a wall completing a heart-hand gesture with the real subject standing beside it, hands joined across the painted and real worlds",
    "art-gallery projection selfie, the subject making a peace sign in a white gallery space with a large projected illustrated portrait of themselves on one wall and a framed photograph on another",
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
# ADDITIONAL SPECIAL PATTERN LIBRARY
# ============================================================

# These are additive patterns only. They are designed for the hot-weather,
# fashion-forward social-media look used in the latest image sets: confident
# summer styling, strong visual variety, and deliberate gaze variation.
# They never replace the original creative libraries.
SPECIAL_PATTERN_CHANCE = 0.35

SPECIAL_PATTERN_POOL = [
    {
        "label": "sunlit rooftop summer fashion editorial",
        "setting": "a bright city rooftop in hot summer weather with open sky, warm concrete and a clean skyline",
        "wardrobe": "fashion-forward hot-weather summer styling with a fitted, confident editorial silhouette, lightweight fabrics and tasteful sensuality, no visible logos",
        "action": "standing naturally with relaxed confidence, with the gaze directed to the right side of the frame",
        "camera": "85mm fashion-editorial portrait at slightly below eye level with bright natural daylight and crisp subject separation",
        "twist": "a strong architectural shadow cuts across the rooftop while leaving the face completely clear",
        "color": "sun-washed cream, warm beige, terracotta, sky blue and deep charcoal",
        "texture": "natural skin texture, lightweight summer fabric, sun-warmed concrete and subtle wind movement in hair and clothing",
        "prop": "a simple pair of sunglasses held loosely in one hand",
        "gaze": "right",
    },
    {
        "label": "luxury poolside summer fashion editorial",
        "setting": "a modern poolside terrace on a very bright summer afternoon with turquoise water and clean resort architecture",
        "wardrobe": "bold hot-weather fashion styling with a sleek summer editorial silhouette, lightweight materials and tasteful sensuality, no branding",
        "action": "resting casually beside the pool with the gaze lifted slightly upward toward the light",
        "camera": "50mm editorial lifestyle framing with crisp daylight, controlled highlights and realistic water reflections",
        "twist": "the pool reflection creates a second geometric composition beneath the subject",
        "color": "turquoise, white, sunlit sand, coral and deep navy",
        "texture": "wet stone, fine water ripples, realistic fabric texture and natural skin detail",
        "prop": "a plain translucent water glass",
        "gaze": "up",
    },
    {
        "label": "tropical street summer street-style portrait",
        "setting": "a lively tropical city street in hot midday weather with palms, painted walls, scooters and hard sunlight",
        "wardrobe": "confident contemporary summer street-style fashion with breathable lightweight pieces, an intentionally bold silhouette and tasteful sensuality, no logos",
        "action": "walking slowly through the street while looking slightly downward as if noticing something near the pavement",
        "camera": "35mm handheld street-fashion framing with natural midday contrast and documentary realism",
        "twist": "one vivid painted wall creates a graphic color block behind the subject without obscuring the face",
        "color": "hot pink, leafy green, sun-bleached cream, cobalt and warm gray",
        "texture": "sun-faded paint, breathable fabric, realistic pavement texture and natural skin detail",
        "prop": "a small plain shoulder bag",
        "gaze": "down",
    },
    {
        "label": "seaside boardwalk summer editorial",
        "setting": "a breezy seaside boardwalk in late-afternoon summer light with ocean haze and weathered wooden railings",
        "wardrobe": "minimal but striking hot-weather fashion styling with lightweight layers, a confident editorial silhouette and tasteful sensuality, no branding",
        "action": "leaning lightly against the railing with the gaze directed toward the camera",
        "camera": "70mm compressed fashion portrait with warm backlight, clean skin detail and gentle ocean bokeh",
        "twist": "wind-driven fabric creates a strong diagonal shape that echoes the boardwalk railing",
        "color": "sea blue, ivory, faded denim, warm tan and muted red",
        "texture": "weathered wood, airy fabric, salt haze and natural hair strands moving in the breeze",
        "prop": "a plain woven tote bag",
        "gaze": "camera",
    },
    {
        "label": "summer balcony city-night fashion portrait",
        "setting": "a high apartment balcony on a warm summer night overlooking a dense city full of small practical lights",
        "wardrobe": "sleek hot-weather evening fashion with a confident silhouette, lightweight fabric and tasteful sensuality, no visible logos",
        "action": "standing near the balcony edge with the head turned slightly over the shoulder and the gaze directed to the left side of the frame",
        "camera": "85mm night editorial portrait with practical city lights, subtle rim light and crisp facial detail",
        "twist": "a glass balcony panel produces a controlled secondary reflection of the city lights",
        "color": "deep navy, warm amber, black, soft ivory and electric blue",
        "texture": "smooth lightweight fabric, glass reflections, realistic skin texture and subtle night grain",
        "prop": "a simple phone held naturally at the side",
        "gaze": "left",
    },
    {
        "label": "open-air cafe hot-weather fashion snapshot",
        "setting": "a stylish open-air cafe on a hot summer morning with striped awnings, leafy shade and sunlit tables",
        "wardrobe": "fresh fashion-forward summer styling with a fitted editorial silhouette, lightweight materials and tasteful sensuality, no logos",
        "action": "seated casually at a cafe table with the gaze turned toward the upper-right side of the frame",
        "camera": "50mm candid lifestyle fashion photography with dappled sunlight and shallow natural depth of field",
        "twist": "leaf shadows form an irregular graphic pattern across the table and nearby wall",
        "color": "cream, olive, pale yellow, espresso brown and sky blue",
        "texture": "linen-like fabric, ceramic, leafy shadows, wood grain and natural skin texture",
        "prop": "a plain iced drink in a clear glass",
        "gaze": "upper-right",
    },
    {
        "label": "beach sunset confident fashion editorial",
        "setting": "a quiet sandy beach during a warm summer sunset with low waves and a clear horizon",
        "wardrobe": "confident summer beach fashion with lightweight flowing materials, a clean editorial silhouette and tasteful sensuality, no branding",
        "action": "walking along the wet sand while looking toward the upper-left horizon",
        "camera": "35mm cinematic beach-fashion frame with low golden sunlight, realistic skin tones and subtle reflection in wet sand",
        "twist": "the wet sand mirrors the subject and sky as a clean secondary composition",
        "color": "peach, soft coral, cream, ocean blue and warm brown",
        "texture": "fine wet sand, airy fabric, sea foam and natural skin detail",
        "prop": "a simple pair of sandals carried in one hand",
        "gaze": "upper-left",
    },
    {
        "label": "summer garden party fashion portrait",
        "setting": "a lush outdoor garden gathering in bright late-summer daylight with flowers, greenery and simple tables",
        "wardrobe": "playful high-fashion summer styling with a confident silhouette, breathable fabric and tasteful sensuality, no logos",
        "action": "standing beside a garden table with the gaze directed downward toward a flower arrangement",
        "camera": "120 medium-format fashion portrait with creamy background separation, soft daylight and precise facial detail",
        "twist": "one oversized botanical leaf creates a natural foreground frame around the subject",
        "color": "leaf green, ivory, soft peach, lavender and warm tan",
        "texture": "petal detail, breathable fabric, natural foliage and realistic skin texture",
        "prop": "a small plain flower stem",
        "gaze": "down",
    },
    {
        "label": "summer night market fashion street portrait",
        "setting": "a crowded open-air summer night market with practical lights, food stalls and humid evening air",
        "wardrobe": "bold contemporary hot-weather evening fashion with a confident editorial silhouette, lightweight materials and tasteful sensuality, no branding",
        "action": "walking between market stalls while looking directly into the camera for a brief candid moment",
        "camera": "35mm handheld night street-fashion photography with realistic practical-light falloff and crisp face detail",
        "twist": "one brightly lit stall creates a strong rectangular frame behind the subject",
        "color": "deep red, amber, black, turquoise and warm cream",
        "texture": "humid pavement, lightweight fabric, practical light reflections and natural skin texture",
        "prop": "a plain paper food tray",
        "gaze": "camera",
    },
    {
        "label": "summer road-trip roadside fashion editorial",
        "setting": "a sun-baked roadside stop during a hot summer afternoon with dry grass, a parked car and distant hills",
        "wardrobe": "confident road-trip summer fashion with lightweight pieces, a strong editorial silhouette and tasteful sensuality, no logos",
        "action": "standing beside the car with one hand resting on the door while looking toward the far right horizon",
        "camera": "70mm environmental fashion portrait with hard summer sunlight, controlled contrast and natural skin tones",
        "twist": "the car window reflects a second slice of the surrounding landscape",
        "color": "dusty orange, faded blue, cream, olive and charcoal",
        "texture": "sun-baked asphalt, lightweight fabric, dusty metal and realistic skin detail",
        "prop": "a plain reusable water bottle",
        "gaze": "right",
    },
    {
        "label": "rooftop pool blue-hour fashion portrait",
        "setting": "a rooftop pool at blue hour on a warm summer evening with a softly glowing skyline",
        "wardrobe": "sleek hot-weather resort fashion with a confident editorial silhouette, lightweight fabric and tasteful sensuality, no visible branding",
        "action": "standing at the pool edge while looking slightly upward and away from the skyline",
        "camera": "85mm blue-hour fashion portrait with practical architectural light, clean rim lighting and crisp facial detail",
        "twist": "the pool edge creates a precise horizontal line that visually balances the skyline",
        "color": "cobalt, pale cyan, black, ivory and muted violet",
        "texture": "wet tile, smooth lightweight fabric, water reflections and natural skin texture",
        "prop": "a plain towel draped over one arm",
        "gaze": "up",
    },
    {
        "label": "humid summer greenhouse fashion editorial",
        "setting": "a large tropical greenhouse during a bright humid summer day with glass panels, dense plants and condensation",
        "wardrobe": "fashion-forward hot-weather styling with a clean confident silhouette, breathable materials and tasteful sensuality, no logos",
        "action": "standing between tropical plants while looking toward the lower-right foreground",
        "camera": "50mm environmental fashion portrait with soft filtered sunlight, glass reflections and precise facial detail",
        "twist": "condensation on one glass panel forms an abstract natural pattern beside the subject",
        "color": "deep green, warm ivory, terracotta, pale aqua and charcoal",
        "texture": "condensation, glossy leaves, breathable fabric and realistic skin texture",
        "prop": "a simple plant mister",
        "gaze": "lower-right",
    },
        # ============================================================
    # NEWLY ADDED STYLES BASED ON UPLOADED IMAGES
    # ============================================================
    {
        "label": "chic oversized-blazer high-fashion street portrait",
        "setting": "a stylish upscale urban street at sunset with clean modern architecture and subtle store reflections",
        "wardrobe": "an elegant oversized tailored blazer worn as a chic statement piece, tasteful high-fashion styling with bold silhouette, no visible logos",
        "action": "walking thoughtfully along the sidewalk with a relaxed posture and gaze turned slightly away from the camera",
        "camera": "85mm prime lens photography at eye level with soft ambient evening light, cream-like bokeh, and sharp subject detail",
        "twist": "the golden hour sunlight strikes the glass building facade creating a soft warm backlight frame",
        "color": "camel brown, soft beige, warm amber, graphite and ivory",
        "texture": "tailored wool-blend texture, smooth concrete, clear glass reflections and natural skin detail",
        "prop": "a small minimalist handbag",
        "gaze": "right",
    },
    # ============================================================
# NEW SPECIAL PATTERNS (inspired by your attached images)
# ============================================================

    {
        "label": "pastel ballet studio arabesque editorial",
        "setting": "a soft pink ballet studio with wooden floor, ballet barres, tall windows and gentle natural light",
        "wardrobe": "delicate lilac ruffled leotard with sheer mesh panels, cream knee-high leg warmers and pointe shoes, soft floral headpiece",
        "action": "holding a high arabesque pose with arms extended gracefully, looking toward the camera with a gentle smile",
        "camera": "50mm fashion-editorial full-body shot at eye level with soft window light and clean background separation",
        "twist": "long geometric window shadows stretch across the wooden floor while the subject stays brightly lit",
        "color": "soft lilac, cream, pale pink, warm wood and soft white",
        "texture": "sheer mesh, soft ruffles, knitted leg warmers, polished wood and natural skin detail",
        "prop": "a small floral hair accessory",
        "gaze": "camera",
    },
    {
        "label": "racing expo holographic bikini portrait",
        "setting": "a brightly lit motorsport expo hall with neon screens, racing simulators and purple ambient lighting",
        "wardrobe": "shiny holographic purple and silver bikini with clear straps, choker and arm cuffs, high-fashion race-queen silhouette",
        "action": "posing confidently with one hand on hip and the other making a peace sign near the face",
        "camera": "35mm handheld event-fashion framing with strong practical neon lights and crisp subject separation",
        "twist": "large digital racing screens create a glowing purple-blue backdrop that frames the subject",
        "color": "holographic purple, silver, electric blue, black and neon magenta",
        "texture": "glossy vinyl, clear plastic straps, metallic hardware and realistic skin sheen",
        "prop": "a small dog-tag necklace",
        "gaze": "camera",
    },
    {
        "label": "sunny balcony Calvin Klein morning portrait",
        "setting": "a bright residential balcony on a clear summer morning with laundry hanging and distant city rooftops",
        "wardrobe": "simple light-blue cotton bra and matching bottoms with clean white elastic bands, casual morning silhouette",
        "action": "standing against the railing while shielding eyes from the sun with one hand and looking upward",
        "camera": "50mm natural-light lifestyle portrait with hard midday sunlight and soft shadow falloff",
        "twist": "hanging white and blue laundry creates a soft fabric curtain behind the subject",
        "color": "sky blue, white, soft gray, warm concrete and bright daylight",
        "texture": "cotton fabric, metal railing, sun-warmed skin and laundry fabric movement",
        "prop": "none",
        "gaze": "up",
    },
    {
        "label": "penthouse sunset sheer shirt editorial",
        "setting": "a luxurious high-rise apartment at golden hour with floor-to-ceiling windows overlooking a glowing city skyline",
        "wardrobe": "oversized sheer white linen shirt worn open over black shorts, barefoot, relaxed luxury silhouette",
        "action": "leaning against the window frame while looking out over the city at sunset",
        "camera": "85mm cinematic environmental portrait with warm backlight and soft rim light on hair and shoulders",
        "twist": "the golden city lights create a second glowing composition through the glass behind the subject",
        "color": "warm amber, soft white, charcoal, peach and deep city blue",
        "texture": "sheer linen, soft carpet, glass reflections and natural skin texture",
        "prop": "none",
        "gaze": "left",
    },
    {
        "label": "ornate Chinese palace night banquet portrait",
        "setting": "a richly decorated traditional Chinese banquet hall at night with candlelight, blue-and-white porcelain and hanging lanterns",
        "wardrobe": "elaborate pink and gold embroidered traditional dress with sheer sleeves, heavy gold jewelry and ornate hairpiece",
        "action": "seated on a low carved stool while looking down and adjusting an ankle bracelet",
        "camera": "50mm cinematic portrait with warm practical candlelight and soft background bokeh",
        "twist": "hanging pearl curtains in the foreground create a soft depth layer framing the subject",
        "color": "dusty rose, antique gold, deep red, ivory and warm candlelight",
        "texture": "embroidered silk, sheer organza, polished wood and metallic jewelry details",
        "prop": "a delicate ankle bracelet with small bells",
        "gaze": "down",
    },
    {
        "label": "sea cave sheer white gown portrait",
        "setting": "a natural sea cave opening onto bright turquoise water and rocky cliffs under clear sky",
        "wardrobe": "flowing off-shoulder sheer white organza gown with gold trim, wet and clinging to the body",
        "action": "standing waist-deep in clear water while looking to the side with one hand holding the fabric at the shoulder",
        "camera": "35mm environmental fashion frame with strong natural backlight and sparkling water reflections",
        "twist": "sunlight piercing through the cave opening creates dramatic shafts of light across the water",
        "color": "turquoise, ivory, soft gold, rock gray and bright sky blue",
        "texture": "wet sheer fabric, sparkling water, rocky surfaces and natural wet skin",
        "prop": "large gold hoop earrings",
        "gaze": "right",
    },
    {
        "label": "Tang dynasty golden headdress close-up",
        "setting": "an elegant traditional Chinese interior with warm window light and soft architectural details",
        "wardrobe": "ornate pink and gold embroidered Tang-style gown with an elaborate golden phoenix headdress and long pearl chains",
        "action": "looking directly at the camera with one hand raised near the face in a soft gesture",
        "camera": "85mm close-up beauty portrait with warm directional light and shallow depth of field",
        "twist": "the long dangling pearl chains create elegant vertical lines framing the face",
        "color": "rose gold, soft pink, pearl white, warm amber and deep burgundy",
        "texture": "intricate metalwork, pearl strands, embroidered silk and soft skin detail",
        "prop": "none",
        "gaze": "camera",
    },
    {
        "label": "pink-haired beach selfie editorial",
        "setting": "a bright sandy beach with turquoise water and a small island in the distance under clear summer sky",
        "wardrobe": "tight ribbed blue low-cut top, casual beach-day silhouette",
        "action": "lying on the sand taking a selfie while holding a small seashell near the face",
        "camera": "wide-angle selfie-style close-up with bright overhead sunlight and natural beach bokeh",
        "twist": "the soft pink hair spreads across the sand creating a strong color contrast with the blue top",
        "color": "pastel pink, sky blue, sand beige, turquoise and bright white",
        "texture": "fine sand, ribbed cotton, soft hair strands and natural skin texture",
        "prop": "a small white seashell",
        "gaze": "camera",
    },
    {
        "label": "northern wilderness fur warrior portrait",
        "setting": "a cold rocky mountain landscape with patches of snow and overcast sky",
        "wardrobe": "raw fur crop top and matching skirt with leather straps, tribal necklace and braided hair",
        "action": "standing among the rocks while looking off to the side with a strong, determined expression",
        "camera": "70mm environmental portrait with cool natural light and dramatic landscape backdrop",
        "twist": "wind-blown braids and fur create dynamic movement against the still rocky background",
        "color": "earth brown, ash gray, cold white, muted green and soft skin tones",
        "texture": "thick animal fur, leather cords, braided hair and realistic skin detail",
        "prop": "a large metal pendant necklace",
        "gaze": "left",
    },
    {
        "label": "vintage clothing shop stairs portrait",
        "setting": "a cozy vintage clothing shop with wooden stairs and racks of colorful clothes in the background",
        "wardrobe": "soft pink and white lace-trimmed camisole and matching short skirt, delicate and intimate silhouette",
        "action": "sitting on the wooden stairs with knees drawn up, looking softly toward the camera",
        "camera": "50mm intimate lifestyle portrait with soft indoor light and shallow depth of field",
        "twist": "the hanging clothes create a colorful, slightly blurred tapestry behind the subject",
        "color": "soft pink, cream, warm wood, muted pastels and gentle white",
        "texture": "delicate lace, soft cotton, polished wood and natural skin detail",
        "prop": "none",
        "gaze": "camera",
    },
    {
        "label": "1920s park bicycle fashion editorial",
        "setting": "a sunny tree-lined park path with benches, a bandstand and people in period clothing",
        "wardrobe": "gray tweed blazer and matching shorts, white shirt, patterned tie, straw boater hat and leather boots",
        "action": "walking a vintage bicycle while looking toward the camera with a confident stride",
        "camera": "35mm painterly fashion frame with soft daylight and gentle background bokeh",
        "twist": "the bicycle handlebars create a strong geometric foreground element",
        "color": "soft gray, cream, warm green, muted red and golden sunlight",
        "texture": "tweed wool, leather, straw hat and natural skin freckles",
        "prop": "a vintage black bicycle",
        "gaze": "camera",
    },
    {
        "label": "night seaside lace ensemble portrait",
        "setting": "a stone pier at night beside calm dark water with distant city lights and a street musician",
        "wardrobe": "cream lace bra and flowing wide-leg trousers with an open lace coat and long pearl necklace",
        "action": "standing barefoot on the stone edge while looking slightly away with wind moving the hair and fabric",
        "camera": "50mm cinematic night portrait with practical streetlights and soft rim lighting",
        "twist": "the long pearl strands catch the light and create elegant vertical lines against the dark water",
        "color": "ivory, soft gold, deep navy, warm amber and muted teal",
        "texture": "delicate lace, flowing silk, polished stone and natural skin detail",
        "prop": "long multi-strand pearl necklace",
        "gaze": "right",
    },
    {
        "label": "desert traveler with glowing sphere",
        "setting": "a vast desert landscape with cacti under a dramatic cloudy sky",
        "wardrobe": "torn beige crop shirt and loose skirt, leather backpack and gold arm cuffs",
        "action": "standing in the desert wind while looking back over the shoulder toward the camera",
        "camera": "35mm cinematic environmental portrait with strong side light and dynamic sky",
        "twist": "a large cracked glowing sphere on the backpack radiates warm light against the cool desert tones",
        "color": "sand beige, soft red hair, glowing amber, muted green and pale blue sky",
        "texture": "weathered fabric, cracked sphere, leather straps and freckled skin",
        "prop": "a leather backpack carrying a glowing cracked sphere",
        "gaze": "camera",
    },
    {
        "label": "rooftop night sheer robe with pigeons",
        "setting": "a rooftop at night overlooking a glowing city with satellite dishes and a crescent moon",
        "wardrobe": "sheer open robe worn loosely, delicate gold jewelry and minimal underwear",
        "action": "standing among the rooftop equipment while looking to the side with wind in the hair",
        "camera": "50mm cinematic night portrait with practical city lights and soft rim light",
        "twist": "several pigeons rest around the subject creating a quiet living still-life",
        "color": "deep blue night, warm city amber, soft skin tones and muted gray",
        "texture": "sheer fabric, city lights, bird feathers and natural skin detail",
        "prop": "gold jewelry and floating white feathers",
        "gaze": "left",
    },
    {
        "label": "flooded street aquatic window portrait",
        "setting": "a flooded European street at dusk with shop windows filled with large fish and soft interior lights",
        "wardrobe": "pale green lace bra and matching bottoms under an open patterned robe",
        "action": "standing knee-deep in the water while looking slightly to the side with a calm expression",
        "camera": "50mm surreal fashion frame with soft overcast light and reflective water",
        "twist": "the shop window full of fish creates a second underwater world beside the subject",
        "color": "soft green, ivory, muted gold, gray pavement and cool water reflections",
        "texture": "wet fabric, lace details, water ripples and natural skin texture",
        "prop": "gold bracelets",
        "gaze": "right",
    },
    {
        "label": "backstage ballet dressing room portrait",
        "setting": "a slightly worn ballet dressing room with a large mirror, vanity lights and scattered papers",
        "wardrobe": "soft pink ballet leotard and tutu with an oversized cream knit cardigan slipping off one shoulder",
        "action": "sitting on a stool in front of the mirror looking over the shoulder toward the camera",
        "camera": "85mm intimate portrait with warm practical vanity lights and soft shadows",
        "twist": "butterflies rest on the mirror and walls, adding a quiet surreal detail",
        "color": "soft pink, cream, warm wood, muted gold and gentle white",
        "texture": "knit wool, tulle, aged wood and freckled skin",
        "prop": "ballet shoes and a single pink rose on the table",
        "gaze": "camera",
    },
    {
        "label": "underwater ballroom with whale",
        "setting": "an ornate flooded ballroom with marble floors, crystal chandeliers and large windows opening onto the ocean",
        "wardrobe": "flowing ivory silk slip dress with delicate straps and a gold belt, barefoot",
        "action": "dancing lightly through shallow water while looking downward with a serene expression",
        "camera": "35mm cinematic wide frame with soft underwater light rays and floating bubbles",
        "twist": "a large blue whale swims past the open windows behind the subject",
        "color": "soft ivory, deep ocean blue, warm gold, marble white and gentle aqua",
        "texture": "wet silk, marble floor, water droplets and natural skin detail",
        "prop": "a discarded violin on the floor",
        "gaze": "down",
    },
    {
        "label": "gothic courtyard pool with skeletons",
        "setting": "a stone gothic courtyard pool surrounded by arches, gargoyles and palm trees under soft daylight",
        "wardrobe": "simple black string bikini with gold accents, wet hair and relaxed resort silhouette",
        "action": "reclining on a stone lounge chair by the pool while looking toward the camera with a slight smile",
        "camera": "35mm fashion-lifestyle frame with soft natural light and clear turquoise water",
        "twist": "skeleton waiters and a skeleton floating on a inflatable create a playful dark-humor contrast",
        "color": "black, turquoise, stone gray, soft green and warm skin tones",
        "texture": "wet skin, stone carvings, pool water and fabric of the bikini",
        "prop": "a bottle of sunscreen and a skull cup with a tiny umbrella",
        "gaze": "camera",
    },
    {
        "label": "sunny gothic pool black lace editorial",
        "setting": "a sunlit poolside with classical columns, palm trees and soft architectural shadows",
        "wardrobe": "black lace bra and high-waisted lace bottoms, gold jewelry and sunglasses",
        "action": "reclining on a white lounge chair while looking slightly to the side",
        "camera": "50mm fashion-editorial frame with strong sunlight and soft pool reflections",
        "twist": "a skeleton butler stands in the background holding a tray, adding quiet surreal humor",
        "color": "black lace, white fabric, turquoise water, warm gold and soft green",
        "texture": "delicate lace, wet skin, pool water and polished gold jewelry",
        "prop": "sunglasses and a dark glass bottle beside the chair",
        "gaze": "right",
    },
    {
        "label": "urban denim jacket sunset editorial portrait",
        "setting": "a city balcony overlooking a glowing horizon during golden hour with distant urban structures",
        "wardrobe": "casual-chic denim jacket styled over a clean minimalist top, timeless urban fashion, no branding",
        "action": "leaning gently against a metal railing, looking towards the warm sunset light with a serene expression",
        "camera": "50mm medium portrait with rich golden backlight, crisp facial clarity, and natural depth of field",
        "twist": "sun flare naturally wraps around the subject's shoulder without obscuring the face",
        "color": "indigo blue, warm golden orange, charcoal, and soft sunset pink",
        "texture": "denim weave, metallic railing, soft sunlight glow and realistic hair texture",
        "prop": "a sleek modern wristwatch",
        "gaze": "upper-right",
    },
    {
        "label": "cozy cable-knit sweater indoor window portrait",
        "setting": "a minimalist sunlit apartment room beside a large floor-to-ceiling glass window with soft curtains",
        "wardrobe": "a cozy oversized cable-knit sweater with rich woven texture and relaxed comfortable fit, no visible logos",
        "action": "sitting comfortably near the window with a warm mug in hand, gazing softly towards the window glass",
        "camera": "85mm portrait photography with soft diffused daylight, gentle shadows, and clean high-detail rendering",
        "twist": "soft window condensation creates a subtle dreamlike gradient near the outer edge of the frame",
        "color": "cream white, warm oatmeal, soft gray, and natural wood tones",
        "texture": "heavy knit yarn, polished glass, soft sheer curtain fabric and natural skin detail",
        "prop": "a ceramic coffee mug held gently with both hands",
        "gaze": "left",
    },
    {
        "label": "glamorous evening satin dress studio portrait",
        "setting": "a high-end studio space with deep dramatic shadows and a single warm directional spotlight",
        "wardrobe": "a sophisticated floor-length satin evening gown with elegant drapery and subtle sheen, no branding",
        "action": "standing with regal posture, head turned gracefully with a confident gaze toward the light source",
        "camera": "120 medium-format studio photography, low-key lighting with high dynamic contrast and pin-sharp focus",
        "twist": "a subtle satin shadow fold creates an architectural geometric line across the background wall",
        "color": "emerald green, deep obsidian black, champagne gold highlights, and warm bronze",
        "texture": "glossy satin fabric, soft studio backdrop, crisp facial features and realistic skin highlights",
        "prop": "a pair of elegant drop earrings",
        "gaze": "upper-left",
    },
    {
        "label": "edgy leather jacket urban alley portrait",
        "setting": "a dramatic city alleyway at twilight with subtle neon signs reflecting off damp pavement",
        "wardrobe": "a fitted black leather jacket over a sleek dark outfit, confident contemporary street fashion, no logos",
        "action": "standing with one hand resting in the jacket pocket, looking directly into the camera with an intense expression",
        "camera": "35mm editorial street-style photography, cinematic lighting with rich contrast and sharp foreground detail",
        "twist": "a neon light reflection on wet pavement creates a glowing directional leading line toward the subject",
        "color": "leather black, crimson red, deep cyan, and cool pavement gray",
        "texture": "grained leather, wet asphalt, subtle metallic zipper details and crisp facial geometry",
        "prop": "a classic leather belt accent",
        "gaze": "camera",
    },
    {
        "label": "vibrant floral summer dress garden portrait",
        "setting": "a lush botanical garden with blooming vibrant flowers and dappled sunlight filtering through tree leaves",
        "wardrobe": "a light flowing summer dress with tasteful floral prints and breathable movement, no branding",
        "action": "walking slowly along a garden path, holding the skirt lightly while looking down with a gentle smile",
        "camera": "70mm portrait lens, natural backlight, soft organic bokeh with precise facial and outfit separation",
        "twist": "dappled sunlight forms an intricate organic shadow pattern on the garden path beside the subject",
        "color": "soft pastel pink, leafy green, sunflower yellow, and soft sky blue",
        "texture": "light chiffon fabric, fresh plant leaves, flower petals and natural skin texture",
        "prop": "a single sun hat held behind the back",
        "gaze": "down",
    },
    {
        "label": "minimalist athletic athleisure studio portrait",
        "setting": "a clean modern studio space with neutral gray background and diffused softbox lighting",
        "wardrobe": "sleek minimalist athleisure wear with clean lines and comfortable modern fit, no visible logos",
        "action": "standing in a strong, grounded pose with hands resting naturally at the waist, gazing toward the camera",
        "camera": "50mm high-key commercial portrait photography with balanced shadowless lighting and crisp detail",
        "twist": "a subtle dual-tone backdrop shadow provides depth without distracting from the subject",
        "color": "matte slate gray, stark white, charcoal, and subtle blush pink",
        "texture": "stretch performance fabric, smooth studio floor, clear skin texture and fine hair strands",
        "prop": "a minimalist sports water bottle beside the feet",
        "gaze": "camera",
    },
    {
        "label": "vintage retro retro-vibes Polaroid snapshot",
        "setting": "a cozy retro-styled living room with vintage furniture, warm lamps, and vinyl record displays",
        "wardrobe": "1990s inspired casual outfit featuring high-waisted denim and a vintage graphic tee without real-brand logos",
        "action": "sitting on a vintage couch with a relaxed candid smile, looking toward the side of the room",
        "camera": "instant-film snapshot camera style with natural flash falloff, warm analog color cast and slight film grain",
        "twist": "the frame features subtle Polaroid-style border framing and authentic analog flash characteristics",
        "color": "warm mustard yellow, faded denim blue, burnt orange, and warm cream",
        "texture": "vintage denim, soft velvet sofa texture, subtle film grain and natural skin detail",
        "prop": "a vintage vinyl record sleeve held casually",
        "gaze": "right",
    },
    {
        "label": "boho-chic suede fringed jacket outdoor portrait",
        "setting": "an open golden meadow at dusk with tall dry grass swaying in the gentle breeze",
        "wardrobe": "a stylish suede jacket with subtle fringe details paired with Bohemian accessories, no branding",
        "action": "standing in the meadow while lightly touching the suede fringe, looking upward toward the evening sky",
        "camera": "85mm wide-aperture portrait with golden hour rim lighting, soft creamy background and sharp face focus",
        "twist": "tall golden grass stems naturally frame the bottom edge of the image composition",
        "color": "warm tan brown, golden wheat, muted burgundy, and twilight blue",
        "texture": "soft suede leather, dry meadow grass, woven fabric and natural hair highlights",
        "prop": "a braided leather bracelet",
        "gaze": "up",
    },
        # ============================================================
    # ADDITIONAL STYLES BASED ON LATEST IMAGE BATCH
    # ============================================================
    {
        "label": "riverside forest stream natural portrait",
        "setting": "a clear natural mountain stream with smooth river stones and green forest foliage in background",
        "wardrobe": "tasteful floral patterned swimwear with delicate strap details, natural outdoor look, no visible logos",
        "action": "resting gently in the shallow clear stream water with hands extended forward and a relaxed warm expression",
        "camera": "35mm natural light portrait with sharp subject clarity, clear water reflections, and soft forest depth",
        "twist": "sunlight filtering through trees creates glistening light caustics on the crystal clear water surface",
        "color": "emerald green, clear aqua blue, soft blush pink, and stone gray",
        "texture": "clear rippling water, wet river stones, mossy greenery and natural skin highlights",
        "prop": "a wooden riverside sauna cabin blurred in distant background",
        "gaze": "camera",
    },
    {
        "label": "festive rooftop maid-inspired cosplay portrait",
        "setting": "an vibrant open-air urban rooftop cafe at dusk with festival lights and city architecture reflections",
        "wardrobe": "a playful maid-inspired ruffled accent top and skirt ensemble with decorative headpiece, high-fashion cosplay style, no branding",
        "action": "winking cheerfully while giving a friendly wave with one hand raised near the shoulder",
        "camera": "50mm portrait lens, rich ambient dusk lighting with glowing warm bokeh, pin-sharp details",
        "twist": "warm golden string lights create a luminous bokeh garland effect across the upper frame",
        "color": "deep navy blue, crisp white, warm amber, and twilight purple",
        "texture": "ruffled fabric trim, smooth satin bows, glowing party lights and crisp facial features",
        "prop": "a decorative matching frilled headpiece",
        "gaze": "camera",
    },
    {
        "label": "evening sky bar maid-cosplay server portrait",
        "setting": "an elegant rooftop sky bar with wooden counter top, chalkboards, and glowing city sunset horizon",
        "wardrobe": "stylish maid-themed hospitality attire with ruffled lace edges and apron detail, no visible logos",
        "action": "standing beside a bar counter holding a serving tray gracefully, smiling warmly at the camera",
        "camera": "85mm prime lens portrait with warm sunset backlight and crisp detail separation",
        "twist": "the glowing orange sunset skyline creates a dramatic warm contour around the silhouette",
        "color": "warm amber orange, jet black, stark white, and natural dark wood",
        "texture": "polished wooden bar top, lace ruffles, slate chalkboard texture and natural skin glow",
        "prop": "a round metallic serving tray",
        "gaze": "camera",
    },
    {
        "label": "cozy sunlit bedroom loungewear portrait",
        "setting": "a minimalist bright sunlit bedroom with soft white pillows and clean natural light filtering through window",
        "wardrobe": "minimalist matching white cotton athletic loungewear set, clean simple aesthetic, no brand logos",
        "action": "resting relaxed on a white bed cushion with a cheerful candid expression",
        "camera": "50mm bright high-key indoor photography, natural soft daylight, subtle shadows, high sharpness",
        "twist": "soft morning sunlight creates a clean pastel tone throughout the background",
        "color": "pure white, soft cream, warm ivory, and natural skin tones",
        "texture": "soft cotton fabric, woven bed linen, fluffy pillows and natural skin texture",
        "prop": "a clean white pillow",
        "gaze": "camera",
    },
    {
        "label": "bright sunny tennis court athletic portrait",
        "setting": "an outdoor professional tennis court under a vivid blue sky with crisp green court backdrop",
        "wardrobe": "chic white athletic tennis crop top and pleated athletic skirt, modern activewear, no visible branding",
        "action": "action pose tossing a tennis ball mid-air overhead while holding a tennis racket ready to serve",
        "camera": "35mm dynamic low-angle sports portrait with high shutter speed capturing freeze-motion detail",
        "twist": "the vibrant yellow tennis ball is perfectly frozen in mid-air against the bright blue sky",
        "color": "bright white, sky blue, tennis yellow, and deep court green",
        "texture": "pleated athletic fabric, racket grip texture, court surface and bright sunlight glints",
        "prop": "a classic tennis racket held firmly in hand",
        "gaze": "up",
    },
    {
        "label": "tropical beach resort coconut drink portrait",
        "setting": "a pristine tropical white sand beach with turquoise ocean waves and wooden cabana lounge area",
        "wardrobe": "elegant white and navy trimmed beachwear, chic tropical resort styling, no brand logos",
        "action": "holding out a fresh coconut drink decorated with a tropical flower towards the camera with a playful smile",
        "camera": "50mm wide-aperture portrait with bright tropical daylight, soft ocean bokeh, and sharp foreground focus",
        "twist": "the extended arm creates a compelling depth-of-field perspective drawing focus to the warm smile",
        "color": "turquoise blue, pristine white, coconut brown, and hibiscus red",
        "texture": "fresh coconut husk, soft beach sand, tropical palm leaves and glowing skin texture",
        "prop": "a fresh tropical coconut drink with a straw and red flower",
        "gaze": "camera",
    },
    {
        "label": "tropical resort sun deck woven hat portrait",
        "setting": "a sun-drenched resort boardwalk terrace overlooking turquoise sea and distant tropical islands",
        "wardrobe": "classic white resort swimwear with subtle navy trim paired with a wide-brim woven straw hat, no logos",
        "action": "gently touching the brim of a woven straw hat while smiling pleasantly toward the viewer",
        "camera": "85mm outdoor portrait photography with warm natural sunlight and soft ocean background",
        "twist": "intricate woven straw hat patterns cast subtle decorative shade lines across the upper forehead",
        "color": "straw yellow, ocean turquoise, white, and deep navy blue",
        "texture": "woven straw texture, braided hair, wooden deck planks and clear ocean water",
        "prop": "a pair of stylish sunglasses held in the other hand",
        "gaze": "camera",
    },
    {
        "label": "crystal sea shoreline wave splash portrait",
        "setting": "shallow crystal-clear ocean water washing over a sandy shoreline under a bright blue sky",
        "wardrobe": "minimalist crisp white two-piece swimwear with navy piping accents, timeless beach look, no logos",
        "action": "walking forward through shallow ocean water, waving hand gently towards the camera with a joyful laugh",
        "camera": "50mm full-body coastal portrait, high shutter speed capturing crisp ocean water splashes",
        "twist": "gentle sea foam swirls around the ankles creating natural white motion lines against the clear water",
        "color": "crystal azure, foam white, seafoam green, and bright sky blue",
        "texture": "glistening sea foam, wet sand, clear rippling water and flowing natural hair",
        "prop": "natural sea foam ripples",
        "gaze": "camera",
    },
    {
        "label": "luxury resort pool float tropical portrait",
        "setting": "a luxury infinity swimming pool surrounded by tropical palm trees and poolside cabanas",
        "wardrobe": "chic white tropical beachwear with dark trim, relaxed summer resort aesthetic, no logos",
        "action": "resting casually beside a colorful pool float at the edge of the crystal clear water",
        "camera": "50mm medium portrait with bright sunlight, crisp reflections, and vibrant tropical color saturation",
        "twist": "caustic sunlight patterns shimmer on the floor of the swimming pool in the background",
        "color": "pool turquoise, tropical green, hibiscus pink, and bright white",
        "texture": "smooth pool tile, clear water surface, tropical foliage and glossy float texture",
        "prop": "a tropical printed inflatable pool ring",
        "gaze": "camera",
    },
    {
        "label": "retro 1950s american diner server portrait",
        "setting": "a vibrant retro 1950s American diner with neon orange accents, chrome stools, and dessert displays",
        "wardrobe": "a stylized high-fashion retro diner server costume in bright orange and silver metallic accents, no logos",
        "action": "holding a silver serving tray with a freshly baked pie, smiling brightly towards the camera",
        "camera": "35mm cinematic editorial portrait with bright warm interior lighting and vivid color depth",
        "twist": "glossy chrome and glass surfaces reflect glowing neon orange ambient light across the diner",
        "color": "neon orange, metallic silver, cream white, and glossy chrome",
        "texture": "glossy vinyl upholstery, metallic chrome, glass display case and dessert crust texture",
        "prop": "a silver tray with a slice of apple pie and a milkshake glass",
        "gaze": "camera",
    },

]


def choose_special_pattern(last_used: dict):
    """Choose one new hot-weather fashion pattern without removing any
    existing ingredient-library behavior."""
    return weighted_choice(SPECIAL_PATTERN_POOL, last_used)


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
TREND_KEYWORDS_PATH = "state/trend_keywords.json"


def load_fallback_trend_keywords() -> list:
    """Load safe local keywords when no external trend source is available."""
    try:
        with open(TREND_KEYWORDS_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            keywords = payload.get("keywords", [])
        else:
            keywords = payload

        if isinstance(keywords, list):
            return [
                str(keyword).strip()
                for keyword in keywords
                if str(keyword).strip()
            ]
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    return [
        "AI art",
        "AI photography",
        "generative art",
        "image generation",
        "cinematic portrait",
        "editorial portrait",
    ]
def build_trend_overlay_block() -> str:
    """Keep trend wording optional while preserving the existing human caption style."""
    keywords = load_fallback_trend_keywords()
    keywords_text = ", ".join(keywords[:6])

    return f"""
TREND OVERLAY RULES:
- Treat these terms as optional topical context, not as a keyword list: {keywords_text}
- Keep the caption realistic, casual, and written from the account owner's first-person perspective.
- Use at most one primary trend phrase and one supporting phrase.
- Use a trend phrase only when it naturally matches the image, prompt, or AI tool.
- Never force, repeat, or dump trend keywords into the caption.
- If trend wording sounds awkward or robotic, omit it and keep the normal caption style.
- If no usable trend phrase is available, write the caption normally without mentioning trends.
"""
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
# SPECIAL-PATTERN SELECTION OVERLAY (ADDITIVE ONLY)
# ============================================================

_ORIGINAL_CHOOSE_UNIQUE_INGREDIENTS = choose_unique_ingredients


def choose_unique_ingredients(state: dict):
    """Keep the original chooser intact, then optionally overlay one of
    the new special patterns. Existing libraries, uniqueness logic and
    fallback behavior remain available exactly as before."""
    used = set(state.get("used_signatures", []))

    for _ in range(40):
        values, subject, _ = _ORIGINAL_CHOOSE_UNIQUE_INGREDIENTS(state)

        if random.random() >= SPECIAL_PATTERN_CHANCE:
            return values, subject, fingerprint_components(
                medium=values["medium"],
                mood=values["mood"],
                setting=values["setting"],
                twist=values["twist"],
                camera=values["camera"],
                subject=values["subject"],
                color=values["color"],
                texture=values["texture"],
                prop=values["prop"],
                action=values["action"],
                wardrobe=values["wardrobe"],
                fusion_medium=values.get("fusion_medium", ""),
            )

        pattern = random.choice(SPECIAL_PATTERN_POOL)

        # Overlay only the creative ingredients needed to make the new
        # pattern coherent. All original pools and selection machinery stay.
        for key in (
            "setting", "wardrobe", "action", "camera", "twist",
            "color", "texture", "prop",
        ):
            values[key] = pattern[key]

        values["special_pattern"] = pattern["label"]
        values["special_gaze"] = pattern["gaze"]
        values["fusion_medium"] = ""

        signature = fingerprint_components(
            medium=values["medium"],
            mood=values["mood"],
            setting=values["setting"],
            twist=values["twist"],
            camera=values["camera"],
            subject=values["subject"],
            color=values["color"],
            texture=values["texture"],
            prop=values["prop"],
            action=values["action"],
            wardrobe=values["wardrobe"],
            fusion_medium=values.get("fusion_medium", ""),
        )

        if signature not in used:
            return values, subject, signature

    # Preserve the original chooser's guaranteed-fresh fallback if every
    # attempted special overlay collides with stored history.
    return _ORIGINAL_CHOOSE_UNIQUE_INGREDIENTS(state)


# ============================================================
# OPENROUTER
# ============================================================

class KeyRotator:
    """Cycles through all configured OpenRouter keys. Starts at a random
    key (spreads load across runs) and rotates forward whenever the
    current key is rate-limited or rejected — so a single run actually
    uses the COMBINED quota of every configured key, instead of getting
    stuck on one exhausted key for the whole run."""

    def __init__(self, keys: list):
        if not keys:
            raise ValueError("KeyRotator needs at least one key.")
        self.keys = keys
        self.index = random.randrange(len(keys))

    def current(self) -> str:
        return self.keys[self.index]

    def rotate(self) -> None:
        self.index = (self.index + 1) % len(self.keys)

    def __len__(self) -> int:
        return len(self.keys)


class RequestBudget:
    """Hard cap on total OpenRouter HTTP requests for this run, so one
    run can never burn through the entire combined daily quota of all
    configured keys (leaving room for the other ~23 runs that day)."""

    def __init__(self, limit: int):
        self.remaining = limit

    def take(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True


def get_free_models(key_rotator: "KeyRotator") -> list:
    last_err = None

    for _ in range(len(key_rotator)):
        api_key = key_rotator.current()
        try:
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

        except Exception as exc:
            last_err = f"key ...{api_key[-4:]} -> {exc}"
            print(f"Listing models failed, rotating key: {last_err}")
            key_rotator.rotate()
            continue

    raise RuntimeError(f"Could not list models with any configured key. Last error: {last_err}")


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
    key_rotator: "KeyRotator",
    free_models: list,
    messages: list,
    max_tokens: int = 2000,
    validator=None,
    max_models_to_try: int = 6,
    budget: "RequestBudget" = None,
) -> str:

    last_error = None

    candidate_pool = free_models[:max_models_to_try * 2] or free_models
    models_to_try = random.sample(
        candidate_pool, min(max_models_to_try, len(candidate_pool))
    )

    for model_id in models_to_try:
        keys_tried_for_this_model = 0

        while keys_tried_for_this_model < len(key_rotator):
            if budget is not None and not budget.take():
                raise RuntimeError(
                    f"Request budget exhausted for this run. Last error: {last_error}"
                )

            api_key = key_rotator.current()
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

                if response.status_code in (429, 401, 402):
                    # rate-limited / unauthorized / payment-required — a
                    # quota or key problem, not a model problem: rotate
                    # to the next key and retry the SAME model with it.
                    last_error = (
                        f"{model_id} -> key ...{api_key[-4:]} "
                        f"HTTP {response.status_code}: {response.text[:150]}"
                    )
                    print(f"Rotating OpenRouter key ({last_error})")
                    key_rotator.rotate()
                    keys_tried_for_this_model += 1
                    continue

                if response.status_code != 200:
                    last_error = (
                        f"{model_id} -> HTTP {response.status_code}: "
                        f"{response.text[:250]}"
                    )
                    break  # not a quota issue — move on to the next model

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                if not content or not content.strip():
                    last_error = f"{model_id} -> empty response"
                    break

                content = content.strip()

                if validator and not validator(content):
                    last_error = f"{model_id} -> validation failed"
                    print(f"Skipping {model_id}: {last_error}")
                    break

                print(f"Used free model: {model_id} (key ...{api_key[-4:]})")
                return content

            except Exception as exc:
                last_error = f"{model_id} -> {exc}"
                break

    raise RuntimeError(
        f"All free OpenRouter models/keys failed. Last error: {last_error}"
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
    trend_overlay = build_trend_overlay_block()
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

{CLARITY_RULE}

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

BOLDNESS CALIBRATION — if the medium is a stylized/artistic one (not
straight photography), it must be executed as a GENUINELY DRAMATIC,
graphically obvious transformation — the kind that stops a scroll —
not a subtle grain/color/texture wash layered thinly over what is
still basically a normal photo. Benchmark examples of the target level
of boldness: a multi-panel contact-sheet grid of the same person in
different poses; a composition clearly split down the middle where one
half is full photorealism and the other half is bold ink-line
illustration; a magazine-cover-style layout with oversized graphic
typography and halftone dots; a 3D collectible-figurine-in-packaging
presentation; a doodle-shadow cast on a wall beside the real person.
Notice these all keep the real person's area crisp and photographic
while the "art" happens in a clearly separate zone, panel, or contrast
layer — that is the technique to reach for (see the clarity rule above).
If your instinct is to just add film grain and a color wash to an
otherwise ordinary photo, that is NOT bold enough — push further into
an actual compositional or medium transformation.

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
{trend_overlay}
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
- always start with a capital letter (even in a casual style, the
  first letter of the sentence is capitalized — casual tone does not
  mean lowercase-only texting style)
- be 1 or 2 sentences
- sound casual and human — like a real person typed it fast on their
  phone, not like polished ad copy
- contain 1 to 3 emojis
- naturally mention the recommended AI tool
- write naturally in first person as the account owner, using I, me, my, or I'm when appropriate; never describe the account owner as "this person", "the subject", "the creator", "she", "he", or "they"
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
- WATAA / PYAR CONTEXT WORDS: look back at the PROMPT you just wrote.
  If it involves water, ocean, sea, rain, a lake, river, pool,
  waterfall or any other water/aquatic element, naturally work the
  word "wataa" into one sentence of the caption as an ordinary word —
  it must fit the sentence grammatically, never dropped in on its own
  and never turned into a hashtag. If the PROMPT involves love,
  romance, affection or tenderness, naturally work the word "pyar"
  into the caption the same way. If both apply, include both words
  naturally in the caption. If neither applies, do not use either
  word — most captions will not use them. Every time you do use
  "wataa" and/or "pyar", phrase the sentence differently from however
  you may have phrased it before — never settle into a repeated
  template or fixed wording for these, since sounding canned/repetitive
  hurts reach.
- end with 2 to 4 relevant, high-traffic discovery hashtags. Draw from a
  MIX of these (rotate — do not use the same combination every time):
  broad/high-volume: #AIart #AIartcommunity #AIartist #AIgenerated
  #AIphotography #digitalart #conceptart #generativeart #AIartdaily
  #AIartwork
  tool-specific (pick the one matching APP): #Midjourney #MidjourneyAI
  #GPTImage2 #DALLE3 #StableDiffusion #NanoBanana #GeminiAI
  Never use sexualized/thirst-trap-style tags (e.g. #AImodel #AIgirl
  #AIbeauty) — keep tags squarely about the art/technology, not the
  person's body.
  Hashtags are separate from the sentence, space-separated, no commas.

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
# SPECIAL-PATTERN GENERATION OVERLAY (ADDITIVE ONLY)
# ============================================================

_ORIGINAL_BUILD_GENERATION_MESSAGES = build_generation_messages


def build_generation_messages(
    recent_summaries: list,
    ingredients: dict,
) -> list:
    """Retain the original generation prompt and add instructions only
    when a new special pattern was selected."""
    messages = _ORIGINAL_BUILD_GENERATION_MESSAGES(
        recent_summaries,
        ingredients,
    )

    special_pattern = ingredients.get("special_pattern")
    if special_pattern:
        special_block = f"""

SPECIAL PATTERN OVERLAY (ADDED FOR THIS PROMPT ONLY):
Pattern: {special_pattern}

This prompt belongs to the new hot-weather fashion/social-media pattern
family. Preserve the supplied pattern details and make the final image
feel like a confident, fashion-forward summer editorial photograph rather
than ordinary everyday clothing. Keep the styling tasteful and non-explicit.

GAZE VARIATION REQUIREMENT:
The intended gaze for this special pattern is {ingredients.get("special_gaze", "varied")}. Follow that gaze direction naturally. Do not copy the gaze direction from the reference image. The reference image is for identity only.

Do not treat this pattern as a template. Keep the identity lock, clarity
rule, demographic neutrality, originality rules, and all existing
requirements from the original generation prompt fully active.
"""
        messages[0]["content"] += special_block

    return messages


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
1b. The prompt explicitly ensures the face and clothing stay sharp,
    clear and legible even with the chosen medium/effect — REVISE if a
    global filter, grain, texture wash, or paint effect would visibly
    degrade/obscure the face or clothing across the whole frame.
1c. If the medium is stylized/artistic (not straight photography), it
    must read as a genuinely bold, graphically obvious transformation
    (e.g. a clear split composition, a distinct illustrated panel/layer,
    an obvious graphic-design layout) — REVISE if it's really just a
    normal photo with a thin grain/color/texture wash over the whole
    frame, since that is not bold enough for this audience.
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
18. Caption uses a natural first-person account voice and does not describe the account owner as a third-person subject.
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
{build_trend_overlay_block()}
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


# ============================================================
# CAPTION ENHANCEMENT (ADDITIVE ONLY — fixed footer + word cap)
# ============================================================
# The wataa/pyar context words are handled entirely by the LLM inside
# the single existing generation call (see the "WATAA / PYAR CONTEXT
# WORDS" rule in CAPTION RULES above) — the model looks at the PROMPT
# it just wrote and naturally works "wataa"/"pyar" into the CAPTION
# itself when water/love themes are present, with fresh phrasing every
# time. No second API call, no fixed template sentences here — this
# keeps everything to one generation call per attempt, same as before.
#
# This block only adds the fixed footer lines and enforces the 280-word
# cap, in plain Python, after the caption comes back.

CAPTION_WORD_LIMIT = 280  # word cap for the caption body. The later
# "Full prompt link: ..." section is appended AFTER this limit is
# enforced, so it is never counted against the 280 words.

CAPTION_FIXED_FOOTER = (
    "Use Chatgpt/Gemini/Midjourney/grok prompt & Ur Image.\n"
    "Prompt in the first comment"
)


def enforce_caption_word_limit(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit])


def build_enhanced_caption(caption_raw: str) -> str:
    """Append the fixed footer lines to the LLM-written caption, then
    enforce the 280-word cap. The caption itself (including any
    wataa/pyar wording) is left exactly as the model wrote it."""
    caption = f"{caption_raw}\n\n{CAPTION_FIXED_FOOTER}"
    caption = enforce_caption_word_limit(caption, CAPTION_WORD_LIMIT)
    return caption


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
# SPECIAL TELEGRAM LABEL (ADDITIVE ONLY)
# ============================================================


def special_prompt_label(ingredients: dict) -> str:
    """Return the exact Telegram marker requested for new special-pattern
    prompts, while leaving all ordinary prompt numbering unchanged."""
    return " (Spacial)" if ingredients.get("special_pattern") else ""


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

    try:
        free_models = get_free_models(key_rotator)
    except Exception as exc:
        print(f"::error::No free OpenRouter models currently available (all configured keys failed): {exc}")
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

        if request_budget.remaining <= 0:
            print(f"Request budget ({REQUEST_BUDGET_PER_RUN}) exhausted — stopping attempts for this run.")
            break

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
                key_rotator,
                free_models,
                build_generation_messages(
                    recent_summaries,
                    ingredients,
                ),
                max_tokens=4000,
                validator=has_markers(GEN_MARKERS),
                budget=request_budget,
            )

            candidate = parse_delimited(
                generated_raw,
                GEN_MARKERS,
            )

            review_raw = call_openrouter(
                key_rotator,
                free_models,
                build_review_messages(
                    candidate,
                    recent_summaries,
                    ingredients,
                ),
                max_tokens=1200,
                validator=has_markers(REVIEW_MARKERS),
                budget=request_budget,
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
    if caption_raw:
        caption_raw = caption_raw[0].upper() + caption_raw[1:]

    # Deterministic (non-LLM) additions: water/love flavor words, the
    # fixed "Use Chatgpt/Gemini/Midjourney/grok..." + "Prompt in the
    # first comment" footer, capped at 280 words. The paste link below
    # is appended AFTER this, so it is never counted toward the cap.
    caption_raw = build_enhanced_caption(caption_raw)

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

    special_label = special_prompt_label(approved_ingredients)
    prompt_header = prompt_header.replace(
        f"#Prompt{prompt_id:04d} |",
        f"#Prompt{prompt_id:04d}{special_label} |",
        1,
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
    special_pattern_value = approved_ingredients.get("special_pattern")
    if special_pattern_value:
        ingredient_last_used[special_pattern_value] = now_iso
    state["ingredient_last_used"] = ingredient_last_used

    save_state(state)

    print(
        f"Posted #Prompt{prompt_id:04d}. "
        f"Image source: {image_source}. "
        f"Stored signatures: {len(state['used_signatures'])}"
    )


if __name__ == "__main__":
    main()
