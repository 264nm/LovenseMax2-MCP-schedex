# Patterns.py
# Custom named pattern presets, played via the Pattern command in Functions.py.

# Each preset defines a strength cycle, a step interval in ms (must exceed 100),
# the features it drives (v=Vibrate, r=Rotate, p=Pump), and a default play time.
# The cycle loops until that time elapses. Max 50 steps per the Lovense spec.
#
# Important: the Pattern command derives Pump and Rotate strength from the
# Vibrate values -- it cannot give them an independent curve. Pump also only has
# levels 0-3, so any step above 3 saturates it. A pattern driving "v,p" therefore
# holds suction at full for every step above 3, and only genuinely drops it in
# troughs at 0-2. Use Scheduler.py when the channels need to move independently.
PATTERNS = {
    "slowburn": {
        # 50 steps x 1000ms = 50s act, loops 6x over the default 300s.
        # Arc: tease -> building strokes -> deepening -> burst -> release.
        # The alternating high/low pairs give a ~0.5Hz stroke cadence. This is
        # subjective texture only -- vibrotactile adaptation is central, with a
        # recovery time course measured in minutes, so sub-second dips do not
        # restore sensitivity (O'Mara, Rowe & Tarvin 1988, doi:10.1152/jn.1988.59.2.607).
        # Suction saturates from the 11th step onward; see the note above.
        "features": "v,p",
        "interval_ms": 1000,
        "time_sec": 300,
        "strength": "3;3;4;4;5;4;5;6;5;6;"
                    "8;5;9;6;10;6;11;7;12;8;13;8;"
                    "14;9;15;10;16;10;17;11;18;12;18;12;"
                    "20;14;20;15;20;16;20;16;20;18;20;18;"
                    "15;10;6;3",
    },
    "edgeplay": {
        # Single-curve fallback for the Scheduler.py "edgeplay" script, for when
        # the phone connection is too unreliable to hold open for 5 minutes.
        # 50 steps x 6000ms = exactly 300s, so the macro arc plays once.
        #
        # Threshold-biased design: sustained high amplitude is the primary lever
        # (Sonksen et al. 1994, doi:10.1038/sc.1994.105 -- at a fixed 100Hz,
        # 1mm amplitude produced ejaculation in 32% of men vs 96% at 2.5mm), so
        # the arc holds long plateaus rather than spiking. Troughs sit at 1 to
        # genuinely drop both channels, and exist to swap which receptor
        # population carries the load: vibration is rapidly-adapting, suction is
        # slowly-adapting, and the two adapt independently (Hollins et al. 1990,
        # doi:10.3109/08990229009144707).
        "features": "v,p",
        "interval_ms": 6000,
        "time_sec": 300,
        "strength": "8;9;10;11;12;"
                    "16;17;18;17;16;17;18;18;17;16;17;18;"
                    "1;1;"
                    "12;13;14;13;12;13;14;14;13;12;13;14;"
                    "1;1;"
                    "18;19;20;19;18;19;20;20;19;18;19;20;"
                    "14;14;14;14;14",
    },
    "edgeplay_motif": {
        # ~20s shareable distillation of edgeplay (40 steps x 500ms). The Lovense
        # Remote in-app pattern editor works on a 10-30s timeline, so the full
        # 5-minute arc cannot be represented there -- this is the signature shape
        # to redraw and share instead: a high sustained floor with periodic
        # swells to maximum.
        "features": "v",
        "interval_ms": 500,
        "time_sec": 20,
        "strength": "16;17;18;18;17;16;17;18;19;20;"
                    "20;19;18;17;16;17;18;19;20;20;"
                    "20;19;18;17;16;17;18;19;20;20;"
                    "19;18;17;16;15;16;17;18;19;20",
    },
}

def GetPattern(name):
    """
    Look up a named custom preset. Returns (rule, strength, default_time_sec)
    or None if the name is unknown.
    """
    preset = PATTERNS.get(name.lower())
    if not preset:
        return None
    rule = f"V:1;F:{preset['features']};S:{preset['interval_ms']}#"
    return rule, preset["strength"], preset["time_sec"]
