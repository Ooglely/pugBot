import json
import requests

uploader_steam = "76561198069079902"
ids = []

query = requests.get("https://logs.tf/api/v1/log?limit=10000&uploader=" + uploader_steam)
json_query = query.json()
for log in json_query["logs"]:
    ids.append(log["id"])

print(ids)
for id in ids:
    query = requests.get("https://logs.tf/api/v1/log/" + str(id))
    with open(f"logs/{uploader_steam}/{id}.json", "w") as f:
        json.dump(query.json(), f)
    print(f"Saved log #{id}")

