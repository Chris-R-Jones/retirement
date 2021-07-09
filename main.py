import json

CONFIG_SAVINGS = 'savings' # savings at start year
CONFIG_EXPENSES = 'expenses' # monthly expenses during start year
CONFIG_INFLATION = 'inflation' # annual inflation percentage

KEY_YEAR = 'year'
KEY_SAVINGS = 'savings'
KEY_EXPENSES = 'expenses'
KEY_INCOME_WORK_HUSBAND = 'incomeworkhusband'
KEY_INCOME_WORK_WIFE = 'incomeworkwife'

def validateConfig():
    assert config[CONFIG_SAVINGS] >= 0
    assert config[CONFIG_EXPENSES] >= 0
    assert config[CONFIG_INFLATION] >= 0 and config[CONFIG_INFLATION] <= 1

def calcSavings(current, previous):
    if (previous == None):
        current[KEY_SAVINGS] = config[CONFIG_SAVINGS]
    else:
        current[KEY_SAVINGS] = previous[KEY_SAVINGS] + 1

def calcExpenses(current, previous):
    if (previous == None):
        current[KEY_EXPENSES] = config[CONFIG_EXPENSES]
    else:
        current[KEY_EXPENSES] = previous[KEY_EXPENSES] * (1 + config[CONFIG_INFLATION])

def calcIncomeWork(current, previous):
    if current[KEY_YEAR] >= 2021 and current[KEY_YEAR] <= 2023: #XXX load from and to husband employment from config
        current[KEY_INCOME_WORK_HUSBAND] = 100000 #XXX load from config
    else:
        current[KEY_INCOME_WORK_HUSBAND] = 0
    if current[KEY_YEAR] >= 2021 and current[KEY_YEAR] <= 2023: #XXX load from and to wife employment from config
        current[KEY_INCOME_WORK_WIFE] = 50000 #XXX load from config
    else:
        current[KEY_INCOME_WORK_WIFE] = 0
        
def calcYear(current, previous):
    calcSavings(current, previous)
    calcExpenses(current, previous)
    calcIncomeWork(current, previous)

#------------------ Main loop

with open("Configuration.json","r") as f:
    config = json.load(f)
validateConfig()

years = []
previous = None
for year in range(2021, 2071):
    current = { KEY_YEAR : year }
    calcYear( current, previous)
    years.append(current)
    previous = current

print("YEAR SAVINGS EXPENSES INCOME_HIS INCOME_HERS")
for year in years:
    print("%4d %10.2f %10.2f %10.2f %10.2f" 
         % (year[KEY_YEAR], year[KEY_SAVINGS], year[KEY_EXPENSES]
           ,year[KEY_INCOME_WORK_HUSBAND]
           ,year[KEY_INCOME_WORK_WIFE]
           )
         )
