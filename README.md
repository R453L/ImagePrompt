# Telegram AI-Prompt Bot

প্রতি ঘণ্টায় GitHub Actions স্বয়ংক্রিয়ভাবে চলবে, নতুন একটা AI-image-generation
prompt বানাবে, Tiyashi-র একটা বেস রেফারেন্স ছবিসহ তোমার প্রাইভেট Telegram
চ্যানেলে পোস্ট করবে।

## সেটআপ (এক বারই করতে হবে)

### ১. GitHub-এ রিপো বানানো
1. github.com-এ লগইন করে **New repository** ক্লিক করো
2. নাম দাও, **Private** সিলেক্ট করো, Create করো
3. এই ফোল্ডারের সবকিছু সেই রিপোতে আপলোড করো — বিশেষভাবে খেয়াল রেখো:
   - `generate_and_post.py`
   - `requirements.txt`
   - `.github/workflows/hourly-prompt.yml` (এই সাবফোল্ডার স্ট্রাকচার ঠিক রেখো)
   - `state/recent_prompts.json`
   - **`reference_photos/` পুরো ফোল্ডার (Tiyashi-র ১০৫টা ছবি)** — এগুলোই
     এখন base image হিসেবে ব্যবহার হবে, কোনো বাইরের স্টক-ফটো API লাগবে না

### ২. Secrets যোগ করা
রিপোর ভেতরে যাও: **Settings → Secrets and variables → Actions →
New repository secret**

নিচের ৩টা secret যোগ করো (আগে ৬টা লাগত, এখন Tiyashi-র নিজস্ব ছবি
ব্যবহার হওয়ায় Pexels/Pixabay/Unsplash আর দরকার নেই):

| Secret নাম | কোথা থেকে পাবে |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather |
| `TELEGRAM_CHAT_ID` | তোমার প্রাইভেট চ্যানেলের chat id (নিচে দেখো) |
| `OPENROUTER_API_KEY` | openrouter.ai → Keys — একাধিক key থাকলে কমা দিয়ে একসাথে বসাও (যেমন `key1,key2,key3`); প্রতি রানে র‍্যান্ডমভাবে একটা বেছে নেওয়া হবে |

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
   Tiyashi-র একটা ছবি + প্রম্পট + সোশ্যাল ক্যাপশন পোস্ট হওয়ার কথা

### এরপর থেকে
GitHub Actions প্রতি ঘণ্টায় নিজে থেকেই চলবে (`:07` মিনিটে, UTC —
BD সময়ের সাথে +6 ঘণ্টা যোগ করে হিসাব করো)। প্রতিবার রান শেষে
`state/recent_prompts.json` আপডেট হয়ে repo-তে commit হয়ে যাবে —
এটাই repetition এড়ানোর মেমোরি (কোন ingredient কবে ব্যবহার হয়েছে,
temporal-decay ওজন-হ্রাসের জন্য)।

### cron-job.org ব্যাকআপ ট্রিগার (মূল রিলায়েবিলিটির অংশ, বাধ্যতামূলক)
GitHub মাঝেমধ্যে ব্যস্ত সময়ে নিজের schedule মিস করে। এর সমাধানে
cron-job.org থেকে জোর করে workflow ট্রিগার করানো হয় — এটা ইতিমধ্যে
সেটআপ করা আছে, workflow-এর `repository_dispatch` ট্রিগারের সাথে যুক্ত।

## যদি কোনো রান ফেইল/স্কিপ হয়
- Actions ট্যাবে লাল ❌ দেখলে, সেই রানে ক্লিক করে লগ দেখো
- "No prompt passed review this hour" লেখা থাকলে সেটা bug না —
  fail-safe কাজ করেছে (দুর্বল প্রম্পট বা wow-factor কম থাকায় পোস্ট
  হয়নি), পরের ঘণ্টায় আবার চেষ্টা হবে
- "skipping to avoid a duplicate post" লেখা থাকলে সেটাও স্বাভাবিক —
  native schedule আর backup trigger একসাথে ফায়ার করেছিল, ডুপ্লিকেট
  পোস্ট আটকানো হয়েছে
