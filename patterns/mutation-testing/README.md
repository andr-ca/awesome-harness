# Mutation Testing

Index for this directory. Each doc is the source of truth for its topic.

Applies at **Production tier** when test suite quality needs to be
verified beyond line/branch coverage. See
`.github/CODING_GUIDELINES.md#rigor-tiers` for what applies at other tiers.

The on-demand skill at `.claude/skills/mutation-testing/SKILL.md` is the
condensed day-to-day reference. The doc below is the canonical source it
summarises.

| Doc | Covers |
|---|---|
| [MUTATION_TESTING.md](./MUTATION_TESTING.md) | What mutation testing is, mutation operators, mutation score thresholds, tooling (mutmut / Stryker / gremlins), interpreting surviving mutants, and cost management |

**Read MUTATION_TESTING.md first.** It explains why line/branch coverage
alone is insufficient and when mutation testing adds real value versus
when the cost doesn't justify it.
