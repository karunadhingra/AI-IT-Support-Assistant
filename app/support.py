def diagnose_problem(problem):
    problem = problem.lower()

    if "wifi" in problem or "wi-fi" in problem:
        return {
            "category": "Network",
            "diagnosis": "The problem may be related to Wi-Fi connectivity.",
            "steps": [
                "Check whether Wi-Fi is enabled.",
                "Restart the Wi-Fi connection.",
                "Check whether other devices can connect to the same network.",
                "Restart the router if other devices are also disconnected."
            ]
        }

    elif "slow" in problem or "slow computer" in problem:
        return {
            "category": "Performance",
            "diagnosis": "The computer may be experiencing a performance issue.",
            "steps": [
                "Check which applications are currently running.",
                "Close unnecessary applications.",
                "Check available storage space.",
                "Restart the computer."
            ]
        }

    elif "bluetooth" in problem:
        return {
            "category": "Bluetooth",
            "diagnosis": "The problem may be related to Bluetooth connectivity.",
            "steps": [
                "Make sure Bluetooth is enabled.",
                "Check whether the device is discoverable.",
                "Remove and reconnect the Bluetooth device.",
                "Restart Bluetooth."
            ]
        }

    elif "audio" in problem or "sound" in problem:
        return {
            "category": "Audio",
            "diagnosis": "The problem may be related to the audio device or settings.",
            "steps": [
                "Check the volume level.",
                "Make sure the correct output device is selected.",
                "Reconnect headphones or speakers.",
                "Restart the audio application."
            ]
        }

    else:
        return {
            "category": "Unknown",
            "diagnosis": "I could not confidently identify the problem category.",
            "steps": [
                "Describe the problem in more detail.",
                "Mention what you expected to happen.",
                "Mention what actually happened."
            ]
        }