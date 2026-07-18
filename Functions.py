# Functions.py
# Send basic functions to Lovense toys (vibration, movement, etc.)

import requests

def SendFunctions(domainUrl,toys, commands, time_sec):
    """
    Send function command(s) to Lovense toys, e.g. "Vibrate:10" or "Vibrate:10,Rotate:5".
    """
    url = f"{domainUrl}/command"
    data = {
        "command": "Function",
        "action": commands,
        "timeSec": time_sec,
        "toy": toys,
        "apiVer": 1
    }

    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SendFunctions Response: {result}")
        return result
    else:
        print(f"❌ SendFunctions Failed. Status Code: {response.status_code}")
        return None

def GetToys(domainUrl):
    """
    Query the connected toy list from the Game Mode API.
    """
    url = f"{domainUrl}/command"
    data = {
        "command": "GetToys",
        "apiVer": 1
    }

    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ GetToys Response: {result}")
        return result
    else:
        print(f"❌ GetToys Failed. Status Code: {response.status_code}")
        return None

def SendPreset(domainUrl, toys, preset_name, time_sec):
    """
    Send a built-in preset pattern (Pulse, Wave, Fireworks, Earthquake) to Lovense toys.
    """
    url = f"{domainUrl}/command"
    data = {
        "command": "Preset",
        "name": preset_name,
        "timeSec": time_sec,
        "toy": toys,
        "apiVer": 1
    }

    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SendPreset Response: {result}")
        return result
    else:
        print(f"❌ SendPreset Failed. Status Code: {response.status_code}")
        return None
