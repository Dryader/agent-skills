---
name: devils-advocate-research
description: Validate recommendations by searching for complaints, and do investigative deep-research on people/orgs by cross-referencing multiple sources to find contradictions and test claims against actions.
tags: [research, reviews, comparison, validation, consumer]
triggers:
  - user asks to compare products/services
  - user asks "which should I buy"
  - making a recommendation between multiple options
  - user says "play devil's advocate"
  - validating a shortlist of candidates
  - "research this person"
  - "summarize their posts"
  - "find contradictions"
  - deep research on a person, organization, or public controversy
---

# Devil's Advocate Research

When recommending a product, service, or option, actively try to DISPROVE your recommendation before presenting it as final. This catches blind spots and prevents recommending something based on surface-level positive reviews.

Also covers **investigative research on people/organizations** — deep multi-source analysis that goes beyond summarizing to find contradictions, test claims against actions, and form defensible opinions. See investigative-research-mcp.md for the MCP Exa workflow and analysis techniques.

## When to Use

- Comparing 3+ options (products, services, tools, shops)
- User asks "which one should I get"
- Before finalizing a recommendation after initial research
- When user explicitly says "play devil's advocate" or "try to disprove it"

## Steps

### Phase 1: Initial Research (normal)
1. Search for the best options in the category
2. Build a shortlist of 3-5 candidates
3. Form an initial recommendation based on features, price, availability

### Phase 2: Devil's Advocate (the key part)
For EACH candidate on the shortlist, search specifically for:

1. **Complaints & negative reviews**
   - Search: `"[product name]" complaints problems issues`
   - Search: `"[product name]" reddit negative review`
   - Search: `"[product name]" BBB complaints`
   - Search: `"[product name]" trustpilot 1 star`
   - Search: `"[product name]" scam OR ripoff OR terrible`

2. **Specific failure patterns**
   - What goes wrong most often?
   - Are complaints about one-off issues or systemic?
   - How does customer service handle problems?
   - Are refunds easy or a nightmare?

3. **Hidden downsides**
   - Hidden fees, bait-and-switch pricing
   - Warranty that's hard to claim
   - Quality that degrades over time
   - Fake/paid reviews inflating ratings

4. **Post-purchase experience**
   - Returns process
   - Customer service responsiveness
   - How they handle defects/errors

### Phase 3: Elimination & Revised Recommendation
1. Eliminate any option with systemic (not one-off) problems
2. Rank remaining options by: worst complaint severity, not just average rating
3. Present the recommendation with honest caveats
4. Note what could go wrong and how to mitigate it

## Search Strategy

Use parallel subagents for efficiency — one per candidate:

```
delegate_task with tasks=[
  {goal: "Find negative reviews and complaints about [Option A]..."},
  {goal: "Find negative reviews and complaints about [Option B]..."},
  {goal: "Find negative reviews and complaints about [Option C]..."}
]
```

Each subagent should search across:
- Reddit (site:reddit.com)
- Trustpilot
- BBB (bbb.org)
- SmartCustomer / Reviews.io
- Facebook groups
- Blog reviews (honest/independent ones)
- Forums specific to the product category
- **RedFlagDeals (forums.redflagdeals.com)** — gold standard for Canadian services. Mega-threads with hundreds of pages of real user data points, pricing, and complaints. Use `mcp__exa__web_fetch_exa` to pull full thread pages.
- **Head-Fi.org** — for audio gear complaints and pad-rolling experiences

## Output Format

Present findings as:

```
[OPTION NAME] — THE CASE AGAINST
================================
PATTERN 1: [Category of complaint]
  "Direct quote from user" — Source
  "Another quote" — Source

PATTERN 2: [Category]
  ...

SILVER LINING: [What they do well even when things go wrong]
```

Then a final verdict:
- Which options were eliminated and why
- Which option survived and what the remaining risks are
- How to mitigate those risks (e.g., "inspect on arrival", "use credit card for chargeback protection")
- Include a comparative summary table showing key metrics side-by-side (rating, price, shipping, complaint severity)

The "ELIMINATED / SURVIVED WITH CAVEATS / STILL THE PICK" framing works well — it's decisive and shows the reasoning chain.

## Key Principles

1. **Patterns > one-offs**: A single bad review means nothing. 10 people reporting the same issue is a pattern.
2. **Customer service matters more than product**: Things go wrong everywhere. How they handle it is the real differentiator.
3. **Check independent reviews, not site reviews**: Trustpilot/BBB/Reddit > company's own testimonial page.
4. **Cheap ≠ bad, expensive ≠ good**: Judge on actual user experience, not price.
5. **Be honest**: If your initial pick gets eliminated, say so. Don't defend it just because you recommended it first.

## Pitfalls

- Don't overweight negative reviews (every product has some)
- Don't dismiss a 4-star product because of a few 1-star reviews — look for PATTERNS
- Paid/fake reviews exist on both positive AND negative sides
- Older complaints may not reflect current state (companies improve or decline)
- Always note the sample size (181 reviews vs 5,000 reviews matters)
- **Coupon/promo codes from third-party sites frequently don't work.** Don't tell the user "try this code" unless you've verified it. The retailer's own site is the most reliable source for active promotions. Coupon aggregator sites (CouponFollow, RetailMeNot) hide codes behind JS buttons and many listed as "verified" are expired or retailer-specific (e.g., US-only codes that don't work on Canadian sites).


## Reference: investigative-research-mcp.md

# Investigative Research with MCP Exa Tools

Multi-source deep research on people, organizations, or controversies. Goes beyond surface summaries to find contradictions, analyze stated beliefs against actions, and understand public reaction.

## User Preference
**Use MCP Exa tools over browser for research/extraction.** If `web_extract` or browser navigation fails or returns jumbled content, switch to `mcp__exa__web_search_exa` / `mcp__exa__web_fetch_exa` immediately. Don't keep trying browser approaches.

## Workflow

### Phase 1: Find All Relevant Content
Use `mcp__exa__web_search_advanced_exa` with filters:
- `site:domain.com` to find all content from a specific author/site
- `startPublishedDate` to filter by time period
- `category: "news"` or `category: "personal site"` for targeted results
- `numResults: 20` for comprehensive coverage

Run multiple searches in parallel:
1. The subject's own writing/site
2. News coverage of the subject
3. Community discussion (HN, Reddit, forums)
4. Related controversies or scandals

### Phase 2: Extract Full Content
Use `mcp__exa__web_fetch_exa` to pull full text from the best URLs. Batch up to 5 URLs per call. Set `maxCharacters` high (15000+) when you need full articles.

For community discussions (HN, Reddit), also try:
- HN Algolia API: `https://hn.algolia.com/api/v1/items/{id}` for structured comment data
- Direct fetch may be rate-limited; have fallback searches ready

### Phase 3: Cross-Reference and Analyze
Don't just summarize each source. Look for:
- **Stated beliefs vs. actions** — Does the subject practice what they preach?
- **Internal contradictions** — Does their own writing argue against their own decisions?
- **Timeline gaps** — What happened between periods of silence? What triggered new activity?
- **Self-serving framing** — Are blog posts/essays actually PR responses to controversy?
- **Community reaction patterns** — What are the main camps? Who's defending, who's attacking, and why?
- **The "steel man" vs. actual position** — What's the strongest version of their argument, and does it hold up?

### Phase 4: Synthesize with Opinions
The user wants analysis, not just summaries. Form and defend positions:
- "Here's what he says vs. here's what he does"
- "The philosophy argues against the action"
- "The simplest explanation is X"
- Identify when someone is using intellectual frameworks as post-hoc justification

## Pitfalls
- **Don't stop at the subject's own framing.** Their blog posts are PR. Always cross-reference with external sources.
- **HN/Reddit may rate-limit.** Have fallback search strategies (Exa search for "site:news.ycombinator.com" + topic keywords).
- **Archive pages often jumble posts together.** If an author archive mixes content without dates, use `mcp__exa__web_search_advanced_exa` with `site:domain.com/author/` and date filters instead of trying to parse the archive page.
- **Don't present both sides as equally valid when evidence clearly favors one.** If someone's philosophy contradicts their actions, say so.
- **Multiple HN threads may exist for the same topic.** Search for all of them — later threads often have different angles and new information.
