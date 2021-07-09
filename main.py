import json
with open("Configuration.json","r") as f:
    x = json.load(f)
print ("dictionary loaded from JSON file" + str(x))
