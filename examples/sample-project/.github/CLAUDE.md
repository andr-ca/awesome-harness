# Sample Project — Claude Instructions

This sample project integrates the agentharness for shared conventions and skills.

## Harness Integration

Skills and hooks are symlinked from the harness:

```
.claude/skills/      → ~/agentharness/.claude/skills/
.github/hooks/       → ~/agentharness/.github/hooks/
```

This means updates to the harness skills are immediately available here.

## How to Use

### Before Creating a Branch
```
Read: .claude/skills/branching/SKILL.md
```

### Before Committing
```
Read: .claude/skills/committing/SKILL.md
```

### Python Code
```
Read: .claude/skills/python-conventions/SKILL.md
```

## Rigor Tier

This sample project uses **Internal Tool** tier (see `.github/CODING_GUIDELINES.md#rigor-tiers`).

That means:
- ✅ 50%+ coverage (not 80%)
- ✅ No mandatory Playwright testing
- ✅ Logging is optional

## What "Done" Means

Before marking any task complete:
1. ✅ Tests pass (if applicable)
2. ✅ Changes are committed (see branching/committing skills)
3. ✅ PR created (git push + gh pr create)
4. ✅ Review completed

See `.claude/skills/committing/SKILL.md` for the full workflow.

## Links

- Full harness: `~/agentharness/`
- Integration guide: `~/agentharness/docs/INTEGRATION.md`
- Coding guidelines: See symlinked `.github/CODING_GUIDELINES.md`
