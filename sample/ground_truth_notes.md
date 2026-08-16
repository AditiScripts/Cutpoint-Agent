# Ground truth annotations — sample.mp4

Hand-annotated from a 1:55 recording made specifically for this project.
Each section was recorded to plant a known conflict between what the
transcript would say and what the audio actually contains.

| Time (approx) | Content | Planted case |
|---|---|---|
| 0:00–0:05 | (room tone) | leading silence, must be ignored |
| 0:05–0:08 | "This is a test recording for a video cutting agent." | clean control — both sources agree |
| 0:13–0:17 | "The goal is to find natural pauses in speech." | clean control |
| 0:20–0:26 | "The transcript will probably mark a sentence boundary here the audio will show nothing at all." | run-on: sentence boundary with little or no pause |
| 0:29–0:39 | "The thing I decided to do was... ship it anyway and fix the edge cases later." | 5.5s mid-clause hesitation, no punctuation |
| 0:41–0:50 | "I think the main risk is, uh... that the timings drift on longer files." | filler-word hesitation, 3.1s gap |
| 0:52–1:06 | "I need silence detection, word timings, punctuation parsing, conflict resolution, and a verification loop." | flat list: many small gaps plus one 3.1s gap with only a comma |
| 1:08–1:18 | "This next part is the one I find interesting. [audible breath] Breathing sounds are quiet but they are not actually silence." | breath swallowed inside a detected silence window |
| 1:20–1:26 | "When the sources disagree, the agent has to decide which one to trust." | comma pause, ~0.9s |
| 1:29–1:46 | "There are a few other cases I could have handled... those are out of scope... for the time limit I have." | trailing off, 3.5s gap |
| 1:49–1:53 | "That is the end of the test recording, and thank you." | clean control |
| 1:53–1:55 | (room tone) | trailing silence, must be ignored |

## Silence threshold selection

`silencedetect` was swept across four thresholds:

| Threshold | Windows | Total silence |
|---|---|---|
| -30 dB | 36 | 63.6s |
| -35 dB | 35 | 59.6s |
| -40 dB | 42 | 54.7s |
| -45 dB | 51 | 29.6s |

Window count rises below -40dB while total silence falls sharply. This is
fragmentation: the room noise floor sits near -42dB, so at -45dB room tone
repeatedly crosses the threshold and splits single pauses into many short
fragments. -30dB and -35dB produce nearly identical counts, indicating a
stable region where the result is insensitive to the exact value.

**-35dB was chosen** as it sits on that plateau, comfortably above the noise
floor. Detection also produces sub-10ms artefacts (e.g. a 1.4ms "speech"
gap at 3.835s) which the agent merges before use.