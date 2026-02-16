"""
Few-shot examples for Stage 2 (The Demon Hunter) analysis.

UPDATED PHILOSOPHY (v2.0):
- MONEY & STABILITY > Corporate Values.
- Silence on salary is NEUTRAL (Score 7).
- "Grey" domains (Gambling, Crypto, Dating) imply USDT/Foreign currency = GREEN FLAG (Score 8+).
- Modern Stack is crucial. Legacy without huge pay is a penalty.
"""

STAGE2_FEW_SHOTS = """
<EXAMPLES_OF_CORRECT_ANALYSIS>

Example 1: The "Standard Corporate Silence" (Baseline)
Input Snippet: "Middle/Senior Python Developer. Stack: Django, DRF, PostgreSQL, Celery. We offer: competitive salary based on interview, health insurance, English classes, friendly team."
Analysis:
  - Trust Score: 7
  - Reasoning: "Standard stack, standard corporate benefits. 'Competitive salary' is vague but NEUTRAL (market standard). No toxic flags found."
  - Honest Summary: "A boring, standard job. They won't tell you the salary until the end, but it doesn't look like a scam."
  - Verdict: Safe - Typical market offer.

Example 2: The "Grey Goldmine" (Implicit USDT)
Input Snippet: "Backend Engineer for a High-load iGaming platform. Tech: Python 3.12, FastAPI, Kafka, ClickHouse, Redis. We handle 10k+ RPS. Remote work, flexible hours."
Analysis:
  - Trust Score: 9
  - Green Flags: ["iGaming domain implies stable revenue & likely USDT/Currency peg", "Modern High-load Stack (FastAPI/ClickHouse)"]
  - Reasoning: "Gambling/iGaming usually pays in hard currency (USDT) and creates technical challenges (Highload). No salary listed, but the domain implies money."
  - Honest Summary: "It's a casino/betting platform. Morally grey, but financially green. You'll likely get paid in USDT and work with cool tech."
  - Verdict: Gem - High probability of good pay and modern stack.

Example 3: The "Burnout Factory" (Toxic)
Input Snippet: "We are a rocket-ship startup! Looking for rockstars willing to wear many hats. Dynamic environment, family atmosphere. Pizza on Fridays! Stress resistance is a must."
Analysis:
  - Trust Score: 3
  - Red Flags: ["'Rockstar' & 'Many hats' = Exploitation", "'Family' = Emotional manipulation", "'Stress resistance' = Toxic processes"]
  - Toxic Phrases: ["wear many hats", "family atmosphere", "stress resistance is a must"]
  - Honest Summary: "You will do the work of three people for the salary of one. They use 'family' to guilt-trip you into unpaid overtime."
  - Verdict: Avoid - Classic toxic startup.

Example 4: The "Legacy Trap" (Honest but Painful)
Input Snippet: "Support and development of internal ERP system. Stack: Python 2.7, Zope, jQuery. Stability guaranteed. Salary: up to $2000."
Analysis:
  - Trust Score: 4
  - Red Flags: ["Ancient Stack (Python 2.7/Zope)", "Salary ($2000) is too low for suffering with legacy"]
  - Honest Summary: "Career suicide. You will rot maintaining dead code for peanuts."
  - Verdict: Risky/Avoid - Unless you are desperate.

Example 5: The "Golden Handcuffs" (Legacy but Rich)
Input Snippet: "Senior Engineer to maintain legacy monolith. Stack: Python 2.7, Twisted. Salary: $6500 - $7000 net. B2B contract."
Analysis:
  - Trust Score: 8
  - Green Flags: ["Very High Salary (compensates for legacy)", "B2B Contract"]
  - Red Flags: ["Legacy Stack"]
  - Reasoning: "The stack is dead, but the money is alive. They understand that maintaining this requires a premium."
  - Honest Summary: "It's a graveyard, but they give you a golden shovel. If you need money and don't care about your CV, take it."
  - Verdict: Safe - Honest trade of sanity for money.

Example 6: The "Web3/Crypto" (Wild West)
Input Snippet: "Blockchain Developer. Solidity + Python. Building the future of DeFi. Token allocation included."
Analysis:
  - Trust Score: 8
  - Green Flags: ["Crypto domain = Potential USDT pay", "Token allocation (bonus lottery)"]
  - Red Flags: ["DeFi can be unstable"]
  - Honest Summary: "High risk, high reward. Likely paid in crypto. If the project doesn't rugpull, you're rich."
  - Verdict: Safe - Good for financial growth.

</EXAMPLES_OF_CORRECT_ANALYSIS>
"""
