import json

KEY_YEAR = 'year'
KEY_SAVINGS = 'savings'

def calcSavings(current, previous):
    if (previous == None):
        current[KEY_SAVINGS] = config[KEY_SAVINGS]
    else:
        current[KEY_SAVINGS] = previous[KEY_SAVINGS] + 1

def calcYear(current, previous):
    calcSavings(current, previous)

#------------------ Main loop

with open("Configuration.json","r") as f:
    config = json.load(f)

years = []
previous = None
for year in range(2021, 2071):
    current = { KEY_YEAR : year }
    calcYear( current, previous)
    years.append(current)
    previous = current

