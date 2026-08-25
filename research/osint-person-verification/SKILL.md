---
name: osint-person-verification
description: Verify a real person's identity and public footprint from a name plus anchor info — public/professional sources only, with an ethics gate. Covers name-collision disambiguation, cross-platform handle correlation, and platform-specific lookup recipes.
tags: [osint, research, verification, investigation]
triggers:
  - verify a person identity online
  - investigate an online persona or username
  - cross-referencing social profiles

---

# OSINT Person Verification (public footprint, ethical scope)

Use when the user asks to find/verify a person from a name: OSINT discovery templates, "find their Instagram", background checks, dating-app safety checks, verifying a business contact, or confirming a LinkedIn story. Works best with at least one anchor (profile paste, city, employer, school, event, project).

## Step 0 — Purpose gate (ALWAYS, before searching)

The OSINT template's "Context / Reason for Search" is often blank. Ask who the person is to the user and why, via clarify. Scope by the answer:

- Public figure / business contact / professional verification → map public professional presence (LinkedIn, company pages, news, event/project pages).
- Dating-app / personal trust check → verify the public story they told; flag inconsistencies. Public social profiles OK.
- Authorized work/security investigation → treat accordingly if the user says so.

**Never do, regardless of purpose**: email enumeration or breach lookups (HIBP, Hunter), reverse-image search on their photos, court/property/voter records aggregation, geolocation/check-in data, PimEyes. State this boundary explicitly up front. User's memory: "verification is the agent's job" — they expect the agent to run the search itself, not hand back homework.

## Step 1 — Anchor inventory

Extract anchors from whatever the user pasted/provided: full name, city, employer, school, program, event names, project names, teammate names, username hints. A pasted LinkedIn profile is an excellent anchor — verify its claims, don't re-derive them.

## Step 2 — Verify anchor claims independently

Every claim on a profile is checkable: does the school/program exist (with matching campus + start month)? Does the event exist (Devpost event page, event site)? Is the employer a real company in that city? Confirm what's independently verifiable; mark the rest (job history details) as plausible-but-unverified.

## Step 3 — Disambiguate: name collisions are the DEFAULT

Common names surface many unrelated people (often in a different country). Never merge them. Build a correlation chain instead:

1. Find a verifiable public artifact tying the name to the person (team roster, event gallery, project submission).
2. Roster/project pages link member profiles (Devpost, GitHub, etc.) → get their exact username.
3. Usernames are the golden thread: the same handle across platforms (Devpost + Instagram, GitHub + elsewhere) is the strongest non-photo signal. Also watch username *families* (e.g. `firstname-lastname-handle` + `firstname-lastname-handle`).
4. GitHub contributor lists on team repos reveal handles + commit counts that tie to roster members.
5. Check repos on the found GitHub account for content consistent with the claimed history (school project names, languages matching their stated skills).

Consistency checks: search-result counts of followers/connections drift across caches — not a red flag. A dormant account (posts years old, few followers) is plausibly the person's abandoned account; if they claim to be active there, THAT is the inconsistency to flag.

## Step 4 — Platform recipes

See platform-recipes.md for exact commands and gotchas (Devpost links scrape, GitHub API, Instagram logged-out browser flow, CDN image fetch, search-snippet mining).

Content-funnel / creator-account checks (Discord-promoting adult or gamer personas, "is this a scam" questions) have their own toolkit: Discord invite API + snowflake dating, Raider.IO game-identity verification, funnel risk mechanics. See social-funnel-verification.md.

## Step 5 — Report format

- WHAT CHECKS OUT — each item with an independent source URL.
- FLAGS / AMBIGUITY — name-collision warnings (list the lookalikes explicitly so they're not attributed), unverifiable claims, timeline gaps (neutral, not accusations).
- DELIBERATELY NOT DONE — restate the ethical boundary so the user knows the limits.
- BOTTOM LINE + residual check — the cheapest human check that settles what public sources can't (e.g. "ask her to demo the project / show the student portal"). Offer next public-side steps.

## Pitfalls

- Firecrawl refuses Instagram ("we do not support this site") — use the browser tool, not firecrawl_scrape.
- Devpost markdown scrape omits the team member links — request `formats: ["links"]` to get member profile URLs.
- Instagram logged-out: the login dialog blocks the view — click Close, then the AX snapshot shows display name, bio, follower counts, post dates, and the posts grid.
- `browser_get_images` returns direct `scontent-*.cdninstagram.com` URLs that curl CAN download even though the site is gated — save the profile pic locally so the user can compare faces themselves.
- GitHub API (repos/contributors/users) works unauthenticated with curl — no need for browser.
- Search engines index Instagram profile meta (followers, bio, pinned caption) — a plain `site:instagram.com "name"` search often confirms details before you even open the profile.
- X logged-out shows only ~1 recent tweet before the signup wall — characterize the rest via `site:x.com HANDLE` search snippets / firecrawl_search so you never load adult media into context.
- Don't conclude "scam" from funnel patterns alone (Discord-only monetization, fresh server, scripted bio). Verify the claimed identity against authoritative game/platform APIs FIRST — a real identity behind a risky funnel is a different verdict than a fake identity, and the user will (rightly) push back if you skip this.


## Reference: platform-recipes.md

# Platform recipes — person footprint lookups

Worked recipes from the [subject] verification ([hackathon] / [institution] case). All public-source only.

## Devpost (hackathon projects) — get team roster + member handles

- Project page: `https://devpost.com/software/<slug>`
- Scrape with `formats: ["links"]` (markdown output HIDES the team member links):
  ```
  firecrawl_scrape(url="https://devpost.com/software/<slug>", formats=["links"])
  ```
  The links array contains `https://devpost.com/<handle>` entries for every team member — these handles are the correlation goldmine (same user may reuse the handle on Instagram/GitHub).
- A member's portfolio page (`devpost.com/<handle>`) carries their display name + listed skills — compare against the person's claimed skills/languages to confirm identity.
- Event galleries: `https://<event>.devpost.com/project-gallery?page=N` lists project cards with team names (not always handles — the project page is the better source).
- Devpost project pages also link: live demo URLs (e.g. `[demo-domain]`), the team's GitHub repo, and the demo YouTube video.

## GitHub — contributor handles without auth

Unauthenticated GitHub API works fine for repos/contributors/users (rate-limited but ample for this):

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/contributors" | python3 -m json.tool
# → login, html_url, contributions per contributor
curl -s "https://api.github.com/users/<login>"          # → name, bio, location, public_repos, created_at
curl -s "https://api.github.com/users/<login>/repos?sort=updated"   # → repo names, languages, dates
```

Tricks:
- Contributor handles on a team repo tie roster names to GitHub identities; commit counts corroborate who did the work.
- A repo named with a first name (e.g. `StoreInventoryFirstname`) + language matching the person's stated coursework is corroboration.
- Username search: `curl -s "https://api.github.com/search/users?q=%22<full name>%22"` — often empty; handle-correlation beats name search.

## Instagram — logged-out profile view (Firecrawl refuses)

- firecrawl_scrape on instagram.com returns: "we do not support this site". Use the browser tool.
- `browser_navigate` to `https://www.instagram.com/<handle>/` → login dialog appears.
- Click Close on the dialog (`browser_click` on the Close button), then `browser_snapshot(full=true)`:
  - shows display name, follower/following counts, bio, story highlights, and dated post links ("Photo by <Name> on <date>")
  - click "Show more posts" if present; if the grid still shows only the same 3 posts, that IS the full public count.
- `browser_get_images` returns direct `scontent-<region>.cdninstagram.com` URLs (profile pic + post images). These download fine with plain curl despite the site being gated:
  ```bash
  curl -sL -o pfp.jpg "<cdn url>" && file pfp.jpg
  ```
  Save the profile pic + posts to a local folder and point the user at it — THEY can do the face comparison (do not reverse-image-search it yourself).
- Instagram profile URLs are also fetchable via `?__a=1` / `__d=1` only when logged in — don't rely on it.

## Search-engine mining of social profiles

- `firecrawl_search query="site:instagram.com \"<full name>\""` — indexed snippets often contain follower counts and the pinned post caption, confirming profile details before opening the site.
- Same pattern for `site:tiktok.com`, `site:facebook.com` — but beware: Facebook name tags (local business pages, school pages) surface OTHER people with the same name. Treat every hit as a separate person until correlated.
- Exa web_search works well for name + context queries ("<name> <city> <school> <project>") and indexes LinkedIn profile text.

## Name-collision handling

"[subject]" case: Instagram/TikTok/Facebook hits pointed at a different person in another city (school pages, food-seller tags). Rule: an account is only "the person" if a correlation chain connects it (same handle as a roster-linked profile, or consistent username family + matching display name). Otherwise list it under FLAGS as a lookalike and explicitly tell the user not to attribute it.


## Reference: social-funnel-verification.md

# Verifying content-funnel personas (Discord-promoting creators, "is this a scam" checks)

Use when the user asks whether a social account is a scam — especially adult-content + gaming personas that funnel to a Discord invite. Goal: verify which claims are REAL against authoritative sources, then assess the funnel's risk mechanics. A persona can be 100% real and still be a bad idea to engage with. Do NOT conclude "scam" from funnel patterns alone — verify the claimed identity first; the verdict differs completely between "fake identity, risky funnel" and "real identity, risky funnel".

## Evidence ladder (in order of decisiveness)

1. Authoritative account/character APIs (game stats, platform metadata)
2. Dates you can compute yourself (Discord snowflakes, server age)
3. Cross-platform name-family correlation (same handle on many sites = one person)
4. Template detection (persona script copy-pasted by other operators)
5. Text-level characterization via search snippets (never load adult media into context)

## Discord invite resolution (public API, no auth, no login)

    curl "https://discord.com/api/v9/invites/CODE?with_counts=true&with_expiration=true"

Returns: inviter (id, username, global_name), guild (id, name, nsfw, nsfw_level, verification_level, features), approximate_member_count, approximate_presence_count, premium_subscription_count, liveliness.

Snowflake → UTC timestamp: ((id >> 22) + 1420070400000) / 1000 s.
- guild.id → server creation date. A days-old server = shell; operators churn because Discord nukes adult servers constantly (fresh server is the norm for these, not suspicious per se).
- inviter.id → Discord account creation date (cross-check against claimed platform join dates).
- invite record id → when the invite was minted.

Reads: nsfw_level 3 + nsfw:true = adult server. premium_subscription_count 0 / no boosts = no community investment. Member verification gate is default tooling, NOT a signal.

Dead ends (don't waste calls): /guilds/{id}/widget.json → "Widget Disabled" usually; /guilds/{id}/preview → 401 without auth.

## WoW identity verification — Raider.IO public API (no auth)

    curl "https://raider.io/api/v1/characters/profile?region=us&realm=REALM&name=NAME&fields=class,active_spec_name,active_spec_role,guild,mythic_plus_scores_by_season:current,mythic_plus_previous_season_scores,mythic_plus_alternate_runs,mythic_plus_recent_runs"

Gotchas:
- Realm names with apostrophes: try both kel%27thuzad and kelthuzad.
- Unicode character names must be URL-encoded (Emmastraszã → Emmastrasz%C3%A3).
- Some runs lack completed_timestamp — parse defensively (KeyError otherwise).
- previous_season_scores empty + high current score = new toon/account this season; flag it, don't assume history.
- last_crawled_at = activity recency. guild None = guildless.
- Alternate runs list other toons on the same account (often empty unless the rio addon links them).
- Drustvar.com mirrors the same data; its search-result SNIPPETS show recent-run group composition (friend names often reveal nationality/cluster) even though /character/*/pve pages are JS-gated.

Interpretation (the decisive patterns):
- 3000+ M+ score = hundreds of hours of real play. Scammers don't grind this. Single strongest "real gamer" signal.
- UNDERSTATED claims (persona says 3250, API says 3473) = real-player signal. Scammers inflate; real players deflate (stale addon, modesty).
- Timezone in LFG posts (e.g. "8 AM CST") cross-checked against claimed location = consistency test.
- Same name family across WoW toons, op.gg LoL, YouTube = one person's handle family. Multiple healers on one realm sharing a naming scheme = a player's roster, not a fabricated alias.

## X/Twitter without API

- Logged-out browser view (x.com/handle) shows bio, join date, follower counts, one recent tweet, then the signup wall. Enough for metadata.
- Characterize the tweet stream WITHOUT visiting the profile: web_search site:x.com HANDLE and firecrawl_search "HANDLE" return tweet URLs + text snippets (including adult/PMV posts) — keeps explicit media out of context.
- Engagement-bait pattern: quote-posting popular meme accounts with low-effort captions = follower farming.

## Funnel risk mechanics (the actual answer users need)

- Discord-only funnel with NO OnlyFans/Fansly/Linktree/Telegram = no payment platform = unregulated payments (cashapp/venmo/crypto), zero chargeback or buyer protection. Real SW funnels to OF/Fansly for payment processing. This is the top scam tell, operator-independent.
- Scam vectors inside the funnel are operator-independent too: fake "age verification" links (Discord token grabbers → account theft + invite spam to the victim's friends), paid "customs" never delivered, sextortion via "DM to Play", malware links. A real operator can still host a compromised funnel: advise leaving the server, never clicking verify links, never paying outside regulated platforms.
- Template detection: search persona name/script phrases on server-listing sites (discodus.com, disboard.org). Identical scripts across differently-named servers ("Heyyy, my name is Emma, I game... I sell to make extra money") = mass-produced playbook. Template match proves the playbook, not the operator.
- Persona contradictions (flag vs location, "married" + explicit persona) are SCRIPT — taboo angles + authenticity theater, not evidence either way. Marriage claims are unverifiable and can be literal (married SW exists).
- Residual human test: offer the claimed concrete skill interaction (add on Battle.net, run a key, voice call). Real people do it in minutes; personas deflect or monetize the request.
- Report shape: WHAT CHECKS OUT (with authoritative receipts) / WHAT DOESN'T CHANGE (funnel mechanics) / residual test.

## Ethics (inherited from parent skill)

No reverse-image search on their photos, no breach/email enumeration, no geolocation of posts. State the boundary; the analysis never depends on it.
