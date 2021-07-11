import json

CONFIG_SAVINGS = 'savings' # savings at start year
CONFIG_EXPENSES = 'expenses' # monthly expenses during start year
CONFIG_INFLATION = 'inflation' # annual inflation percentage

KEY_YEAR = 'year'
KEY_SAVINGS = 'savings'
KEY_EXPENSES = 'expenses'
KEY_INCOME_WORK_HUSBAND = 'incomeworkhusband'
KEY_INCOME_WORK_WIFE = 'incomeworkwife'

OUTPUT_KEYS = [(KEY_YEAR, "%d")
               , (KEY_SAVINGS, "%.2f")
               , (KEY_EXPENSES, "%.2f")
               , (KEY_INCOME_WORK_HUSBAND, "%.2f")
               , (KEY_INCOME_WORK_WIFE, "%.2f")
              ]

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

def outputYearsHtml(years):
    with open('Results.html', "w") as of:
        of.write("<HTML><BODY><TABLE>\n")

        of.write("<TR>")
        for keytup in OUTPUT_KEYS:
            of.write("<TH>"+keytup[0]+"</TH>")
        of.write("</TR>\n")

        for year in years:
            of.write("<TR>")
            for keytup in OUTPUT_KEYS:
                of.write("<TD>"+(keytup[1] % year[keytup[0]])+"</TD>")
            of.write("</TR>\n")

        of.write("</TABLE></BODY></HTML>\n")

#------------------ Main loop

def main():
    with open("Configuration.json","r") as f:
        global config
        config = json.load(f)
    validateConfig()

    years = []
    previous = None
    for year in range(2021, 2071):
        current = {KEY_YEAR : year}
        calcYear(current, previous)
        years.append(current)
        previous = current

    outputYearsHtml(years)

main()
