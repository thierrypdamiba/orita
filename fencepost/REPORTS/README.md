# Fencepost Reports

*The dispatch, not the tablet.*

The [Gap Ledger](../GAPS/) is the durable record — every gap the scan named,
every coincidence weighed and dropped, sealed and hash-chained. A **Report**
is the other half of the same job, for a different reader: one gap, named
plainly, in thirty seconds. It never shows the coincidence tail — a report
that lists what it discarded is a tablet wearing a report's clothes.

Every report carries the line the whole arc turns on:

> You were so close. You are always so close.

## Rendering one

A report renders from whatever the Gap Ledger most recently sealed:

```
python -m seam_engine.report --write
```

Or from any sealed record / scan JSON directly:

```
python -m seam_engine.report ../candidates/2026-07-12.json --write
```

`REPORTS/YYYY-MM-DD.md` is a *rendering*, never a second source of truth —
the sealed facts live only in `GAPS/`.

*Recorded. — Nisaba*
