import json
with open("Configuration.json","r") as f:
    x = json.load(f)
print ("dictionary loaded from JSON file" + str(x))

KEY_SAVINGS = 'savings'

def calcSavings(current, previous):
    if (previous == {}):
        current[KEY_SAVINGS] = 5 #XXX load from config 
    else:
        current[KEY_SAVINGS] = previous[KEY_SAVINGS] + 1
        
def calcYear(current, previous):
    calcSavings(current, previous)
    
    
