# Transport.py
# Lovense command transports not present in the upstream RemoteMCP sample.
#
# Kept separate from Functions.py so that upstream-sourced code and original
# work stay cleanly separable -- see README.md for provenance.

import requests

def SendPattern(domainUrl, toys, rule, strength, time_sec):
    """
    Send a custom pattern to Lovense toys, e.g. rule "V:1;F:v;S:500#" with
    strength "5;10;15;20;10". The strength sequence loops until timeSec elapses.

    Uses apiVer 2, which the Game Mode endpoint requires for Pattern. Note that
    pump and rotation strength are derived from the vibration values, so a
    pattern cannot drive them on an independent curve; Scheduler.py exists for
    that case.
    """
    url = f"{domainUrl}/command"
    data = {
        "command": "Pattern",
        "rule": rule,
        "strength": strength,
        "timeSec": time_sec,
        "toy": toys,
        "apiVer": 2
    }

    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SendPattern Response: {result}")
        return result
    else:
        print(f"❌ SendPattern Failed. Status Code: {response.status_code}")
        return None
