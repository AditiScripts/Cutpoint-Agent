"""Write machine-readable and human-readable output."""

from pathlib import Path

from .state import CutPlan, CutStatus


def write_json(plan: CutPlan, path: str = "output/cuts.json") -> None:
    Path(path).parent.mkdir(exist_ok=True)
    Path(path).write_text(plan.to_json(), encoding="utf-8")
    print(f"Wrote {path}")


def write_markdown(plan: CutPlan, path: str = "output/decisions.md") -> None:
    s = plan.summary()
    lines = [
        "# Cut point decisions",
        "",
        f"Source: `{s['audio']}` ({s['duration_s']}s)  ",
        f"Generated: {s['generated']}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Proposals evaluated | {s['proposed']} |",
        f"| Confirmed by audio | {s['accepted']} |",
        f"| Corrected to nearby silence | {s['shifted']} |",
        f"| Rejected | {s['rejected']} |",
        f"| Final cut points | {s['final_cut_count']} |",
        f"| Targeted re-analyses | {s['targeted_reanalyses']} |",
        "",
        "## Final cut points",
        "",
        "| # | Time | Conf. | Conflict | Moved | Reasoning |",
        "|---|---|---|---|---|---|",
    ]

    for i, c in enumerate(plan.final_cuts(), 1):
        moved = f"{c.time - c.original_time:+.2f}s" if c.was_moved else "—"
        lines.append(
            f"| {i} | {c.time:.2f}s | {c.confidence:.2f} | "
            f"{c.conflict.value} | {moved} | {c.rationale} |"
        )

    lines += ["", "## Rejected proposals", "",
              "Cuts the agent planned and then withdrew after examining the audio.", ""]

    for c in plan.rejected():
        lines += [
            f"### {c.original_time:.2f}s — {c.conflict.value}",
            "",
            f"- **Context:** `{c.context}`",
            f"- **Proposed because:** {c.rationale}",
            f"- **Withdrawn because:** {c.history[-1] if c.history else 'n/a'}",
            "",
        ]

    lines += ["## Full audit log", "", "```"]
    lines += [str(e) for e in plan.log]
    lines += ["```", ""]

    Path(path).parent.mkdir(exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path}")