---
name: browser-privacy-hardening
description: "Harden Firefox (and Chromium-based) browsers for privacy: about:config prefetch/network prefs, uBlock Origin interaction bugs, DNS-over-HTTPS layering (Firefox TRR vs OS-level), ECH, Early Hints bypass, arkenfox alignment. Use when the user asks about browser privacy settings, prefetching, DNS leaks past adblockers, about:config hardening, or DoH/DoT setup."
tags: [firefox, privacy, dns, doh, ublock, arkenfox, prefetch, networking]
triggers:
  - browser privacy settings
  - DNS leaks past adblockers
  - about:config hardening or DoH setup

---

# Browser Privacy Hardening

## When to load this skill

- User asks about Firefox about:config privacy settings
- User asks about prefetching, preconnect, or speculative loading
- User uses uBlock Origin and wants to know what it does/doesn't control
- User asks about DNS-over-HTTPS setup (Firefox TRR vs OS-level)
- User asks about arkenfox user.js alignment
- User mentions "DNS leaks", "prefetch bypasses adblocker", or "Early Hints"
- User asks about resist fingerprinting (RFP), fingerprinting protection (FPP), or why a browser keeps hitting Cloudflare captchas

## Firefox prefetch surface area

Firefox has multiple independent prefetch/preconnect mechanisms. ETP Strict mode does NOT touch any of them. Each must be manually verified in about:config.

### Pref categories (least to most leaky)

| Mechanism | Pref | Default | What it does |
|-----------|------|---------|--------------|
| DNS prefetch (HTTP) | `network.dns.disablePrefetch` | false | Resolves domain names for links on HTTP pages |
| DNS prefetch (HTTPS) | `network.dns.disablePrefetchFromHTTPS` | true | Resolves domain names for links on HTTPS pages |
| Link prefetch | `network.prefetch-next` | true | Fetches full HTML of linked pages in background |
| Preconnect (hover) | `network.http.speculative-parallel-limit` | 6 | Opens TCP+TLS to domains when hovering links |
| Preconnect (HTML) | `network.preconnect` | true | `<link rel=preconnect>` from page HTML |
| Early Hints preconnect | `network.early-hints.preconnect.enabled` | true | 103 Early Hints server-driven preconnect |
| Address bar preconnect | `browser.urlbar.speculativeConnect.enabled` | true | Pre-connects to predicted site from address bar |
| Bookmark preconnect | `browser.places.speculativeConnect.enabled` | true | Pre-connects on bookmark hover |

### Pref hierarchy (critical to understand)

- `network.dns.disablePrefetch` is a **master switch**. When true, it overrides `network.dns.disablePrefetchFromHTTPS` and the `dom.prefetch_dns_for_anchor_*` prefs.
- `network.dns.disablePrefetchFromHTTPS` controls only `rel="dns-prefetch"` HTML hints on HTTPS pages and `dom.prefetch_dns_for_anchor_https_document`.
- The `network.predictor.*` prefs were **entirely removed** from Firefox in late 2025 (bug 2006028). They are dead prefs. Don't reference them.

### Recommended about:config (privacy-first)

```javascript
// Preconnect / speculative (always disable)
user_pref("network.http.speculative-parallel-limit", 0);
user_pref("network.preconnect", false);
user_pref("network.early-hints.preconnect.enabled", false);
user_pref("browser.urlbar.speculativeConnect.enabled", false);
user_pref("browser.places.speculativeConnect.enabled", false);

// Link prefetch (always disable)
user_pref("network.prefetch-next", false);

// DNS prefetch (see DoH section below for decision)
user_pref("network.dns.disablePrefetch", true);
user_pref("network.dns.disablePrefetchFromHTTPS", true);
```

## uBlock Origin interaction (critical pitfalls)

### What uBlock's "Disable pre-fetching" actually controls

uBlock Origin uses the `browser.privacy.network.networkPredictionEnabled` API. When enabled, it sets:
- `network.dns.disablePrefetch` = true ✓
- `network.prefetch-next` = false ✓
- `network.http.speculative-parallel-limit` = 0 (maybe) ✓

### What uBlock does NOT control

- `network.dns.disablePrefetchFromHTTPS` — **known gap**, never fixed (bug 1900730)
- `network.preconnect` — no API exists for this
- `network.early-hints.preconnect.enabled` — no API exists for this
- `browser.urlbar.speculativeConnect.enabled` — not covered
- `browser.places.speculativeConnect.enabled` — not covered

**Implication**: uBlock thinks it disabled all prefetching. It didn't. Manual about:config settings are required for the gaps.

### Known bugs where DNS/connection leaks bypass uBlock

1. **Preconnect bypasses uBlock** (bug 1861889, still open as of FF150+): Firefox makes DNS queries for domains uBlock is blocking, visible in DoH resolver logs (NextDNS, ControlD). Fix: `network.preconnect = false`.

2. **Early Hints bypass uBlock entirely** (uBlock-issues #3888): HTTP 103 Early Hints trigger real TCP+TLS connections to blocked hosts. These happen **outside the webRequest API** — uBlock literally cannot intercept them. gorhill (uBlock author): "These requests are not going through the webRequest API, there is nothing which can be done in uBO." Fix: `network.early-hints.preconnect.enabled = false`.

3. **HTTPS RR DNS leak with DoH** (bug 1730418, fixed FF94): When Firefox's own TRR is active (network.trr.mode 2/3), HTTPS record lookups leak DNS queries for uBlock-blocked domains to the DoH resolver. Fix: `network.dns.upgrade_with_https_rr = false` (only needed on pre-94 Firefox).

### Extension pref locking

When uBlock's "Disable pre-fetching" is ON, about:config shows affected prefs as "modified by extension" and manual overrides are blocked. If uBlock is disabled, prefs silently snap back to defaults. **Always set the prefs manually in about:config as a belt-and-suspenders approach.**

## DNS-over-HTTPS layering

### Two layers: OS-level vs Firefox TRR

| Aspect | OS-level DoH (Windows/ctrld) | Firefox TRR |
|--------|------------------------------|-------------|
| DNS encryption | ✓ | ✓ |
| ECH support | ✗ (requires Firefox TRR) | ✓ |
| Per-device ID at resolver | OS-level only | Browser-specific |
| TRR-only mode (no fallback) | N/A | `network.trr.mode = 3` |
| HTTPS RR leak bug | Not affected | Affected (pre-FF94) |

### Recommendation: use Firefox TRR on top of OS DoH

Set Firefox to Max Protection > Custom > ControlD DoH URL. Firefox will use its own TRR and ignore the system resolver. Keep OS-level DoH as fallback for other apps.

Benefits:
- **ECH (Encrypted Client Hello)** works — encrypts TLS SNI, so network observers can't see which domain you're connecting to. This is a major privacy win on public WiFi and against ISPs. Without Firefox TRR, ECH is disabled.
- ControlD can identify Firefox specifically for per-browser filtering rules.
- TRR-only mode (`network.trr.mode = 3`) prevents fallback to plaintext DNS.

### ControlD setup in Firefox

Settings > Privacy & Security > DNS over HTTPS > Max Protection > Custom:
- Free: `https://freedns.controld.com/p0` (unfiltered) or `p1` (malware block)
- Premium: `https://dns.controld.com/<your-resolver-id>`

### If staying with OS-level DoH only

All about:config settings from above still apply. The TRR-specific HTTPS RR leak bug doesn't apply. But ECH won't work — a real privacy gap.

## Arkenfox alignment

Arkenfox user.js (the gold standard Firefox hardening config) takes a blanket approach: disable ALL implicit outbound connections regardless of DoH status.

Key arkenfox sections:
- **0602**: Block implicit outbound connections (DNS prefetch, link prefetch, preconnect, speculative connect)
- **0710/0712**: DoH configuration (commented out — user must set their own provider)

Arkenfox treats DoH and prefetch-disable as **independent layers**, not alternatives. Even with DoH, arkenfox disables DNS prefetch because the resolver (even encrypted) learns browsing intent from prefetch queries.

Recent change (v127/FF127): `network.dns.disablePrefetchFromHTTPS` changed from true to false in arkenfox because Firefox bug 1596935 split the pref's scope — it now only controls `rel="dns-prefetch"` HTML hints, not automatic anchor prefetching. The master switch `network.dns.disablePrefetch = true` covers everything.

## Decision framework: what to enable with DoH

With encrypted DNS (ControlD DoH at any layer), the privacy cost of DNS prefetch is reduced because:
- The resolver already sees every domain you actually visit
- Prefetch only reveals "I viewed a page with a link to X" vs "I visited X"
- The incremental leak is marginal

**However**, enabling DNS prefetch:
- Conflicts with uBlock's settings (extension locks the pref)
- Arkenfox recommends against it (defense-in-depth)
- The performance gain is ~50-100ms — minimal

**Recommendation**: Keep DNS prefetch disabled. The performance gain doesn't justify fighting uBlock's settings or deviating from arkenfox.

## Fingerprinting resistance: RFP vs FPP (decision framework)

State as of FF128+/2026. Full detail: fingerprinting-rfp-fpp-brave-cloudflare.md.

- **RFP** (`privacy.resistFingerprinting`) is Tor Browser hardening ported to Firefox — a blunt hammer: UTC timezone, en-US locale, canvas noise, reduced timers, letterboxing, spoofed UA/hardware, forced light theme. Adoption ~0.02% of Firefox users (Mozilla telemetry) → you land in a rare bucket, not a crowd. Breaks calendars/scheduling (wrong-day appointments), Gmail timestamps, food delivery, captchas, SSO/OAuth, canvas-heavy sites. Mozilla ships a Settings warning banner (bug 1666160).
- **FPP** (`privacy.fingerprintingProtection`) is the breakage-aware successor: dynamic, targets actual fingerprinting attempts, randomizes canvas per eTLD+1/session, restricts fonts, hides hardware details — but does NOT spoof timezone/locale. On by default in Private Browsing (FF118+) and with ETP Strict (FF119+). Arkenfox's default since v128.
- RFP overrides FPP when both are on. Split is possible: FPP in normal windows + RFP in private windows via `privacy.resistFingerprinting.pbmode=true`.
- **Crowd argument** (arkenfox maintainer): fingerprinting resistance only works in a crowd; the best any non-Tor browser does is fool naive scripts via canvas randomization. "If you do nothing, you are unique. You can't make it worse."
- **Daily-driver recommendation**: ETP Strict + uBlock Origin. Optional extra: `privacy.fingerprintingProtection.overrides` = `"+AllTargets,-JSDateTimeUTC"` (Mozilla's own recipe — keeps real timezone; only needed if a site shows UTC, which usually means RFP is actually on). Full arkenfox user.js for the whole program. RFP only in a separate high-threat profile or Tor/Mullvad Browser; if used anyway: `privacy.resistFingerprinting.spoofTimezone=false`, canvas site exception via urlbar shield, `privacy.resistFingerprinting.exemptedDomains`.
- **Bot-detection angle**: Brave and RFP-Firefox get Cloudflare-challenged more than Firefox Strict because bot scoring wants consistency + membership in a modeled population. Brave farbling (fingerprint randomization per session) reads as automation; Brave's Chromium-claimed identity missing Privacy Sandbox surface triggers Turnstile 600010; shields block challenge infrastructure; aggressive cookie purging wipes cf_clearance (CHIPS-partitioned) → re-challenge every visit. Firefox Strict passes because its identity surface is stable and FPP rides the ETP-Strict crowd. "Boring and consistent" beats "aggressively unique" for CAPTCHA friction.

## Locale & language fingerprinting (what to actually set)

Full detail: locale-fingerprint-coherence.md.

- Windows has NO en-CA display language pack (only en-US/en-GB); en-CA exists only as regional format/spellcheck. OEMs (Dell/HP/Lenovo) ship en-US media in Canada; OOBE defaults region to US and can silently revert. en-US + Canada timezone is the modal Canadian machine.
- Chrome cannot emit en-CA: OS set to en-CA → browser reports en-GB,en-US,en. Firefox has an en-CA locale but adoption is tiny. Browser language is a browser setting, not a Windows one.
- Detection hierarchy: timezone-vs-IP is the strong signal, language is weak; coherence scoring means one mismatch is weak evidence, accumulation is the flag; perfectly uniform profiles read as automation (coarse-alignment tell).
- Rules: timezone must match the IP; stay in the modal cohort (Canada = en-US + America/Toronto); regional tags need the bare-language fallback (en-CA,en); in Playwright set context locale, never Accept-Language headers alone (header-vs-JS mismatch is detectable).

## References

- firefox-prefetch-bugs.md — detailed bug reports and workarounds
- fingerprinting-rfp-fpp-brave-cloudflare.md — RFP vs FPP mechanics, breakage list, arkenfox stance, Brave-vs-Cloudflare mechanisms with bug references


## Reference: fingerprinting-rfp-fpp-brave-cloudflare.md

# Fingerprinting resistance: RFP vs FPP, and bot-detection interactions

Research state: FF128+/2026. Sources: Mozilla bugzilla, arkenfox wiki/issues, brave-browser issues, Cloudflare docs.

## RFP (privacy.resistFingerprinting)

- What it does: UTC timezone, en-US locale, canvas noise, timer precision reduction, letterboxed window sizes, spoofed UA/hardware, forces light theme (`prefers-color-scheme: light`).
- Adoption: ~0.02% of Firefox users (Mozilla telemetry, per bug 1666160 thread) → no anonymity crowd.
- Known breakage (bugs 1364261, 1426232, 1666160): calendar/scheduling apps book appointments on the wrong day (Red Cross blood-donation anecdote in bug 1426232), Gmail timestamp formatting, food delivery times, Facebook birthday alerts, captchas, SSO/OAuth flows, canvas-heavy apps, video playback. Mozilla added a Settings warning banner pointing at a SUMO page (bug 1666160).
- Mozilla's stance: built for Tor Browser, not front-facing for Firefox; considered experimental ("running Firefox with it on should be considered experimental" — Mozilla commenter in bug 1426232).
- Fine-grained control prefs:
  - `privacy.resistFingerprinting.spoofTimezone = false` — keep real timezone (added later; defaults true so Tor behavior unchanged)
  - `privacy.resistFingerprinting.pbmode = true` — RFP only in private windows (then FPP applies in normal windows; FF123+ fixed the conflict, bug 1851816)
  - `privacy.resistFingerprinting.exemptedDomains` — unpublicized per-domain exemption (still leaves RoundedWindowSize etc.)
  - Canvas site exception via urlbar shield dialog
- arkenfox maintainer's personal RFP setup: RFP on + letterboxing on + `webgl.disabled=true` (WebGL is barely protected by RFP and concentrates huge entropy: GPU, math, fonts, CSS colors) + `privacy.spoof_english=2`.

## FPP (privacy.fingerprintingProtection)

- Dynamic: protects against actual fingerprinting behavior rather than blanket-spoofing. Canvas randomization per eTLD+1, per session, per window-mode; font restriction to system fonts; hides hardware details (cores, touchpoints, etc.). No timezone/locale spoofing — real timezone by default.
- Controlled by ETP: enabled with ETP Strict (FF119+) and default in Private Browsing (FF118+). Has a UI toggle (unlike RFP) → can build a crowd.
- FF145+ (2026): expanded protections; Mozilla claims fingerprintable user count halved. Randomization key daily reset (bug 2039194, landed FF153).
- Per-site webcompat exemptions via Remote Settings can auto-relax protections on broken sites.
- Overrides pref: `privacy.fingerprintingProtection.overrides`, e.g. `"+AllTargets,-JSDateTimeUTC"` (Mozilla support's recipe when sites show UTC — usually the user has RFP on; FPP alone does not spoof timezone). Caveat: disabling Tracking Protection for a site also disables fingerprinting protection there.
- RFP overrides FPP whenever RFP is enabled.

## Arkenfox stance (the authoritative community view)

- v128 (2024) flipped arkenfox's default from RFP to FPP ("ATTN: arkenfox v128 is now RFP-inactive and FPP is default", issue #1804): FPP is palatable because it emphasizes no breakage, and ETP Strict gives it a real crowd.
- Crowd argument: "If you do nothing, you are unique. You can't make it worse." Fingerprinting resistance requires a crowd (Tor Browser ~6M users); the best any non-Tor browser can do is fool naive scripts with canvas randomization — RFP and FPP both do that.
- Wiki "3.3 Overrides [To RFP or Not]": use RFP if you can live with the occasional site glitch (keep a secondary browser), otherwise FPP. RFP additionally carries timing-precision patches that blunt side-channel attacks.

## Brave vs Cloudflare: why Brave gets challenged more

Four structural mechanisms, documented in brave-browser issues across years:

1. **Farbling (fingerprint randomization) = inconsistency = bot signal.** Brave randomizes fingerprint values per-site/session/storage by design (its wiki: "you should get a different fingerprint each time"). Cloudflare scores consistency — a changing fingerprint reads as automation. Issue #15039 (2021) "Cloudflare endless looping due fingerprinting": only fix was "Allow all fingerprints". Issue #27006 (2022): "Enable fingerprinting solved this problem."
2. **Identity mismatch (Turnstile 600010).** Issue #45608 (current-gen, controlled repro on Linux/ARM64): Brave fails Turnstile with client-side error 600010 ("bot behaviour detected") 100% of the time — Stable and Beta, shields up/down, fingerprinting off, clean profiles — while vanilla Chromium 150 and Firefox 152 pass from the same IP within the hour. Measured diffs: Brave adds "Brave" to `navigator.userAgentData.brands`, and lacks Chromium's Privacy Sandbox / Private State Token surface. Cloudflare scores conditionally on browser class: something announcing Chromium/150 is expected to expose what Chromium 150 ships; absence reads as anomalous. Firefox is never held to that expectation (Gecko passes despite also lacking PST). Related: issue #47826 — Brave sends `"Brave";v="139"` instead of `"Google Chrome";v="139"` in Sec-CH-UA specifically when redirected from Cloudflare.
3. **Shields blocks the challenge's own infrastructure.** Brave actively blocks known fingerprinting domains (e.g. fingerprint.com network requests — advertised feature). Partially blocked challenge scripts can't compute a score → fail → retry loop.
4. **cf_clearance cookie state.** `cf_clearance` is `SameSite=None; Secure; Partitioned` (CHIPS), default lifetime 30 min (Challenge Passage, 15–45 min recommended). Brave's "forget me when I close this site" and aggressive-mode cookie purging wipe it → re-challenge every visit. Firefox Total Cookie Protection partitions cookies but persists them within the partition, so clearance survives.

Caveat: environment-dependent, not a law — Cloudflare community report (July 2026) of the exact inverse (Turnstile 600010 on Firefox/Linux while Brave passes, two networks). IP reputation dominates. But the structural mechanisms above are documented across years of Brave issues.

## Synthesis / decision rule

- Bot detection wants consistency + membership in a known population; anti-fingerprinting randomization defeats trackers but trips bot detectors.
- Firefox Strict/FPP: subtle canvas noise, stable identity surface, rides the ETP-Strict crowd → scores as a normal Firefox.
- Brave: unique fingerprint every session by design → looks like a bot trying to look human.
- RFP Firefox: unique Tor-flavored browser matching no model → captcha'd too (documented in Mozilla bug threads).
- Rule of thumb: "boring and consistent" beats "aggressively unique" for CAPTCHA friction.


## Reference: firefox-prefetch-bugs.md

# Firefox Prefetch Bugs and Workarounds

## Bug 1861889: Preconnect bypasses uBlock Origin

**Status**: Still open (as of FF150+, 2025)
**URL**: https://bugzilla.mozilla.org/show_bug.cgi?id=1861889

**Problem**: `chrome.privacy.network.networkPredictionEnabled` API (used by uBlock Origin) no longer prevents preconnecting. When uBlock sets `networkPredictionEnabled = false`, Firefox still makes DNS queries and TCP connections to domains that uBlock is blocking.

**Reproduction**:
1. Install uBlock Origin, enable "Disable pre-fetching"
2. Set up a DoH resolver with logging (NextDNS, ControlD)
3. Visit a site that loads google-analytics.com
4. Check DoH resolver logs — DNS queries for google-analytics.com appear despite uBlock blocking

**Root cause**: `network.preconnect` (HTML `<link rel=preconnect>`) is NOT controlled by the `networkPredictionEnabled` API. The API controls `network.dns.disablePrefetch`, `network.prefetch-next`, and `network.http.speculative-parallel-limit`, but not `network.preconnect`.

**Fix**: `network.preconnect = false` in about:config

**Notes**:
- The predictor (`network.predictor.enabled`) was removed in late 2025 (bug 2006028), which was one previous cause
- `network.preconnect` is the remaining gap
- This still affects Firefox 150+ as of late 2025

---

## Bug 3888 (uBlock-issues): Early Hints bypass uBlock entirely

**Status**: Closed as "external" — uBlock cannot fix this
**URL**: https://github.com/uBlockOrigin/uBlock-issues/issues/3888

**Problem**: Firefox supports HTTP 103 Early Hints (default since FF120). When a server sends `103 Early Hints` with preconnect directives, Firefox opens actual TCP+TLS connections to those hosts. These connections happen **outside the webRequest API** — uBlock cannot intercept them.

**Reproduction**:
1. Visit medium.com (sends 103 Early Hints for google.com/reCAPTCHA)
2. Monitor with Little Snitch or tcpdump
3. Observe TCP SYN to www.google.com:443 even though uBlock shows google.com as "blocked"

**gorhill's response** (uBlock author): "These requests are not going through the webRequest API, there is nothing which can be done in uBO."

**Fix**: `network.early-hints.preconnect.enabled = false`

**Notes**:
- No extension API exists to control this pref
- This is a real TCP connection (SYN-ACK), not just a DNS query
- The connection is visible to the target server and network observers

---

## Bug 1730418: HTTPS RR DNS leak with DoH

**Status**: Fixed in Firefox 94
**URL**: https://bugzilla.mozilla.org/show_bug.cgi?id=1730418

**Problem**: When Firefox's own TRR is active (`network.trr.mode` = 2 or 3), HTTPS record lookups leak DNS queries for uBlock-blocked domains to the DoH resolver. The HTTP request is blocked by uBlock, but the DNS query still reaches the resolver.

**Root cause**: HTTPS RR resolution is triggered from `BeginConnect -> MaybeStartDNSPrefetch`, which runs before uBlock's webRequest filter gets a chance to block the channel. This only happens with TRR (not system DNS) because TRR resolves HTTPS records while the native resolver doesn't.

**Workaround** (pre-FF94): `network.dns.upgrade_with_https_rr = false`

**Notes**:
- Does NOT affect OS-level DoH (Windows/ctrld) — only Firefox's own TRR
- Fixed in FF94, but the pref can be set as insurance on older versions
- `network.dns.echconfig.enabled` and `network.dns.use_https_rr_as_altsvc` are NOT affected by this workaround

---

## Bug 1900730: uBlock's "Disable pre-fetching" incomplete

**Status**: Duplicate of bug 1861889
**URL**: https://bugzilla.mozilla.org/show_bug.cgi?id=1900730

**Problem**: uBlock Origin's "Disable pre-fetching" option does not set `network.dns.disablePrefetchFromHTTPS` to true. The `networkPredictionEnabled` API was never updated to include this pref.

**Impact**: On HTTPS pages, `<link rel=dns-prefetch>` hints still trigger DNS lookups even with uBlock's setting enabled.

**Fix**: Set `network.dns.disablePrefetchFromHTTPS = true` manually, or rely on the master switch `network.dns.disablePrefetch = true` (which uBlock does set correctly).

---

## Bug 1596935: DNS prefetch pref scope split

**Status**: Fixed
**URL**: https://bugzilla.mozilla.org/show_bug.cgi?id=1596935

**Problem**: Firefox split the DNS prefetch pref behavior. `network.dns.disablePrefetch` and `network.dns.disablePrefetchFromHTTPS` now only control `rel="dns-prefetch"` HTML hints. Automatic anchor prefetching is controlled by separate prefs: `dom.prefetch_dns_for_anchor_http_document` and `dom.prefetch_dns_for_anchor_https_document`.

**Key finding** (from arkenfox issue #1870): `network.dns.disablePrefetch` is still the master switch — when set to true, it disables both `dom.prefetch_dns_for_anchor_*` prefs automatically.

**Hierarchy**:
1. `network.dns.disablePrefetch` — master switch for everything
2. `network.dns.disablePrefetchFromHTTPS` — master switch for `dom.prefetch_dns_for_anchor_https_document`
3. `dom.prefetch_dns_for_anchor_http_document` — controls anchor DNS prefetch on HTTP
4. `dom.prefetch_dns_for_anchor_https_document` — controls anchor DNS prefetch on HTTPS

---

## Bug 2006028: Network predictor removed

**Status**: Fixed (removed from Firefox)
**URL**: https://bugzilla.mozilla.org/show_bug.cgi?id=2006028

**Problem**: The network predictor (`network.predictor.*`) was removed from Firefox in late 2025. It used the HTTP cache as a database to learn browsing patterns and make speculative DNS prefetches, TCP preconnects, and resource prefetches.

**Impact**: Any about:config guide referencing `network.predictor.enabled`, `network.predictor.enable-prefetch`, or other `network.predictor.*` prefs is outdated. These prefs no longer exist and have no effect.

**Replaced by**: HTTP 103 Early Hints and Speculation Rules API (server-driven, more accurate).


## Reference: locale-fingerprint-coherence.md

# Locale & language fingerprinting: what to actually set

Research-backed guidance (Aug 2026, exa-verified) for questions like "should I set my locale to match my country" / "will this fingerprint flag me". The Canada case is the worked example; the principles generalize.

## The OS reality (Windows 11, Canada case)

- **No en-CA display language pack exists.** Windows ships exactly two English display packs: en-US and en-GB. en-CA exists only as a preferred-language entry (spellcheck/app dictionaries) and as a regional format (date/number formatting). "Fully Canadian" is not a reachable configuration.
- OEMs ship en-US media for Canada: Dell Canada's Ready Image spec lists single-language builds English (US), English (UK), French (Canada) — no English (Canada) — and the AMER multi-language build is "created with English (United States) media". HP/Lenovo same.
- OOBE preselects United States as region; documented cases of OOBE region/language selections silently reverting to en-US after first login; skipping the language step (e.g. network cable connected) defaults to English US.
- Conclusion: a normal Canadian machine is en-US display + Canada region (or even US region). **en-US + Canada timezone IS the modal Canadian fingerprint.**

## Browser emission

- **Chrome cannot emit en-CA.** It has no en-CA localization; OS set to English (Canada) produces `navigator.languages = ["en-GB","en-US","en"]` and `Accept-Language: en-GB,en-US;q=0.9,en;q=0.8` (chromium-os-dev thread). Same for fr-CA → fr-FR. Setting OS language is therefore pointless for Chrome fingerprint purposes.
- Firefox has a real en-CA locale (since FF62) but adoption is tiny; Mozilla had to run a promotion campaign to get Canadians onto it. en-CA in navigator.language is a small minority cohort.
- navigator.language comes from the BROWSER's language setting, not the Windows regional format. Changing Windows regional format does not change the browser fingerprint. Browsers must be changed in their own settings (Chrome: en-US; Firefox: en-US or en-US,en).

## Detection hierarchy (Kameleo, BotBrowser, ToDetect, BrowserInsight, Sendwin all agree)

- **Strong signal: timezone vs IP geolocation.** Multi-hour offset gap against the IP's country = flag. Use IANA names (America/Toronto) not fixed UTC offsets (DST transitions are checked).
- **Weak signal: language vs IP.** People travel with their language; travelers/expats are normal. A mismatch here alone is weak evidence.
- **Coherence scoring, not purity.** One mismatch is weak; accumulation of mismatches is the flag. Scoring is about "does this story hold together", not "is the locale correct".
- **Uniformity is itself a tell.** Proxy pools that map a whole country to one fixed TZ/locale read as automation (coarse-alignment failure). Real residents show variation. Blend into the modal cohort; being a small minority cohort is a cost, not a benefit.

## Rules

- Timezone must match the IP's geolocation, always. Never combine a regional locale (en-CA) with a US timezone or US IP.
- Regional tags need the bare-language fallback: `en-CA,en` (W3C convention; Chrome auto-appends the bare language, Firefox requires manual addition).
- Set browser language in the browser, not the OS. Keep the modal locale for the region (Canada = en-US).
- Automation (Playwright/Puppeteer): set context `locale` + `timezoneId` (e.g. `en-US`, `America/Toronto`) and make the exit IP geolocate to the same region. Never spoof Accept-Language via `page.setExtraHTTPHeaders` alone — header-vs-navigator mismatch is detectable.
- Date formats are cross-checked too: US timezone with DD/MM/YYYY formatting is a mismatch tell; Canada's en-CA regional format (yyyy-mm-dd style dates) is genuinely common so it does not flag — but it also doesn't reach the browser fingerprint.
- For a Canadian user wanting to blend in: leave Windows display en-US, region Canada, timezone America/Toronto, browser en-US. Doing nothing already matches the average machine.
