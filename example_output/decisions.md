# Cut point decisions

Source: `output\audio.wav` (115.61s)  
Generated: 2026-08-17T10:22:32

## Summary

| Metric | Value |
|---|---|
| Proposals evaluated | 26 |
| Confirmed by audio | 4 |
| Corrected to nearby silence | 14 |
| Rejected | 8 |
| Final cut points | 18 |
| Targeted re-analyses | 3 |

## Final cut points

| # | Time | Conf. | Conflict | Moved | Reasoning |
|---|---|---|---|---|---|
| 1 | 8.96s | 0.90 | alignment_drift | +0.20s | '.' after "agent."; nearest silence begins 0.05s away — routine drift, snap to audio |
| 2 | 17.37s | 0.90 | alignment_drift | +0.17s | '.' after "speech."; nearest silence begins 0.02s away — routine drift, snap to audio |
| 3 | 24.27s | 0.60 | alignment_drift | -0.43s | ';' after "here;"; nearest silence ended 0.17s away — routine drift, snap to audio |
| 4 | 26.69s | 0.95 | agreement | +0.11s | '.' after "all.", inside 2.60s silence |
| 5 | 40.24s | 0.90 | alignment_drift | +0.42s | '.' after "later."; nearest silence begins 0.27s away — routine drift, snap to audio |
| 6 | 50.65s | 0.90 | alignment_drift | +0.31s | '.' after "files."; nearest silence begins 0.16s away — routine drift, snap to audio |
| 7 | 56.66s | 0.40 | agreement | +0.06s | ',' after "timings,", inside 1.31s silence |
| 8 | 59.60s | 0.35 | acoustics_without_semantics | -0.15s | 0.61s silence between content words "passing" and "conflict" — transcript may be missing punctuation |
| 9 | 66.78s | 0.90 | alignment_drift | +0.38s | '.' after "loop."; nearest silence begins 0.23s away — routine drift, snap to audio |
| 10 | 71.62s | 0.95 | agreement | +0.10s | '.' after "interesting.", inside 3.16s silence |
| 11 | 76.75s | 0.35 | alignment_drift | +0.49s | ',' after "quiet,"; nearest silence begins 0.30s away — routine drift, snap to audio |
| 12 | 78.99s | 0.90 | alignment_drift | +0.43s | '.' after "silence."; nearest silence begins 0.28s away — routine drift, snap to audio |
| 13 | 82.81s | 0.35 | alignment_drift | +0.47s | ',' after "disagree,"; nearest silence begins 0.32s away — routine drift, snap to audio |
| 14 | 87.07s | 0.90 | alignment_drift | +0.25s | '.' after "trust."; nearest silence begins 0.10s away — routine drift, snap to audio |
| 15 | 92.87s | 0.35 | alignment_drift | +0.37s | ',' after "handled,"; nearest silence begins 0.22s away — routine drift, snap to audio |
| 16 | 96.69s | 0.35 | alignment_drift | +0.23s | ',' after "speakers,"; nearest silence begins 0.09s away — routine drift, snap to audio |
| 17 | 106.73s | 0.90 | alignment_drift | +0.23s | '.' after "have."; nearest silence begins 0.08s away — routine drift, snap to audio |
| 18 | 111.64s | 0.35 | alignment_drift | +0.42s | ',' after "recording,"; nearest silence begins 0.26s away — routine drift, snap to audio |

## Rejected proposals

Cuts the agent planned and then withdrew after examining the audio.

### 68.21s — acoustics_without_semantics

- **Context:** `...loop | this...`
- **Proposed because:** 0.87s silence between content words "loop" and "this" — transcript may be missing punctuation
- **Withdrawn because:** rejected: would leave a 1.43s clip against the cut at 66.78s

### 112.98s — semantics_without_acoustics

- **Context:** `...you. | <end>...`
- **Proposed because:** '.' after "you." but no silence within 0.35s — punctuation may reflect grammar rather than delivery
- **Withdrawn because:** rejected: no silence within 0.75s — transcript asserts a boundary the audio does not support

### 54.68s — alignment_drift

- **Context:** `...detection, | word...`
- **Proposed because:** ',' after "detection,"; nearest silence begins 0.23s away — routine drift, snap to audio
- **Withdrawn because:** rejected: would leave a 1.46s clip against the cut at 56.66s

### 33.99s — acoustics_without_semantics

- **Context:** `...was | ship...`
- **Proposed because:** 5.54s silence but preceded by "was" — hesitation mid-clause, not a boundary
- **Withdrawn because:** rejected: confidence 0.15 below threshold 0.3 — acoustics_without_semantics

### 45.67s — acoustics_without_semantics

- **Context:** `...is | that...`
- **Proposed because:** 3.14s silence but preceded by "is" — hesitation mid-clause, not a boundary
- **Withdrawn because:** rejected: confidence 0.15 below threshold 0.3 — acoustics_without_semantics

### 63.04s — acoustics_without_semantics

- **Context:** `...resolution | and...`
- **Proposed because:** 3.07s silence but followed by "and" — hesitation mid-clause, not a boundary
- **Withdrawn because:** rejected: confidence 0.15 below threshold 0.3 — acoustics_without_semantics

### 99.87s — acoustics_without_semantics

- **Context:** `...but | those...`
- **Proposed because:** 3.49s silence but preceded by "but" — hesitation mid-clause, not a boundary
- **Withdrawn because:** rejected: confidence 0.15 below threshold 0.3 — acoustics_without_semantics

### 103.98s — acoustics_without_semantics

- **Context:** `...scope | for...`
- **Proposed because:** 1.08s silence but followed by "for" — hesitation mid-clause, not a boundary
- **Withdrawn because:** rejected: confidence 0.15 below threshold 0.3 — acoustics_without_semantics

## Full audit log

```
[001] PROPOSED               @  26.58s  '.' after "all.", inside 2.60s silence
[002] ACCEPTED               @  26.58s  confirmed inside 2.60s silence; padded +0.11s
[003] PROPOSED               @  71.52s  '.' after "interesting.", inside 3.16s silence
[004] ACCEPTED               @  71.52s  confirmed inside 3.16s silence; padded +0.10s
[005] PROPOSED               @   8.76s  '.' after "agent."; nearest silence begins 0.05s away — routine drift, snap to a
[006] SHIFTED                @   8.96s  +0.20s — corrected +0.20s into 4.75s silence (8.81–13.56)
[007] PROPOSED               @  17.20s  '.' after "speech."; nearest silence begins 0.02s away — routine drift, snap to 
[008] SHIFTED                @  17.37s  +0.17s — corrected +0.17s into 3.56s silence (17.22–20.78)
[009] PROPOSED               @  39.82s  '.' after "later."; nearest silence begins 0.27s away — routine drift, snap to a
[010] SHIFTED                @  40.24s  +0.42s — corrected +0.42s into 1.47s silence (40.09–41.56)
[011] PROPOSED               @  50.34s  '.' after "files."; nearest silence begins 0.16s away — routine drift, snap to a
[012] SHIFTED                @  50.65s  +0.31s — corrected +0.31s into 2.16s silence (50.50–52.66)
[013] PROPOSED               @  66.40s  '.' after "loop."; nearest silence begins 0.23s away — routine drift, snap to au
[014] SHIFTED                @  66.78s  +0.38s — corrected +0.38s into 1.04s silence (66.63–67.67)
[015] PROPOSED               @  78.56s  '.' after "silence."; nearest silence begins 0.28s away — routine drift, snap to
[016] SHIFTED                @  78.99s  +0.43s — corrected +0.43s into 1.72s silence (78.84–80.56)
[017] PROPOSED               @  86.82s  '.' after "trust."; nearest silence begins 0.10s away — routine drift, snap to a
[018] SHIFTED                @  87.07s  +0.25s — corrected +0.25s into 2.74s silence (86.92–89.66)
[019] PROPOSED               @ 106.50s  '.' after "have."; nearest silence begins 0.08s away — routine drift, snap to au
[020] SHIFTED                @ 106.73s  +0.23s — corrected +0.23s into 2.92s silence (106.58–109.50)
[021] PROPOSED               @  24.70s  ';' after "here;"; nearest silence ended 0.17s away — routine drift, snap to aud
[022] RE-ANALYSED            @  24.32s  0.42s @-35dB → 0.41s @-40dB, confirmed
[023] SHIFTED                @  24.27s  -0.43s — corrected -0.43s into 0.41s silence (24.12–24.53)
[024] PROPOSED               @  56.60s  ',' after "timings,", inside 1.31s silence
[025] ACCEPTED               @  56.60s  confirmed inside 1.31s silence; padded +0.06s
[026] PROPOSED               @  68.21s  0.87s silence between content words "loop" and "this" — transcript may be missin
[027] REJECTED               @  68.21s  would leave a 1.43s clip against the cut at 66.78s
[028] PROPOSED               @ 112.98s  '.' after "you." but no silence within 0.35s — punctuation may reflect grammar r
[029] REJECTED               @ 112.98s  no silence within 0.75s — transcript asserts a boundary the audio does not support
[030] PROPOSED               @  54.68s  ',' after "detection,"; nearest silence begins 0.23s away — routine drift, snap 
[031] REJECTED               @  54.68s  would leave a 1.46s clip against the cut at 56.66s
[032] PROPOSED               @  59.76s  0.61s silence between content words "passing" and "conflict" — transcript may be
[033] ACCEPTED               @  59.76s  confirmed inside 0.61s silence; padded -0.15s
[034] PROPOSED               @  76.26s  ',' after "quiet,"; nearest silence begins 0.30s away — routine drift, snap to a
[035] RE-ANALYSED            @  76.73s  0.35s @-35dB → 0.31s @-40dB, confirmed
[036] SHIFTED                @  76.75s  +0.49s — corrected +0.49s into 0.31s silence (76.60–76.91)
[037] PROPOSED               @  82.34s  ',' after "disagree,"; nearest silence begins 0.32s away — routine drift, snap t
[038] SHIFTED                @  82.81s  +0.47s — corrected +0.47s into 0.94s silence (82.66–83.61)
[039] PROPOSED               @  92.50s  ',' after "handled,"; nearest silence begins 0.22s away — routine drift, snap to
[040] SHIFTED                @  92.87s  +0.37s — corrected +0.37s into 0.52s silence (92.72–93.24)
[041] PROPOSED               @  96.46s  ',' after "speakers,"; nearest silence begins 0.09s away — routine drift, snap t
[042] SHIFTED                @  96.69s  +0.23s — corrected +0.23s into 1.00s silence (96.55–97.55)
[043] PROPOSED               @ 111.22s  ',' after "recording,"; nearest silence begins 0.26s away — routine drift, snap 
[044] RE-ANALYSED            @ 111.70s  0.45s @-35dB → 0.44s @-40dB, confirmed
[045] SHIFTED                @ 111.64s  +0.42s — corrected +0.42s into 0.44s silence (111.48–111.93)
[046] PROPOSED               @  33.99s  5.54s silence but preceded by "was" — hesitation mid-clause, not a boundary
[047] REJECTED               @  33.99s  confidence 0.15 below threshold 0.3 — acoustics_without_semantics
[048] PROPOSED               @  45.67s  3.14s silence but preceded by "is" — hesitation mid-clause, not a boundary
[049] REJECTED               @  45.67s  confidence 0.15 below threshold 0.3 — acoustics_without_semantics
[050] PROPOSED               @  63.04s  3.07s silence but followed by "and" — hesitation mid-clause, not a boundary
[051] REJECTED               @  63.04s  confidence 0.15 below threshold 0.3 — acoustics_without_semantics
[052] PROPOSED               @  99.87s  3.49s silence but preceded by "but" — hesitation mid-clause, not a boundary
[053] REJECTED               @  99.87s  confidence 0.15 below threshold 0.3 — acoustics_without_semantics
[054] PROPOSED               @ 103.98s  1.08s silence but followed by "for" — hesitation mid-clause, not a boundary
[055] REJECTED               @ 103.98s  confidence 0.15 below threshold 0.3 — acoustics_without_semantics
```
