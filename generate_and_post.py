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

THEME_POOL = [
    "mixed-media doodle/shadow portrait",
    "editorial Polaroid-style double portrait",
    "premium product/commercial storyboard",
    "minimalist hand-drawn doodle illustration of a scene",
    "cinematic photorealistic selfie/candid portrait",
    "two-panel photo + minimal ink vignette poster",
    "luxury travel poster built around a photo",
    "brand/creative-agency style identity showcase",
    "photo + tiny ink-doodle storytelling poster",
    "high-fashion editorial B&W cinematic portrait",
    "vintage film / analog nostalgic portrait",
    "surreal fantasy composite built from a real photo",
]

SUBJECT_POOL = [
    {
        "label": "a solo person (selfie/candid style)",
        "queries": ["portrait face", "smiling person portrait",
                    "young woman portrait", "young man portrait"],
    },
    {
        "label": "a couple together",
        "queries": ["couple portrait", "couple smiling together"],
    },
    {
        "label": "a person with their pet",
        "queries": ["person with dog portrait", "person with cat portrait",
                     "woman with dog", "man with dog"],
    },
    {
        "label": "a small family/group",
        "queries": ["family portrait", "family photo studio"],
    },
    {
        "label": "a person in an everyday candid moment",
        "queries": ["candid portrait", "candid photo person"],
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

GEN_MARKERS = ["HOOK", "PROMPT", "APP", "THEME_USED"]
REVIEW_MARKERS = ["VERDICT", "REASON"]


def build_generation_messages(recent_summaries: list, theme: str, subject: str) -> list:
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

Hard requirements for the prompt text you write:
- Extremely detailed, professional, unambiguous, production-quality
  (rival the best commercial AI-art prompts).
- Include composition/aspect ratio, lighting, style/medium, mood, and a
  short negative-prompt section.
- Must be copy-paste ready: clean prose, no markdown symbols, no
  placeholders like [X] left unfilled.
- Must feel completely original — do NOT repeat or lightly reword any
  idea from the recent prompts list below.

Recently used prompt concepts (avoid repeating these ideas):
{recent_block}

Loosely use this theme as inspiration: {theme}
Loosely use this subject type as inspiration: {subject}
(You may reinterpret these freely — prioritize originality over sticking
to them literally.)

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
short label for the theme/style used"""
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

CANDIDATE HOOK: {candidate.get('hook', '')}
CANDIDATE PROMPT: {candidate.get('prompt', '')}

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
    photo = random.choice(photos)
    url = photo["src"]["large"]
    img = requests.get(url, timeout=REQUEST_TIMEOUT)
    img.raise_for_status()
    return img.content, "Pexels"


def fetch_from_pixabay(api_key: str, query: str):
    r = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": api_key, "q": query, "image_type": "photo",
            "orientation": "vertical", "category": "people", "per_page": 20,
        },
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    hits = r.json().get("hits", [])
    if not hits:
        raise RuntimeError("Pixabay: no results")
    hit = random.choice(hits)
    url = hit["largeImageURL"]
    img = requests.get(url, timeout=REQUEST_TIMEOUT)
    img.raise_for_status()
    return img.content, "Pixabay"


def fetch_from_unsplash(access_key: str, query: str):
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {access_key}"},
        params={"query": query, "per_page": 20, "orientation": "portrait"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError("Unsplash: no results")
    result = random.choice(results)
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
        theme = random.choice(THEME_POOL)
        subject = random.choice(SUBJECT_POOL)
        print(f"Attempt {attempt}: theme='{theme}' subject='{subject['label']}'")

        try:
            gen_raw = call_openrouter(
                openrouter_key, free_models,
                build_generation_messages(recent_summaries, theme, subject["label"]),
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

    paste_url = create_paste_link(prompt_text)

    caption_html = f"<b>{hook}</b>\n#Prompt{pid:04d}"
    paste_line = f"\nShare link (for X/Twitter): {escape_html(paste_url)}\n" if paste_url else "\n"
    prompt_message_html = (
        f"#Prompt{pid:04d} | Best on: {app_rec}\n"
        f"{paste_line}\n"
        f"<code>{escape_html(prompt_text)}</code>"
    )

    telegram_send_photo(tg_token, tg_chat, image_bytes, caption_html)
    telegram_send_message(tg_token, tg_chat, prompt_message_html)
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
