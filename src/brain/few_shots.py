"""
Few-shot examples for Stage 2 (The Demon Hunter) analysis.

These examples teach the LLM to detect toxic patterns, corporate lies,
and red flags in job vacancies. They demonstrate the cynical, honest
analysis style we expect.

Update this file as we discover new toxic patterns in the wild.
"""

STAGE2_FEW_SHOTS = """
<EXAMPLES_OF_CORRECT_ANALYSIS>

Example 1: The "Legacy Trap"
Input Snippet: "Main stack: Python 3.11. Tasks: Maintenance of existing code base written in Twisted and Python 2.7."
Analysis:
  - Trust Score: 3
  - Red Flag: "Technical Contradiction (Bait & Switch): Title says Python 3.11, reality is Python 2.7 legacy."
  - Honest Summary: "You will rot maintaining dead code while dreaming of modern features. The 'Python 3.11' in the title is bait."
  - Verdict: Avoid - Major contradiction between advertised and actual tech stack.

Example 2: The "Burnout Factory"
Input Snippet: "We are a rocket-ship startup! Looking for rockstars willing to wear many hats and work in a fast-paced dynamic environment. Pizza on Fridays!"
Analysis:
  - Trust Score: 2
  - Red Flag: "Classic burnout signals ('rockstar', 'many hats', 'fast-paced')."
  - Red Flag: "Pizza used as a benefit substitute instead of real compensation."
  - Red Flag: "No clear role definition - 'wear many hats' means chaos."
  - Toxic Phrases: ["rockstars willing to wear many hats", "fast-paced dynamic environment"]
  - Honest Summary: "Chaos, unpaid overtime, and no defined role. You are cheap labor. 'Pizza on Fridays' is insulting instead of proper benefits."
  - Verdict: Avoid - Multiple red flags indicating toxic startup culture.

Example 3: The "Good Galley" (Rare but Exists)
Input Snippet: "Stack: FastAPI, SQLAlchemy, PostgreSQL, AWS. Salary: $4000-5000 net. Sick leaves: 20 days paid. Overtime: Paid x2 (rarely happens, we respect work-life balance). Health insurance included."
Analysis:
  - Trust Score: 9
  - Honest Summary: "A transparent offer with clear rules, market salary, and real benefits. They explicitly mention work-life balance and compensate overtime properly."
  - Verdict: Safe - Apply confidently. Rare example of honest vacancy.

Example 4: The "Vague Responsibilities"
Input Snippet: "Responsibilities: Develop innovative solutions. Work with cutting-edge technologies. Collaborate with team. Deliver results."
Analysis:
  - Trust Score: 4
  - Red Flag: "Zero concrete responsibilities - all buzzwords."
  - Red Flag: "No mention of actual tech stack or projects."
  - Honest Summary: "They have no idea what they want. You'll be thrown into random tasks with no direction."
  - Verdict: Risky - Ask very specific questions about actual day-to-day work.

Example 5: The "Salary Manipulation"
Input Snippet: "Competitive salary based on experience. Senior Python Developer position."
Analysis:
  - Trust Score: 5
  - Red Flag: "'Competitive salary' without numbers = below market rate."
  - Red Flag: "For Senior level, salary should be stated upfront."
  - Honest Summary: "They're hiding the salary because it's low. 'Based on experience' means they'll lowball you."
  - Verdict: Risky - Demand exact numbers before wasting time on interviews.

Example 6: The "Family Atmosphere" Trap
Input Snippet: "We're like a family here! Everyone helps each other. Sometimes we work late together, but it's fun!"
Analysis:
  - Trust Score: 3
  - Red Flag: "'Family' = emotional manipulation and guilt trips."
  - Red Flag: "'Work late together' = unpaid overtime normalized."
  - Toxic Phrases: ["We're like a family", "Sometimes we work late together, but it's fun"]
  - Honest Summary: "They'll guilt you into unpaid overtime using 'family' rhetoric. Boundaries don't exist here."
  - Verdict: Avoid - Classic toxic culture red flag.

</EXAMPLES_OF_CORRECT_ANALYSIS>
"""


# Future: Add more examples as we discover patterns
# TODO: Consider A/B testing different example sets
# TODO: Version control example quality (track which examples improve accuracy)
