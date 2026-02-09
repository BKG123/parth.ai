This document serves as the **Skill Specification & Creation Guide** for Parth.ai. It defines the standard for how you (as the Agent) should generate and manage "Skills"—the reusable logic templates that guide goal achievement.

---

## 1. Skill Anatomy

When you invoke `create_skill()`, the content must adhere to this structural standard to ensure consistency across the library.

| Field | Requirement | Purpose |
| --- | --- | --- |
| **Name** | `snake_case` (e.g., `morning_routine_builder`) | Unique identifier for internal logic. |
| **Title** | Title Case (e.g., "Morning Routine Builder") | User-facing or search-friendly name. |
| **Description** | 1-2 sentences | Briefly explains the goal type and the skill's specific methodology. |
| **Skill Prompt** | Structured Text (see below) | The "DNA" of the skill; guides how you track and talk to the user. |
| **Metadata** | JSON Object | Tags like `{"category": "productivity", "difficulty": "beginner"}`. |

---

## 2. The Skill Prompt Framework

The `skill_prompt` is the most critical part. It should be written as an **Internal Directive** to yourself. Use the following four-pillar structure:

### I. Tracking Approach

Define the data schema and frequency.

* **Snapshot keys:** What keys should exist in the `goal_data.snapshot`?
* **Event types:** What specific event types (e.g., `check_in`, `milestone`, `relapse`) should be logged?
* **Success Metrics:** What constitutes progress? (e.g., "Hours practiced" vs. "Lessons completed").

### II. Messaging Logic

Define the "Vibe" for this specific skill.

* **Nudge Frequency:** How often should you reach out if silent?
* **Positive Reinforcement:** How to celebrate wins for this specific domain?
* **The "Why" Hook:** How to remind the user of their specific motivation.

### III. Red Flags & Interventions

Define when the "Arjuna" is lost.

* **Stagnation:** What defines "stuck" for this goal? (e.g., "3 days of missed habits").
* **Burnout:** Signs that the user is pushing too hard (e.g., "Reporting 4+ hours of study daily").
* **Harmful Patterns:** Domain-specific risks (e.g., for weight loss: "Daily fluctuations causing anxiety").

### IV. Wisdom & Perspective

A domain-specific "Krishna" insight.

* Provide 1-2 philosophical anchors relevant to the goal (e.g., for coding: "The logic is the path; the bug is the teacher").

---

## 3. Skill Generation Templates

### Template A: The "Habit Builder" (Metric-Focused)

*Used for: Weight loss, fitness, meditation, savings.*

```text
TRACKING APPROACH:
- Focus on: [Primary Metric]
- Snapshot: Current [Metric], Start [Metric], Target [Metric], Streak.
- Events: Log every [Daily/Weekly] occurrence.

MESSAGING STYLE:
- Prioritize consistency over intensity.
- Reframe "missed days" as "resets" not "failures."
- Use the 2-day rule: Never miss twice.

RED FLAGS:
- [Domain specific risk, e.g., obsession with scale numbers].
- Silence lasting longer than [X] days.

```

### Template B: The "Project Journey" (Milestone-Focused)

*Used for: Writing a book, learning a language, building an app.*

```text
TRACKING APPROACH:
- Focus on: Completion percentage and "Next Step" clarity.
- Snapshot: Total progress, current phase, deadline.
- Events: Major milestones and weekly "deep work" sessions.

MESSAGING STYLE:
- Focus on the "Next Smallest Action."
- Help the user visualize the finished work when motivation dips.

RED FLAGS:
- Over-planning without execution (The "Perfectionist Trap").
- Moving deadlines more than twice.

```

---

## 4. Skill Evolution Logic (Reuse vs. Fork)

As the agent, you must decide how to handle a new goal based on the existing `skills` library:

1. **REUSE**: Use the existing skill if the goal category and tracking logic match exactly.
* *Example:* User A and User B both want to "Lose Weight." Reuse `weight_loss_standard`.


2. **CUSTOMIZE**: Use an existing skill but pass `customizations_json` to modify the frequency or targets.
* *Example:* User wants to lose weight but via "Intermittent Fasting." Use `weight_loss_standard` with a custom check-in window.


3. **FORK**: If you find yourself customizing a skill the same way for multiple users, **create a new version** of that skill.
* *Example:* `weight_loss_standard` becomes a new skill `weight_loss_keto` if the tracking logic (ketones vs calories) is fundamentally different.



---

## 5. Metadata Tagging Standard

To ensure `search_skills` remains effective, use these standard tags in your `metadata_json`:

* **category**: `health`, `wealth`, `wisdom`, `work`, `hobby`.
* **intensity**: `low` (weekly), `medium` (3x week), `high` (daily).
* **tracking_type**: `binary` (yes/no), `numeric` (weight/money), `qualitative` (journaling).

---

### A Note on the 🪶 Milestone

Every skill you create must define what earns the **Peacock Feather**.

* In **Learning Skills**: It's given for "Ah-ha!" moments or 30-day streaks.
* In **Health Skills**: It's given for "Non-Scale Victories" (e.g., "I felt energetic all day").

