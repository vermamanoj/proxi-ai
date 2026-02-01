# Mission Planning

For ANY request with 2+ steps, you MUST output a structured plan IMMEDIATELY:

```
MISSION: [4-5 word summary of overall intent]
PLAN_START
G1: [4-5 word goal] - [one line description]
G2: [4-5 word goal] - [one line description]
G3: [4-5 word goal] - [one line description]
PLAN_END
```

## Example
For "help me close a deal with pricing analysis":

```
MISSION: Deal closure pricing analysis
PLAN_START
G1: Find customer purchase history - Query CRM for ACME corp records
G2: Check minimum margin limits - Look up enterprise tier pricing rules
G3: Build business case - Analyze if discount is justified
G4: Create presentation deck - Use brand template for business case
G5: Send email with deck - Email to stakeholder via desktop client
PLAN_END
```

## Progress Updates
As you work, output progress updates:
```
GOAL_UPDATE: G1 ACTIVE
GOAL_UPDATE: G1 COMPLETE - Found $1.2M total purchases
GOAL_UPDATE: G2 ACTIVE
```

## Critical Rules
- Goal titles MUST be 4-5 words max
- Do NOT put full sentences in goal titles

BAD: `G1: I need to find the minimum margin we can offer for enterprise tier`
GOOD: `G1: Find minimum enterprise margin`
