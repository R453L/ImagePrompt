"""
Hourly AI-image-prompt generator + Telegram poster.

Flow:
  1. Pull the current list of FREE models from OpenRouter (never hardcoded).
  2. Stage 1: generate a brand-new, high-imagination prompt (with a hard
     "face/identity must stay locked to reference image" rule baked in),
     picking a random theme + subject-type to keep variety high and
     avoiding recent repeats (state/recent_prompts.json).
  3. Stage 2: self-review the generated prompt for cleanliness /
     professionalism / no ambiguity / face-lock present / not a near-dupe.
     Retries up to MAX_ATTEMPTS; if it never passes, the hour is skipped
     (no bad content is ever posted).
  4. Fetch a random base portrait photo (Pexels -> Pixabay -> Unsplash
     fallback chain).
  5. Post base image + prompt (raw, copy-ready, in a <code> block, with a
     bold hook kept OUTSIDE the code block so it never gets copied along
     with the prompt) to the PRIVATE Telegram channel.
  6. Update state/recent_prompts.json so the next run avoids repeats.

Required secrets (env vars):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID        (the PRIVATE channel's chat id, e.g. -100xxxxxxxxxx)
  OPENROUTER_API_KEY
  PEXELS_API_KEY
  PIXABAY_API_KEY
  UNSPLASH_ACCESS_KEY
"""

import os
import sys
import json
import random
import re
import time
from datetime import datetime, timezone

import requests

# ---------- config ----------

STATE_PATH = "state/recent_prompts.json"
RECENT_KEEP = 10
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = 60

MEDIUM_POOL = [
    "straight photorealistic photography",
    "ink/line-art hybrid blended into the photo",
    "graphite pencil sketch texture blended in",
    "3D-rendered collectible figurine / toy-in-box look",
    "bold typography-driven graphic poster layout",
    "mixed-media paper collage with torn edges and textures",
    "vintage analog film photography look",
    "surreal digital composite / impossible-scene photobash",
    "watercolor or gouache painted elements blended with the photo",
    "multi-panel contact-sheet grid of the same subject",
    "double-exposure style layered imagery",
    "claymation / stop-motion diorama look",
    "high-contrast black-and-white film-noir photography",
    "documentary/photojournalistic raw realism",
    "studio portrait photography with softbox lighting",
    "high-key photography (bright, minimal shadow)",
    "low-key photography (deep shadow, dramatic contrast)",
    "extreme macro photography with shallow focus",
    "aerial/drone top-down photography",
    "risograph-print poster aesthetic (limited flat color layers)",
    "screen-print / gig-poster aesthetic",
    "cyanotype (blueprint-blue) photographic aesthetic",
    "stained-glass illustration style",
    "mosaic / tile-art style",
    "origami paper-craft look",
    "pixel-art retro game aesthetic",
    "botanical-illustration engraving style",
    "long-exposure light-trail photography",
    "tintype / antique wet-plate photography look",
    "flat vector illustration, clean geometric shapes",
    "isometric illustration, no vanishing point",
    "charcoal and chalk mixed sketch",
    "embroidery / stitched-fabric texture look",
    "stop-motion felt/puppet diorama look",
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
    "eerie and unsettling (tasteful, not gory)",
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
    "awe-struck, sublime scale",
    "hopeful and optimistic",
    "brooding and intense",
    "innocent and curious",
    "confident and unbothered",
]

SETTING_POOL = [
    "a rain-soaked neon-lit city street at night",
    "an old dusty bookstore with towering shelves",
    "an abandoned greenhouse reclaimed by plants",
    "a floating platform above the clouds",
    "a cluttered vintage workshop lit by a single bulb",
    "an underwater ruin with shafts of light",
    "a snow-covered mountain overlook at dawn",
    "a retro roadside diner at 2am",
    "a night market full of paper lanterns",
    "a minimalist white void/studio with one surreal object",
    "a grand old train station with steam and light beams",
    "a rooftop garden overlooking a sprawling skyline",
    "a harbor fishing village at first light",
    "a foggy pier at low tide",
    "a jazz-club basement with warm low light",
    "an art-deco ballroom mid-renovation",
    "a carnival/funfair at night, lights blurring",
    "an ice cave with blue ambient light",
    "a cliffside lighthouse in a storm",
    "a mountain monastery courtyard",
    "a rooftop infinity pool at dusk",
    "a botanical conservatory full of glass and steam",
    "an abandoned drive-in cinema at dusk",
    "a desert canyon at golden hour",
    "an orchard in full bloom",
    "an artist's cluttered loft studio",
    "a backstage opera corridor",
    "a vineyard at harvest, warm dust in the air",
    "a quiet subway platform, one train blurring past",
    "a terraced rice field seen from directly above",
]

TWIST_POOL = [
    "an object in the scene defies gravity or physics",
    "the subject's shadow does something the subject isn't doing",
    "one element of the scene is rendered in a completely different art style than the rest",
    "a burst of a single vivid color cuts through an otherwise muted/monochrome scene",
    "an animal or creature appears in an unexpected, symbolic way",
    "the scale of something in the scene is wildly exaggerated (tiny or giant)",
    "part of the scene appears to be dissolving, melting, or made of an unexpected material",
    "a reflection (mirror, water, glass) shows something different from reality",
    "light comes from an impossible or unidentifiable source",
    "time-of-day or season is deliberately mismatched between foreground and background",
    "the subject seems to be interacting with an echo of their own past or future self",
    "only one object in the frame stays in perfect focus while everything else dissolves away",
    "gravity visibly runs sideways for a single element",
    "the color palette inverts for exactly one object in the scene",
    "a swarm of tiny lights/fireflies subtly forms a recognizable shape",
    "the image looks like it's torn, revealing a different scene underneath",
    "unusual localized weather happens only in a small radius around the subject",
    "a clock, calendar, or other time-marker in the scene shows something impossible",
    "an everyday small object appears at impossible architectural scale",
    "the subject appears doubled or mirrored in a way that shouldn't be physically possible",
]

CAMERA_POOL = [
    "golden-hour backlight with soft lens flare",
    "blue-hour ambient city glow",
    "long-exposure light trails",
    "extreme macro with paper-thin depth of field",
    "aerial drone top-down framing",
    "tilt-shift miniature effect",
    "handheld documentary motion and grain",
    "medium-format square crop with creamy bokeh",
    "infrared/thermal color-shifted palette",
    "vintage film grain with subtle light leaks",
    "wide-angle low-angle perspective for a powerful stance",
    "85mm portrait compression, shallow depth of field",
    "high dynamic range with crisp micro-contrast",
    "soft diffused overcast-day lighting",
    "harsh single hard-light source with deep shadow",
]

SUBJECT_POOL = [
    {
        "label": "a solo person (selfie/candid style)",
        "queries": ["professional portrait photography person",
                    "natural candid portrait photography woman",
                    "natural candid portrait photography man",
                    "high quality lifestyle portrait photography"],
    },
    {
        "label": "a couple together",
        "queries": ["professional couple portrait photography",
                    "candid couple photography smiling"],
    },
    {
        "label": "a person with their pet",
        "queries": ["professional portrait photography person with dog",
                    "professional portrait photography person with cat",
                    "lifestyle photography woman with dog",
                    "lifestyle photography man with dog"],
    },
    {
        "label": "a small family/group",
        "queries": ["professional family portrait photography studio",
                    "candid family photography outdoors"],
    },
    {
        "label": "a person in an everyday candid moment",
        "queries": ["candid lifestyle photography person",
                    "documentary style candid portrait photography"],
    },
]

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
OPENROUTER_API = "https://openrouter.ai/api/v1"

HARD_RULE = (
    "Non-negotiable rule that must appear in every prompt: the person's "
    "face, facial features, skin tone and identity must be preserved "
    "exactly as shown in the uploaded reference image — strict identity "
    "lock, no exceptions."
)


def env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"::error::Missing required secret/env var: {name}")
        sys.exit(1)
    return val


# ---------- state (repetition avoidance) ----------

def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"recent": []}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def next_id(state: dict) -> int:
    return state.get("last_id", 0) + 1


# ---------- OpenRouter: dynamic free-model selection ----------

def get_free_models(api_key: str) -> list:
    r = requests.get(
        f"{OPENROUTER_API}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    free = []
    for m in data:
        pricing = m.get("pricing", {})
        try:
            prompt_cost = float(pricing.get("prompt", "1") or "1")
            completion_cost = float(pricing.get("completion", "1") or "1")
        except ValueError:
            continue
        if prompt_cost == 0 and completion_cost == 0:
            free.append(m["id"])
    random.shuffle(free)
    return free


def call_openrouter(api_key: str, free_models: list, messages: list,
                     max_tokens: int = 900) -> str:
    """Try free models one by one until one responds successfully."""
    last_err = None
    for model_id in free_models:
        try:
            r = requests.post(
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
            if r.status_code != 200:
                last_err = f"{model_id} -> HTTP {r.status_code}: {r.text[:200]}"
                continue
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            if content and content.strip():
                print(f"Used free model: {model_id}")
                return content.strip()
            last_err = f"{model_id} -> empty response"
        except Exception as e:
            last_err = f"{model_id} -> {e}"
            continue
    raise RuntimeError(f"All free models failed. Last error: {last_err}")


# ---------- Stage 1: generate ----------

GEN_MARKERS = ["HOOK", "PROMPT", "APP", "THEME_USED", "CAPTION"]
REVIEW_MARKERS = ["VERDICT", "REASON"]
LINK_TOKEN = "[PROMPT_LINK]"


def build_generation_messages(recent_summaries: list, medium: str, mood: str,
                               setting: str, twist: str, camera: str, subject: str) -> list:
    recent_block = (
        "\n".join(f"- {s}" for s in recent_summaries)
        if recent_summaries else "(none yet)"
    )
    system = f"""You are an elite AI-image-prompt creative director for a Telegram
channel. Your job: invent a brand-new, extremely imaginative, highly
detailed AI-image-generation prompt (for tools like GPT Image, Gemini
image, Midjourney-style apps) that a viewer can copy, paste into an AI
app together with their OWN photo, and get a professional, polished,
scroll-stopping result.

{HARD_RULE}

Additional hard rules:
- NEVER specify or invent the reference person's gender, age, or
  ethnicity anywhere in the prompt text (e.g. do NOT write "a young
  woman", "a man in his 40s", etc.) — a real base photo of UNKNOWN
  gender/age/ethnicity will be attached to this prompt, so any invented
  demographic detail can directly contradict the actual photo. Instead
  refer to them neutrally: "the person from the reference image", "they
  / their", or similar. All other details (clothing, pose, setting,
  style, mood) can be as specific and imaginative as you like.
- NEVER name or depict a real celebrity, public figure, or real trademarked
  brand/logo/franchise (e.g. no real magazine names, no real sports team or
  sponsor logos, no real band/movie/character IP). If inspired by such an
  aesthetic, describe it generically instead (e.g. "a vintage rock concert
  poster look" instead of naming a real band; "a glossy fashion-magazine
  cover layout" instead of a real magazine's name).
- For the identity-lock instruction, you may use strong, explicit,
  non-negotiable phrasing (even ALL-CAPS emphasis on key words like FACE,
  IDENTITY, PRESERVE) when it fits the prompt's tone — this level of
  emphasis measurably improves how well AI image apps keep the person's
  real face.

Hard requirements for the prompt text you write:
- Extremely detailed, professional, unambiguous, production-quality
  (rival the best commercial AI-art prompts).
- Include composition/aspect ratio, lighting, style/medium, mood, and a
  short negative-prompt section.
- Must be copy-paste ready: clean prose, no markdown symbols, no
  placeholders like [X] left unfilled.
- Must feel completely original — do NOT repeat or lightly reword any
  idea from the recent prompts list below.
- Your own imagination is the primary source, not any hint given below.
  Invent concepts, mediums, formats, and visual metaphors nobody has
  suggested to you. Combine unrelated ideas, invent new visual formats,
  reference art movements, photography styles, or storytelling devices
  freely.

Recently used prompt concepts (avoid repeating these ideas):
{recent_block}

Raw creative ingredients (these are NOT a named theme to reproduce
literally — they are independent raw material for YOU to reinterpret,
remix, subvert, or combine in an unexpected way; use as much or as
little of each as genuinely sparks a good original idea, and feel free
to override any of them if a better original direction emerges):
- medium/technique spark: {medium}
- mood spark: {mood}
- setting spark: {setting}
- unexpected-twist spark: {twist}
- camera/lens spark: {camera}
Do not just describe these four things literally back-to-back — use
them as a starting spark and then invent your own specific, surprising
concept on top of them.

Required subject constraint (this one must be followed — it determines
which real base photo gets paired with your prompt, so the prompt must
genuinely feature this subject type, though you're free to invent
anything about the setting/style/story around them):
- subject: {subject}

Do NOT show your reasoning or thinking process, and do NOT use JSON.
Output ONLY the final answer, starting immediately with ===HOOK===, in
EXACTLY this plain-text format, with each marker on its own line,
nothing before ===HOOK=== and nothing after the last field:

===HOOK===
short punchy bold-worthy caption, max 8 words
===PROMPT===
the full clean copy-paste-ready AI image prompt text (can be several
sentences/paragraphs, no markdown symbols)
===APP===
one short line naming which AI app/tool this prompt works best on
===THEME_USED===
short label for the theme/style used
===CAPTION===
a short (1-2 sentence) social-media caption for X/Twitter, written the
way a real person casually posting a cool AI-art result would write it
— NOT a formal instruction, NOT "Best on: X app" style, and NOT written
as a personal narrative about the poster's own life (this account
posts results using photos of many different people, never the
poster's own face or story). Rules:
- NEVER use "I", "we", "my", "our", "us" — describe the image/result
  itself, not a personal experience (e.g. "This turned into a moody
  noir portrait" not "I turned my photo into...").
- Naturally mention which AI app/tool gives the best result, as a
  casual aside (e.g. "works great on GPT Image 2").
- Include 1 to 3 fitting emoji, placed naturally (not one after every
  word).
- Avoid dashes almost entirely. NEVER use a double hyphen "--" or an
  em dash "—" anywhere (a dead giveaway of AI-generated text) — use
  periods or commas instead. At most one single hyphen in the entire
  caption, only if truly natural.
- Do NOT include any link or the words "full prompt" — that line is
  added separately afterward, so the caption must read as complete
  and correct on its own without it.
- Keep it warm, casual, a little excited, never robotic."""
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Generate one new prompt now."}]


def parse_delimited(text: str, markers: list) -> dict:
    """Robustly extract marker=>value blocks from free-form model output.
    Tolerant of extra prose before/after, markdown fences, and models that
    forget a trailing marker (last field just runs to the end)."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    positions = []
    for m in markers:
        match = re.search(rf"===\s*{re.escape(m)}\s*===", text)
        if match:
            positions.append((match.start(), match.end(), m))
    if not positions:
        raise ValueError(f"No known markers found in model output: {text[:300]}")
    positions.sort(key=lambda p: p[0])

    result = {}
    for i, (start, end, name) in enumerate(positions):
        value_start = end
        value_end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        result[name.lower()] = text[value_start:value_end].strip()

    missing = [m for m in markers if m.lower() not in result or not result[m.lower()]]
    if missing:
        raise ValueError(f"Missing/empty fields {missing} in model output: {text[:300]}")
    return result


# ---------- Stage 2: self-review ----------

def build_review_messages(candidate: dict, recent_summaries: list) -> list:
    recent_block = (
        "\n".join(f"- {s}" for s in recent_summaries)
        if recent_summaries else "(none yet)"
    )
    system = f"""You are a strict quality reviewer for AI-image-generation
prompts that will be published to a public audience.

Review the CANDIDATE prompt below against these rules:
1. It must explicitly preserve the reference-image face/identity
   (strict identity lock) — reject if missing or weak.
2. It must be clean, professional, unambiguous, copy-paste ready
   (no leftover placeholders, no markdown symbols, no broken sentences).
3. It must describe a result that a general AI image app can plausibly
   produce (not physically/logically nonsensical).
4. It must be meaningfully different from these recent concepts:
{recent_block}
5. It must NOT invent or specify the reference person's gender, age, or
   ethnicity anywhere (e.g. "a young woman", "an elderly man") — reject
   if any such demographic detail appears; it should say "the person
   from the reference image" or similar neutral phrasing instead.
6. It must NOT name or depict any real celebrity, public figure, or real
   trademarked brand/logo/franchise — reject if any real name/brand
   appears (generic/fictional equivalents are fine).
7. The CANDIDATE CAPTION must sound like a real person casually wrote
   it (not robotic/formal, not "Best on: X app" style), must naturally
   mention an AI app recommendation, must contain at least one emoji,
   must NOT use "I"/"we"/"my"/"our"/"us", must NOT contain a double
   hyphen "--" or an em dash "—", and must NOT mention a link or "full
   prompt" — reject if any of these are violated.

CANDIDATE HOOK: {candidate.get('hook', '')}
CANDIDATE PROMPT: {candidate.get('prompt', '')}
CANDIDATE CAPTION: {candidate.get('caption', '')}

Do NOT show your reasoning or thinking process. Do NOT use JSON. Output
ONLY the final answer, starting immediately with ===VERDICT===, in
EXACTLY this plain-text format:

===VERDICT===
APPROVE or REVISE
===REASON===
short reason (one sentence)"""
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Review it now."}]


# ---------- base image fetch (Pexels -> Pixabay -> Unsplash) ----------

def fetch_from_pexels(api_key: str, query: str):
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": 15, "orientation": "portrait"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError("Pexels: no results")
    # bias toward the most relevant results (API returns best matches first)
    top_photos = photos[:8] if len(photos) > 8 else photos
    photo = random.choice(top_photos)
    url = photo["src"]["large"]
    img = requests.get(url, timeout=REQUEST_TIMEOUT)
    img.raise_for_status()
    return img.content, "Pexels"


def fetch_from_pixabay(api_key: str, query: str):
    def _search(editors_choice: bool):
        params = {
            "key": api_key, "q": query, "image_type": "photo",
            "orientation": "vertical", "category": "people", "per_page": 20,
            "order": "popular",
        }
        if editors_choice:
            params["editors_choice"] = "true"
        r = requests.get("https://pixabay.com/api/", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json().get("hits", [])

    # prefer hand-picked high-quality (editors_choice) results first
    hits = _search(editors_choice=True)
    if not hits:
        hits = _search(editors_choice=False)
    if not hits:
        raise RuntimeError("Pixabay: no results")
    top_hits = hits[:8] if len(hits) > 8 else hits
    hit = random.choice(top_hits)
    url = hit["largeImageURL"]
    img = requests.get(url, timeout=REQUEST_TIMEOUT)
    img.raise_for_status()
    return img.content, "Pixabay"


def fetch_from_unsplash(access_key: str, query: str):
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {access_key}"},
        params={"query": query, "per_page": 20, "orientation": "portrait",
                "order_by": "relevant"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError("Unsplash: no results")
    top_results = results[:8] if len(results) > 8 else results
    result = random.choice(top_results)
    url = result["urls"]["regular"]
    img = requests.get(url, timeout=REQUEST_TIMEOUT)
    img.raise_for_status()
    return img.content, "Unsplash"


def fetch_base_image(pexels_key, pixabay_key, unsplash_key, queries: list):
    query = random.choice(queries)
    for fn, key in (
        (fetch_from_pexels, pexels_key),
        (fetch_from_pixabay, pixabay_key),
        (fetch_from_unsplash, unsplash_key),
    ):
        try:
            return fn(key, query)
        except Exception as e:
            print(f"Base image source failed ({fn.__name__}, query='{query}'): {e}")
            continue
    raise RuntimeError("All base-image sources failed.")


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
            # request the raw/plain view so it opens as clean text
            return url.rstrip("/") + ".txt"
        return ""
    except Exception as e:
        print(f"Paste link creation failed (non-fatal): {e}")
        return ""


# ---------- Telegram ----------

def telegram_send_photo(token: str, chat_id: str, image_bytes: bytes,
                         caption_html: str) -> None:
    r = requests.post(
        TELEGRAM_API.format(token=token, method="sendPhoto"),
        data={"chat_id": chat_id, "caption": caption_html, "parse_mode": "HTML"},
        files={"photo": ("base.jpg", image_bytes)},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()


def telegram_send_message(token: str, chat_id: str, text_html: str) -> None:
    r = requests.post(
        TELEGRAM_API.format(token=token, method="sendMessage"),
        data={"chat_id": chat_id, "text": text_html, "parse_mode": "HTML"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()


def escape_html(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------- main ----------

def main():
    tg_token = env("TELEGRAM_BOT_TOKEN")
    tg_chat = env("TELEGRAM_CHAT_ID")
    openrouter_key = env("OPENROUTER_API_KEY")
    pexels_key = env("PEXELS_API_KEY")
    pixabay_key = env("PIXABAY_API_KEY")
    unsplash_key = env("UNSPLASH_ACCESS_KEY")

    state = load_state()
    recent_summaries = [item["summary"] for item in state.get("recent", [])]

    free_models = get_free_models(openrouter_key)
    if not free_models:
        print("::error::No free models currently available on OpenRouter.")
        sys.exit(1)
    print(f"Found {len(free_models)} free models.")

    approved = None
    approved_subject = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        medium = random.choice(MEDIUM_POOL)
        mood = random.choice(MOOD_POOL)
        setting = random.choice(SETTING_POOL)
        twist = random.choice(TWIST_POOL)
        camera = random.choice(CAMERA_POOL)
        subject = random.choice(SUBJECT_POOL)
        print(f"Attempt {attempt}: medium='{medium}' mood='{mood}' "
              f"setting='{setting}' twist='{twist}' camera='{camera}' "
              f"subject='{subject['label']}'")

        try:
            gen_raw = call_openrouter(
                openrouter_key, free_models,
                build_generation_messages(recent_summaries, medium, mood,
                                           setting, twist, camera, subject["label"]),
                max_tokens=4000,
            )
            candidate = parse_delimited(gen_raw, GEN_MARKERS)

            review_raw = call_openrouter(
                openrouter_key, free_models,
                build_review_messages(candidate, recent_summaries),
                max_tokens=1200,
            )
            review = parse_delimited(review_raw, REVIEW_MARKERS)
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            continue

        if review.get("verdict", "").strip().upper().startswith("APPROVE"):
            approved = candidate
            approved_subject = subject
            break
        else:
            print(f"Rejected: {review.get('reason')}")

    if not approved:
        print("No prompt passed review this hour — skipping post (fail-safe).")
        return

    # fetch base image matching the same subject type as the approved prompt
    try:
        image_bytes, source = fetch_base_image(
            pexels_key, pixabay_key, unsplash_key, approved_subject["queries"]
        )
    except Exception as e:
        print(f"::error::Could not fetch a base image, skipping post: {e}")
        return

    pid = next_id(state)
    hook = escape_html(approved.get("hook", "").strip())
    prompt_text = approved.get("prompt", "").strip()
    app_rec = escape_html(approved.get("app", "").strip())
    theme_used = approved.get("theme_used", "").strip()
    caption_raw = approved.get("caption", "").strip()

    paste_url = create_paste_link(prompt_text)

    if paste_url:
        social_caption = f"{caption_raw}\n\nFull prompt here: {paste_url}"
    else:
        social_caption = caption_raw

    caption_html = f"<b>{hook}</b>\n#Prompt{pid:04d}"
    prompt_message_html = (
        f"#Prompt{pid:04d} | Best on: {app_rec}\n\n"
        f"<code>{escape_html(prompt_text)}</code>"
    )
    social_caption_html = (
        f"#Prompt{pid:04d} social caption (tap to copy, ready for X/Twitter):\n\n"
        f"<code>{escape_html(social_caption)}</code>"
    )

    telegram_send_photo(tg_token, tg_chat, image_bytes, caption_html)
    telegram_send_message(tg_token, tg_chat, prompt_message_html)
    telegram_send_message(tg_token, tg_chat, social_caption_html)
    print(f"Posted #Prompt{pid:04d} (base image source: {source}).")

    # update state
    recent = state.get("recent", [])
    recent.append({
        "id": pid,
        "summary": f"[{theme_used}] {approved.get('hook', '')}".strip(),
        "posted_at": datetime.now(timezone.utc).isoformat(),
    })
    state["recent"] = recent[-RECENT_KEEP:]
    state["last_id"] = pid
    save_state(state)


if __name__ == "__main__":
    main()
