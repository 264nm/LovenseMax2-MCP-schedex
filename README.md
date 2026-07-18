# RemoteMCP — extended

An MCP server for driving Lovense toys, built on Lovense's official RemoteMCP sample
with added multi-channel scripting, custom presets, and corrected input validation.

## ⚠️ Licensing — read before making this repository public

**This repository should stay private as-is.** It contains code from Lovense's official
sample, which carries **no license**:

- [developer.lovense.com/docs/ai/remote-mcp.html](https://developer.lovense.com/docs/ai/remote-mcp.html)
- [cdn.lovense.com/UploadFiles/mcp/RemoteMCP.zip](https://cdn.lovense.com/UploadFiles/mcp/RemoteMCP.zip)

No LICENSE file, copyright header, or terms of use appear in the zip, on the docs page,
or on [Lovense's GitHub org](https://github.com/lovense). Absence of a license is not
permission — under default copyright, all rights are reserved and no redistribution right
has been granted. A free download is not a license grant.

Files are kept separable so this can be resolved without untangling anything:

| File | Provenance |
|---|---|
| `Functions.py` | **Upstream Lovense**, unmodified |
| `StopFunction.py` | **Upstream Lovense**, unmodified |
| `RemoteMCP.py` | **Mixed** — upstream skeleton, with added tools and validation |
| `Transport.py` | Original |
| `Patterns.py` | Original |
| `Scheduler.py` | Original |

**To publish publicly:** drop `Functions.py` and `StopFunction.py`, replace `RemoteMCP.py`
with a thin registration layer of your own, and have users fetch the official zip
themselves. That distributes only original work rather than redistributing Lovense's.

Not legal advice — if it matters, check the terms you accepted on the Lovense developer
portal, which govern regardless of what the public pages say.

## Setup

```bash
cp .mcp.json.example .mcp.json    # then fill in your own path and LAN IP
uv sync
```

Get the IP and port from Lovense Remote → Game Mode. The app's local API server only runs
while the app is foregrounded — it stops on background or screen lock, and requests then
fail with connection refused.

## Tools

| Tool | Purpose |
|---|---|
| `GetToys` | List connected toys with IDs, battery, and supported functions |
| `SendFunctions` | Direct control, e.g. `Vibrate:10,Pump:2` |
| `SendPattern` | Custom pattern from a strength sequence |
| `SendPreset` | Built-in presets, or a named preset from `Patterns.py` |
| `PlayScript` | Multi-channel script with independent per-channel curves |
| `SendStopFunction` | Stop everything, including a running script |

### Strength ranges

**Vibrate and Rotate accept 0–20, but Pump only accepts 0–3.** The upstream sample did not
enforce this, so out-of-range pump values were silently clamped to maximum — a pattern
sweeping 0–20 across `v,p` held suction at full for most of its run rather than following
the intended arc. Both entry points now validate per-feature ceilings.

One subtlety: when a pattern lists `v,p` together, the strength list *is* the vibration
curve and pump is derived from it, so 0–20 remains legal there. Only a pump-only pattern
caps at 3.

### Patterns vs scripts

The `Pattern` command derives pump and rotation strength from the vibration values, so it
**cannot** give them an independent curve. The trade-off:

- **`SendPattern` / `SendPreset`** — uploaded once and executed on the phone, so playback
  survives a dropped connection. Single curve only.
- **`PlayScript`** — issues timed commands so vibration and suction can counterpoint each
  other, but needs the connection alive for the whole run.

`Patterns.py` carries an `edgeplay` single-curve fallback mirroring the `edgeplay` script,
for when the connection is unreliable.

## Presets

| Name | Type | Length | Notes |
|---|---|---|---|
| `slowburn` | pattern | 50s loop | Tease → build → burst arc |
| `edgeplay` | pattern | 300s | Single-curve fallback for the script below |
| `edgeplay_motif` | pattern | 20s | Shareable distillation, fits the in-app editor |
| `edgeplay` | script | 300s | Dual-channel, vibration and suction alternating |

### Design basis

`edgeplay` is built on measured physiology rather than intuition:

- **Sustained amplitude is the lever that crosses threshold.** At a fixed 100 Hz, 1mm
  peak-to-peak amplitude produced ejaculation in 32% of men versus 96% at 2.5mm — amplitude
  mattered, frequency did not (Sønksen et al. 1994,
  [10.1038/sc.1994.105](https://doi.org/10.1038/sc.1994.105)). Hence three 75-second
  plateaus rather than spikes.
- **Vibrotactile adaptation is central, not peripheral.** Cuneate-neuron responsiveness
  stays depressed with recovery measured in minutes, and it generalizes to skin sites that
  were never stimulated (O'Mara, Rowe & Tarvin 1988,
  [10.1152/jn.1988.59.2.607](https://doi.org/10.1152/jn.1988.59.2.607)). Sub-second dips
  restore nothing — a correction to `slowburn`, whose original comment claimed otherwise.
- **Adaptation is channel-specific**, with a 1.5–2 minute time constant; a 10 Hz adapter
  barely raises a 50 Hz threshold (Hollins et al. 1990,
  [10.3109/08990229009144707](https://doi.org/10.3109/08990229009144707)). Vibration
  (rapidly-adapting receptors) and suction (slowly-adapting) are therefore alternated so
  each channel rests while the other leads.
- **Arousal lowers detection thresholds** at 30/60/100 Hz (Jiao et al. 2007,
  [10.1007/s10508-007-9232-x](https://doi.org/10.1007/s10508-007-9232-x)), so perceived
  intensity rises on its own and absolute output need not climb linearly.

Literature retrieved via PubMed.

### Sharing

The in-app pattern editor works on a 10–30 second timeline, so a 5-minute arc cannot be
represented there. `edgeplay_motif` is the 20-second signature shape to redraw in the
editor and share via long-press. There is no documented text-import path into the app.
