#!/usr/bin/env python3
import json
import urllib.request


def check():
    url = "http://127.0.0.1:8000/api/v1/s/Cyc6Ad4o_issuqc4_xnxbd6t8GAS5YXhp80ST-mE9E4"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print("Status 200:", data)
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code, e.read().decode())
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    check()
