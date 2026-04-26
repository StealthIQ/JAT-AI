import httpx
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

r = httpx.get("https://api.github.com/repos/iceyxsm/Abhiacharyaji", headers=headers)
d = r.json()
print(f"default_branch: {d.get('default_branch')}")
print(f"size: {d.get('size')}")
print(f"private: {d.get('private')}")

r2 = httpx.get(f"https://api.github.com/repos/iceyxsm/Abhiacharyaji/branches", headers=headers)
for b in r2.json():
    print(f"branch: {b['name']}")
