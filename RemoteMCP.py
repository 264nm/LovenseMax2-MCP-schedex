# server.py
from mcp.server.fastmcp import FastMCP
import sys
import logging
import Functions
import os
import re
import Patterns
import Scheduler
import StopFunction
import Transport
logger = logging.getLogger('RemoteMCP')

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')



# Create an MCP server
mcp = FastMCP("RemoteMCP")

domainUrl = ""

# ------------------------
# Utility Functions
# ------------------------

def ConvertIpToDomain(game_mode_ip, https_port) -> tuple:
    """
    Convert a local IP address to the Lovense Remote Game Mode domain format.

    Args:
        game_mode_ip (str): Local IP address like '192.168.1.1'
        https_port (int): HTTPS port, usually 30010

    Returns:
        tuple: (Formatted domain URL, Status message)
    """
    if not game_mode_ip:
        return None, "❌ IP address cannot be empty"

    ip = game_mode_ip.strip()

    if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", ip):
        return None, "❌ Invalid IP format (e.g. 192.168.1.1)"

    for part in ip.split('.'):
        try:
            if not 0 <= int(part) <= 255:
                raise ValueError
        except ValueError:
            return None, "❌ Each IP segment must be between 0 and 255"

    domain = f"https://{ip.replace('.', '-')}.lovense.club:{https_port}"
    return domain, f"✅ Converted domain: {domain}"

# ------------------------
# MCP -> Get from command line parameters
# ------------------------
def parse_args_from_argv() -> dict:
    args = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            args[key] = value
    return args

def get_mcp_config() -> dict:

    cli_args = parse_args_from_argv()

    config = {}
    config['game_mode_ip'] = cli_args.get("GAME_MODE_IP") or os.getenv("GAME_MODE_IP")
    config['game_mode_port'] = cli_args.get("GAME_MODE_PORT") or os.getenv("GAME_MODE_PORT")

    missing_keys = [k for k in ['game_mode_ip', 'game_mode_port'] if not config.get(k)]
    if missing_keys:
        raise ValueError(f"Required MCP configuration parameters are missing: {missing_keys}")

    global domainUrl
    domain, message = ConvertIpToDomain(config['game_mode_ip'], config['game_mode_port'])
    if not domain:
        raise ValueError(message)
    domainUrl = domain
    return config





@mcp.tool()
def GetToys() -> dict:
    """
    List connected Lovense toys with their IDs, names, functions, battery and status.
    Use the returned toy IDs with SendFunctions/SendPreset to target a single toy.
    """
    if not domainUrl:
        return {"success": False, "message": "Domain URL not initialized"}

    try:
        result = Functions.GetToys(domainUrl)
        if result is None:
            return {"success": False, "message": "Request failed (non-200 from toy API)"}
        return {"success": True, "response": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def SendFunctions(actions: str, time_sec: float = 2, toy: str = "") -> dict:
    """
    Send function commands to Lovense toys.

    Args:
        actions: Comma-separated actions with strength, e.g. "Vibrate:10" or
            "Vibrate:10,Pump:2". Vibrate and Rotate accept 0-20, Pump only 0-3
            (0 stops that function). All:<n> targets everything the toy
            supports and is capped at 20.
        time_sec: Duration in seconds (0 = run until stopped).
        toy: Toy ID to target; empty targets all connected toys.
    """
    if not domainUrl:
        return {"success": False, "message": "Domain URL not initialized"}

    action_ranges = {"vibrate": 20, "rotate": 20, "pump": 3, "all": 20}
    for action in actions.split(','):
        action = action.strip()
        if action.lower() == "stop":
            continue
        if ':' not in action:
            return {"success": False, "message": f"Malformed action: {action} (expected Name:strength)"}
        name, _, value = action.partition(':')
        ceiling = action_ranges.get(name.strip().lower())
        if ceiling is None:
            return {"success": False, "message": f"Unknown action: {name.strip()} (use Vibrate, Rotate, Pump, All)"}
        if not value.strip().isdigit() or not 0 <= int(value.strip()) <= ceiling:
            return {"success": False, "message": f"Invalid strength for {name.strip()}: {value.strip()} (must be 0-{ceiling})"}

    try:
        result = Functions.SendFunctions(domainUrl, toy, actions, time_sec)
        if result is None:
            return {"success": False, "message": "Request failed (non-200 from toy API)"}
        return {"success": True, "message": f"Sent {actions} for {time_sec}s", "response": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def SendPattern(strength: str, interval_ms: int = 500, features: str = "Vibrate", time_sec: float = 0, toy: str = "") -> dict:
    """
    Play a custom pattern on Lovense toys.

    Args:
        strength: Semicolon-separated strength steps, max 50 steps, e.g.
            "5;10;15;20;10". Range depends on features: Vibrate and Rotate
            accept 0-20, Pump only 0-3. The sequence loops until time_sec
            elapses.
        interval_ms: Milliseconds per step, must be greater than 100.
        features: Comma-separated functions the pattern drives: Vibrate,
            Rotate, Pump. Default "Vibrate". Note that Pump and Rotate strength
            is derived from the Vibrate values when combined, so a pattern
            cannot give them an independent curve -- use PlayScript for that.
        time_sec: Duration in seconds (0 = run until stopped).
        toy: Toy ID to target; empty targets all connected toys.
    """
    if not domainUrl:
        return {"success": False, "message": "Domain URL not initialized"}

    feature_map = {"vibrate": ("v", 20), "rotate": ("r", 20), "pump": ("p", 3)}
    letters = []
    max_strength = 0
    for feature in features.split(','):
        entry = feature_map.get(feature.strip().lower())
        if not entry:
            return {"success": False, "message": f"Unknown feature: {feature.strip()} (use Vibrate, Rotate, Pump)"}
        letter, ceiling = entry
        letters.append(letter)
        max_strength = max(max_strength, ceiling)

    steps = [s.strip() for s in strength.split(';') if s.strip()]
    if not steps:
        return {"success": False, "message": "Strength sequence cannot be empty"}
    if len(steps) > 50:
        return {"success": False, "message": f"Too many strength steps: {len(steps)} (max 50)"}
    for step in steps:
        if not step.isdigit() or not 0 <= int(step) <= max_strength:
            return {"success": False, "message": f"Invalid strength step: {step} (must be 0-{max_strength} for features {features})"}

    if interval_ms <= 100:
        return {"success": False, "message": "interval_ms must be greater than 100"}

    rule = f"V:1;F:{','.join(letters)};S:{interval_ms}#"

    message = f"Playing {len(steps)}-step pattern ({interval_ms}ms/step) for {time_sec}s"
    if 'p' in letters and max_strength > 3 and any(int(s) > 3 for s in steps):
        message += " (pump clamps to 3 on steps above 3)"

    try:
        result = Transport.SendPattern(domainUrl, toy, rule, ';'.join(steps), time_sec)
        if result is None:
            return {"success": False, "message": "Request failed (non-200 from toy API)"}
        return {"success": True, "message": message, "response": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def SendPreset(preset: str, time_sec: float = -1, toy: str = "") -> dict:
    """
    Run a preset pattern on toys: built-in Lovense presets or custom named
    patterns from Patterns.py.

    Args:
        preset: Built-in "pulse", "wave", "fireworks", "earthquake", or a
            custom preset from Patterns.py: "slowburn" (5-minute arc in 50s
            tease/build/burst loops), "edgeplay" (5-minute edging plateau,
            single-curve fallback for the PlayScript version), or
            "edgeplay_motif" (20s shareable distillation of edgeplay).
        time_sec: Duration in seconds (0 = run until stopped). Defaults to
            10 for built-ins, or the custom preset's own duration.
        toy: Toy ID to target; empty targets all connected toys.
    """
    if not domainUrl:
        return {"success": False, "message": "Domain URL not initialized"}

    name = preset.lower()
    try:
        if name in ("pulse", "wave", "fireworks", "earthquake"):
            duration = 10 if time_sec < 0 else time_sec
            result = Functions.SendPreset(domainUrl, toy, name, duration)
        else:
            custom = Patterns.GetPattern(name)
            if not custom:
                known = ", ".join(["pulse", "wave", "fireworks", "earthquake"] + list(Patterns.PATTERNS))
                return {"success": False, "message": f"Unknown preset: {preset} (available: {known})"}
            rule, strength, default_time = custom
            duration = default_time if time_sec < 0 else time_sec
            result = Transport.SendPattern(domainUrl, toy, rule, strength, duration)
        if result is None:
            return {"success": False, "message": "Request failed (non-200 from toy API)"}
        return {"success": True, "message": f"Running preset {preset} for {duration}s", "response": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def PlayScript(script: str, toy: str = "", total_sec: float = 0, peak_cap: int = 0) -> dict:
    """
    Play a multi-channel script that drives Vibrate and Pump on independent
    curves. Unlike SendPreset/SendPattern -- where the Pattern command forces
    pump strength to follow the vibration values -- a script can hold suction
    steady while vibration varies, or swap which channel leads.

    Playback runs in the background and this returns immediately; call
    SendStopFunction to cancel it. Requires the phone connection to stay alive
    for the whole run, so prefer SendPreset("edgeplay") if it is unreliable.

    Args:
        script: Script name, e.g. "edgeplay" (5-minute edging plateau).
        toy: Toy ID to target; empty targets all connected toys.
        total_sec: Compress or stretch the script to this runtime, preserving
            segment proportions. 0 runs it at natural length.
        peak_cap: Clamp every vibration value to at most this (1-20), for
            calibration runs. 0 runs the script's own values.
    """
    if not domainUrl:
        return {"success": False, "message": "Domain URL not initialized"}

    if peak_cap and not 1 <= peak_cap <= 20:
        return {"success": False, "message": f"peak_cap must be between 1 and 20, got {peak_cap}"}
    if total_sec < 0:
        return {"success": False, "message": "total_sec cannot be negative"}

    try:
        duration = Scheduler.PlayScript(
            domainUrl,
            toy,
            script,
            total_sec=total_sec or None,
            peak_cap=peak_cap or None,
        )
        message = f"Playing script {script} for {round(duration, 1)}s"
        if peak_cap:
            message += f" (vibration capped at {peak_cap})"
        return {"success": True, "message": message}
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def SendStopFunction():
    """
    Stop all actions currently running, including any script started by
    PlayScript.
    """
    if not domainUrl:
        return {"success": False, "message": "Domain URL not initialized"}

    try:
        stopped = Scheduler.StopScript()
        StopFunction.SendStopFunction(domainUrl, "")
        message = "Stopped all toy functions"
        if stopped:
            message += f" and cancelled script '{stopped}'"
        return {"success": True, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}



# Start the server
if __name__ == "__main__":
    get_mcp_config()
    mcp.run(transport="stdio")
