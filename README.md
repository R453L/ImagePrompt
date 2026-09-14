# Telegram AI-Prompt Bot

প্রতি ঘণ্টায় GitHub Actions স্বয়ংক্রিয়ভাবে চলবে, নতুন একটা AI-image-generation
prompt বানাবে, একটা বেস পোর্ট্রেট ইমেজসহ তোমার প্রাইভেট Telegram চ্যানেলে
পোস্ট করবে।

## সেটআপ (এক বারই করতে হবে)

### ১. GitHub-এ রিপো বানানো
1. github.com-এ লগইন করে **New repository** ক্লিক করো
2. নাম দাও (যেমন `telegram-prompt-bot`), **Private** সিলেক্ট করো, Create করো
3. এই ফোল্ডারের সবগুলো ফাইল/ফোল্ডার (`generate_and_post.py`,
   `requirements.txt`, `.github/workflows/hourly-prompt.yml`,
   `state/recent_prompts.json`) সেই রিপোতে আপলোড করো
   (রিপো পেজে **Add file → Upload files** দিয়ে ড্র্যাগ-ড্রপ করলেই হবে —
   ফোল্ডার স্ট্রাকচার ঠিক রেখো, `.github/workflows/` ভেতরেই
   `hourly-prompt.yml` থাকতে হবে)

### ২. Secrets যোগ করা
রিপোর ভেতরে যাও: **Settings → Secrets and variables → Actions →
New repository secret**

নিচের ৬টা secret একে একে যোগ করো (নাম হুবহু মিলিয়ে):

| Secret নাম | কোথা থেকে পাবে |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather |
| `TELEGRAM_CHAT_ID` | তোমার প্রাইভেট চ্যানেলের chat id (নিচে দেখো) |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys |
| `PEXELS_API_KEY` | pexels.com/api |
| `PIXABAY_API_KEY` | pixabay.com/api/docs |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers |

**Chat ID বের করার উপায়:** বটকে প্রাইভেট চ্যানেলে admin বানানোর পর,
চ্যানেলে যেকোনো একটা মেসেজ পাঠাও, তারপর ব্রাউজারে এই লিঙ্ক খোলো
(টোকেন বসিয়ে):
`https://api.telegram.org/bot<TOKEN>/getUpdates`
রেসপন্সে `"chat":{"id": -100XXXXXXXXXX, ...}` — এই নেগেটিভ নম্বরটাই
`TELEGRAM_CHAT_ID`।

### ৩. টেস্ট রান
1. রিপোর **Actions** ট্যাবে যাও
2. বাঁ পাশে **Hourly AI Prompt Generator** ওয়ার্কফ্লো সিলেক্ট করো
3. **Run workflow** বাটনে ক্লিক করো (ম্যানুয়াল ট্রিগার)
4. রান শেষ হলে (সবুজ ✅ চেকমার্ক) তোমার প্রাইভেট চ্যানেল চেক করো —
   বেস ইমেজ + প্রম্পট পোস্ট হয়ে যাওয়ার কথা

### এরপর থেকে
কিছু করতে হবে না — GitHub Actions প্রতি ঘণ্টায় নিজে থেকেই চলবে (UTC
সময় অনুযায়ী, BD সময়ের সাথে +6 ঘণ্টা যোগ করে হিসাব করো)। প্রতিবার
রান শেষে `state/recent_prompts.json` ফাইল আপডেট হয়ে repo-তে commit
হয়ে যাবে — এটাই repetition এড়ানোর মেমোরি।

## যদি কোনো রান ফেইল/স্কিপ হয়
- Actions ট্যাবে লাল ❌ দেখলে, সেই রানে ক্লিক করে লগ দেখো — কোন
  secret ভুল বা কোন API down ছিল বোঝা যাবে
- "No prompt passed review this hour" লেখা থাকলে সেটা bug না —
  fail-safe কাজ করেছে (দুর্বল প্রম্পট পোস্ট হয়নি), পরের ঘণ্টায় আবার
  চেষ্টা হবে
