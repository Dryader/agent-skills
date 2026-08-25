---
name: subagent-debate
description: "Decision-making pattern using opposing subagent advocates. Each advocate researches and argues their position, then the parent agent judges based on evidence. Use for technology comparisons, architecture decisions, vendor evaluations, and any choice where both sides have merit."
tags: [decision-making, research, comparison, debate, subagent]
triggers:
  - deciding between opposing options
  - adversarial review of a plan
  - user says debate this

---

# Subagent Debate Pattern

## When to Use

Use this pattern when:
- Comparing two or more technologies/vendors/approaches
- The decision has real tradeoffs (not obvious)
- You need evidence-based arguments, not opinions
- The user wants to see both sides before deciding
- You need to research extensively before recommending

## The Pattern

### 1. Define the Debate

Create two subagents with opposing positions. Each advocate should:
- Research their position using MCP web search
- Build a structured argument with citations
- Specifically attack the OTHER side's weaknesses
- Find evidence that their side is better

### 2. Prompt Design

**Key principles:**
- **Don't guide what they should look for** — let them find their own arguments. User explicitly corrected this: "dont guide it to what its supposed to look for." Biased prompts produce biased results.
- Tell them to specifically attack the OTHER side, not just promote their own
- Ask for evidence, not opinions
- Be explicit about the scope (governance vs security, cost vs features, etc.)
- **Don't mention specific tools/CVEs/approaches in the prompt** — this biases the research

**Example prompts (unbiased):**

```
Subagent 1: "You are arguing that [Option A] is BETTER than [Option B] for [specific use case]. Your job is to specifically attack [Option B]'s weaknesses and prove why [Option A] is the superior choice OVER [Option B]. Research using MCP web search. Find whatever evidence you can — don't look for specific things, just find what's out there that supports your position. Build a structured argument with citations. Be thorough — do as many searches as you need."

Subagent 2: [Same prompt with A and B swapped]
```

**What NOT to do (user corrected this):**
```
❌ BAD: "Focus on: enforcement model, CVE track record, compliance frameworks, cost, Microsoft's recommendation"
   → This tells the advocate what to find, biasing the research

✅ GOOD: "Find whatever evidence you can — don't look for specific things, just find what's out there"
   → Let the advocate discover their own arguments
```

### 3. Run in Parallel

Both advocates should run in parallel (not sequentially). This prevents the second advocate from being influenced by the first.

### 4. Judge the Results (Use a Separate Judge Subagent)

**Critical: Dispatch a THIRD subagent as judge. Don't judge yourself.**

The parent agent has context from the conversation that biases judgment. A fresh subagent evaluates only the evidence presented. User explicitly requested this: "instead dispatch a subagent to judge the results rather than you."

**Judge prompt:**
```
"You are an impartial judge evaluating a debate between two advocates:
1. [Option A] advocate — arguing that [Option A] is better than [Option B] for [specific use case]
2. [Option B] advocate — arguing that [Option B] is better than [Option A] for [specific use case]

Your job is to:
1. Read both arguments from the files provided
2. Evaluate each argument on its merits — what's strong, what's weak, what's misleading
3. Determine a winner for the specific question of [scope]
4. Provide a detailed, evidence-based judgment with specific citations from both arguments
5. Be honest — if one side made a stronger case, say so. If it's a tie, explain why.

Context: [provide relevant context about the decision]"
```

**Why a separate judge subagent:**
- The parent agent has context from the conversation that biases judgment
- A fresh subagent evaluates only the evidence presented
- Produces more balanced, evidence-based verdicts

### 5. Present the Verdict

The verdict should include:
- Round-by-round comparison (which side wins each dimension)
- The strongest arguments from each side
- The weakest arguments from each side
- A clear recommendation with reasoning
- The question that determines which option is right

## Anti-Patterns

- **Guiding the advocates** — Don't tell them what to look for. Let them find their own evidence.
- **Asking for opinions** — Ask for evidence and research, not opinions.
- **Biased prompts** — Don't frame the prompt to favor one side.
- **Stopping too early** — Both advocates should do extensive research (10+ searches each).
- **Ignoring context** — The verdict should consider the specific use case, not just abstract advantages.

## Example: Enterprise Application Control

The user asked: "Could CyberArk EPM do everything? Why use WDAC/AppLocker?"

**Approach:**
1. Created two advocates: WDAC advocate and Idira advocate
2. First round: general arguments (each promoted their own side)
3. Second round: attack arguments (each attacked the other side)
4. Judged based on governance vs security distinction

**Key insight from the debate:**
- For GOVERNANCE (controlling what users run), Idira wins on features
- For SECURITY (defending against sophisticated attackers), WDAC wins on boundary strength
- The correct answer depends on the priority: governance vs security

## Tips

- Run 2-3 rounds for complex decisions (general → attack → specific)
- Use MCP web search for evidence, not just your training data
- Present the verdict as a decision framework, not just a recommendation
- Include the "question to ask" that determines which option is right
- Save the debate results as a reference file for future use
- **Distinguish governance vs security framing.** When the user asks about "governing" something, they mean: discovery, graduated controls, identity-aware targeting, operational manageability. This is DIFFERENT from "security" which means: tamper resistance, CVE-class boundaries, kernel enforcement. The debate outcome depends heavily on which framing you use. Ask the user which framing they care about.
- **Ask "what were the prompts you gave?"** — Users want transparency on delegation prompts. Be prepared to show exactly what you told each subagent.
