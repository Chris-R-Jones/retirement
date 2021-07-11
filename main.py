import json

# Configuration keys
CONFIG_EXPENSES = 'expenses' # monthly expenses during start year
CONFIG_INFLATION = 'inflation' # annual inflation percentage
CONFIG_EXPENSES = 'expenses'

CONFIG_INCOME_SOURCES = 'incomeSources'
CONFIG_INCOME_NAME = 'name'
CONFIG_INCOME_AMOUNT = 'amount'
CONFIG_INCOME_START_YEAR = 'startYear'
CONFIG_INCOME_END_YEAR = 'endYear'
CONFIG_INCOME_START_AGE = 'startAge'
CONFIG_INCOME_END_AGE = 'endAge'

CONFIG_ACCTS = 'accounts'
CONFIG_ACCT_NAME = 'name'
CONFIG_ACCT_BALANCE = 'balance'
CONFIG_ACCT_TARGET_BALANCE = 'targetBalance'
CONFIG_ACCT_RETURN_RATE = 'returnRate'

# Output-only keys
KEY_YEAR = 'year'
CONFIG_INCOME_TOTAL = 'incomeTotal'
KEY_EXPENSES = 'expenses'

OUTPUT_KEYS = [(KEY_YEAR, "%d")
               , (KEY_EXPENSES, "%.2f")
               , (CONFIG_INCOME_TOTAL, "%.2f")
              ]

def validateConfig():
    assert config[CONFIG_EXPENSES] >= 0
    assert config[CONFIG_INFLATION] >= 0 and config[CONFIG_INFLATION] <= 1
    assert config[CONFIG_ACCTS] is not None and len(config[CONFIG_ACCTS]) > 0

def calcReturns(current, previous):
    current[CONFIG_ACCTS] = {}
    for acctName in config[CONFIG_ACCTS]:
        cfgAcct = config[CONFIG_ACCTS][acctName]
        if previous is None:
            newAcct = cfgAcct
            newAcct[CONFIG_ACCT_BALANCE] = ( cfgAcct[CONFIG_ACCT_BALANCE]
                                             * (1.0 + cfgAcct[CONFIG_ACCT_RETURN_RATE])
                                           )
        else:
            prvAcct = previous[CONFIG_ACCTS][acctName]
            newAcct = prvAcct.copy()
            newAcct[CONFIG_ACCT_BALANCE] = ( prvAcct[CONFIG_ACCT_BALANCE] 
                                             * (1.0 + cfgAcct[CONFIG_ACCT_RETURN_RATE])
                                           )
        current[CONFIG_ACCTS][acctName] = newAcct

def calcExpenses(current, previous):
    if (previous == None):
        current[KEY_EXPENSES] = config[CONFIG_EXPENSES]
    else:
        current[KEY_EXPENSES] = previous[KEY_EXPENSES] * (1 + config[CONFIG_INFLATION])

def calcIncome(current, previous):
    current[CONFIG_INCOME_TOTAL] = 0

    for incomeSource in config[CONFIG_INCOME_SOURCES]:
        if (CONFIG_INCOME_START_YEAR in incomeSource
                and CONFIG_INCOME_END_YEAR in incomeSource
                and current[KEY_YEAR] >= incomeSource[CONFIG_INCOME_START_YEAR]
                and current[KEY_YEAR] <= incomeSource[CONFIG_INCOME_END_YEAR]
           ):
            current[CONFIG_INCOME_TOTAL] += incomeSource[CONFIG_INCOME_AMOUNT]

def calcYear(current, previous):
    calcReturns(current, previous)
    calcExpenses(current, previous)
    calcIncome(current, previous)

def outputYearsHtml(years):
    with open('Results.html', "w") as of:
        of.write("<HTML><BODY><TABLE>\n")

        of.write("<TR>")
        for keytup in OUTPUT_KEYS:
            of.write("<TH>"+keytup[0]+"</TH>")
        for acctName in config[CONFIG_ACCTS]:
            of.write("<TH>"+acctName+"</TH>")
        of.write("</TR>\n")

        for year in years:
            of.write("<TR>")
            for keytup in OUTPUT_KEYS:
                of.write("<TD>"+(keytup[1] % year[keytup[0]])+"</TD>")

            for acctName in config[CONFIG_ACCTS]:
                acct = year[CONFIG_ACCTS][acctName]
                of.write("<TD>"
                         +"%.2f" % acct[CONFIG_ACCT_BALANCE]
                         +"</TD>"
                        )

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
