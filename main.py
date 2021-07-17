""" Theiding-Jones Retirement calculator
    Mostly to prove we could have retired several years ago
"""
import json

# Configuration keys
CONFIG_EXPENSES = 'expenses' # monthly expenses during start year
CONFIG_INFLATION = 'inflation' # annual inflation percentage

CONFIG_START_YEAR = 'startYear'
CONFIG_END_YEAR = 'endYear'
CONFIG_NAME = 'name'

CONFIG_INCOME_SOURCES = 'incomeSources'
CONFIG_INCOME_NAME = CONFIG_NAME # TBD needed at all?
CONFIG_INCOME_AMOUNT = 'amount'
CONFIG_INCOME_START_AGE = 'startAge'
CONFIG_INCOME_END_AGE = 'endAge'
CONFIG_INCOME_ACCOUNTS = 'incomeAccounts'

CONFIG_ACCTS = 'accounts'
CONFIG_ACCT_NAME = CONFIG_NAME # TBD needed at all?
CONFIG_ACCT_BALANCE = 'balance'
CONFIG_ACCT_TARGET_BALANCE = 'targetBalance'
CONFIG_ACCT_RETURN_RATE = 'returnRate'

KEY_INCOME_FROM_INCOME_SOURCES = 'incomeFromIncomeSources'
KEY_INCOME_FROM_ACCOUNTS = 'incomeFromAccounts'
KEY_ACCOUNT_BALANCES = 'accountBalances'
# TBD need to cleanup when to use CONFIG and KEY prefix

# Output-only keys
KEY_YEAR = 'year'
CONFIG_INCOME_TOTAL = 'incomeTotal'
KEY_EXPENSES = 'expenses'

#------------------ Config

def validate_config():
    """ Reviews configuration settings for correctness """
    assert config[CONFIG_EXPENSES] >= 0
    assert config[CONFIG_INFLATION] >= 0 and config[CONFIG_INFLATION] <= 1

    assert config[CONFIG_ACCTS] is not None and len(config[CONFIG_ACCTS]) > 0
    for acct_name in config[CONFIG_ACCTS]:
        acct = config[CONFIG_ACCTS][acct_name]
        assert acct[CONFIG_ACCT_BALANCE] is not None
        assert acct[CONFIG_ACCT_BALANCE] >= 0
        assert acct[CONFIG_ACCT_RETURN_RATE] is not None
        assert acct[CONFIG_ACCT_RETURN_RATE] >= 0
        assert (CONFIG_ACCT_TARGET_BALANCE not in acct
                or acct[CONFIG_ACCT_TARGET_BALANCE] > 0
               )

    assert (config[CONFIG_INCOME_SOURCES] is not None
            and len(config[CONFIG_INCOME_SOURCES]) > 0
           )
    for income in config[CONFIG_INCOME_SOURCES]:
        assert income[CONFIG_INCOME_NAME] is not None
        assert income[CONFIG_INCOME_AMOUNT] is not None

def load_config():
    """Loads user preferences from json configuration file"""
    with open("Configuration.json", "r") as infile:
        global config
        config = json.load(infile)
    validate_config()

#------------------ Util

def filter_year(year, src):
    """ Checks specified dictionary for CONFIG_START_YEAR / END_YEAR keys """
    return ((CONFIG_START_YEAR not in src or src[CONFIG_START_YEAR] <= year) and
            (CONFIG_END_YEAR not in src or src[CONFIG_END_YEAR] >= year)
           )

#------------------ Expenses

def calc_expenses(current, previous):
    """ Calculates yearly expenses, based on user configuration """
    if previous is None:
        current[KEY_EXPENSES] = config[CONFIG_EXPENSES]
    else:
        current[KEY_EXPENSES] = previous[KEY_EXPENSES] * (1 + config[CONFIG_INFLATION])

#------------------ Income

def calc_income(current):
    """ Calculates all types of yearly income """
    current[CONFIG_INCOME_TOTAL] = 0

    calc_income_sources(current)
    calc_income_accounts(current)

def calc_income_sources(current):
    """ Calculates yearly income from configured sources """

    incomes = {}
    for source in config[CONFIG_INCOME_SOURCES]:
        income = 0
        if filter_year(current[KEY_YEAR], source):
            income = source[CONFIG_INCOME_AMOUNT]
        incomes[source[CONFIG_NAME]] = income
        current[CONFIG_INCOME_TOTAL] += income
    current[KEY_INCOME_FROM_INCOME_SOURCES] = incomes

    # TBD -- need to adjust the above for inflation
    # TBD Mark: income is what it is regardless of inflation, but we can add support for raises)

def calc_income_accounts(current):
    """ Calculates annual gains on accounts """
    incomes = {}
    for acct_name in config[CONFIG_ACCTS]:
        income = current[KEY_ACCOUNT_BALANCES][acct_name] \
                 * config[CONFIG_ACCTS][acct_name][CONFIG_ACCT_RETURN_RATE]
        incomes[acct_name] = income
        current[CONFIG_INCOME_TOTAL] += income
    current[KEY_INCOME_FROM_ACCOUNTS] = incomes

#------------------ Account balances

def calc_account_balance(current, previous):
    """ Adjusts account balances with previous year's income and pay expenses

        TBD: to not hardcode "savings"...
    """

    if previous is None:
        # Initialize accounts to starting balance
        account_balances = {}
        for acct_name in config[CONFIG_ACCTS]:
            account_balances[acct_name] = config[CONFIG_ACCTS][acct_name][CONFIG_ACCT_BALANCE]
        current[KEY_ACCOUNT_BALANCES] = account_balances
        return

    account_balances = previous[KEY_ACCOUNT_BALANCES].copy()
    account_balances["savings"] += previous[CONFIG_INCOME_TOTAL]
    account_balances["savings"] -= previous[KEY_EXPENSES]

    deficit = config[CONFIG_ACCTS]["savings"][CONFIG_ACCT_TARGET_BALANCE] \
              - account_balances["savings"]

    # Draw/Push funds from other accounts to match savings target.
    # TBD to add priorities or similar to control ordering
    for acct_name in config[CONFIG_ACCTS]:
        if acct_name == "savings" or deficit == 0:
            continue
        if deficit < 0:
            account_balances[acct_name] += -deficit
            account_balances["savings"] += deficit
            deficit = 0
        elif deficit > 0 and account_balances[acct_name] > 0:
            transfer = min(deficit, account_balances[acct_name])
            account_balances["savings"] += transfer
            account_balances[acct_name] -= transfer
            deficit -= transfer
    current[KEY_ACCOUNT_BALANCES] = account_balances

def calc_year(current, previous):
    """ Calculates the next year's results, given global configuration
        and the previous year
    """
    calc_account_balance(current, previous)
    calc_expenses(current, previous)
    calc_income(current)

#------------------ Output

def get_output_keys():
    """ Assembles keys for output table """
    output_keys = [(KEY_YEAR, "%d"),
                   (KEY_EXPENSES, "%.2f"),
                   (CONFIG_INCOME_TOTAL, "%.2f")
                  ]
    return output_keys

def output_years_html(years):
    """ Generates HTML output summarizing the key calculations for each year """
    output_keys = get_output_keys()
    with open('Results.html', "w") as outf:
        outf.write("<HTML><BODY><TABLE>\n")

        outf.write("<TR>")
        for keytup in output_keys:
            outf.write("<TH>"+keytup[0]+"</TH>")
        for source in config[CONFIG_INCOME_SOURCES]:
            outf.write("<TH>income source (%s)</TH>" % source[CONFIG_NAME])
        for acct_name in config[CONFIG_ACCTS]:
            outf.write("<TH>account income (%s)</TH>" % acct_name)
        for acct_name in config[CONFIG_ACCTS]:
            outf.write("<TH>%s</TH>" % acct_name)
        outf.write("</TR>\n")

        for year in years:
            outf.write("<TR>")
            for keytup in output_keys:
                outf.write("<TD>"+(keytup[1] % year[keytup[0]])+"</TD>")
            for source in config[CONFIG_INCOME_SOURCES]:
                outf.write("<TD>"
                           +"%.2f" % year[KEY_INCOME_FROM_INCOME_SOURCES][source[CONFIG_NAME]]
                           +"</TD>")
            for acct_name in config[CONFIG_ACCTS]:
                outf.write("<TD>"
                           +"%.2f" % year[KEY_INCOME_FROM_ACCOUNTS][acct_name]
                           +"</TD>"
                          )
            for acct_name in config[CONFIG_ACCTS]:
                outf.write("<TD>"
                           +"%.2f" % year[KEY_ACCOUNT_BALANCES][acct_name]
                           +"</TD>"
                          )

            outf.write("</TR>\n")

        outf.write("</TABLE></BODY></HTML>\n")

#------------------ Main loop

def main():
    """ Program main entry point """
    load_config()

    years = []
    previous = None
    for year in range(2021, 2071):
        current = {KEY_YEAR : year}
        calc_year(current, previous)
        years.append(current)
        previous = current
        if current[KEY_ACCOUNT_BALANCES]["savings"] < 0:
            print 'Destitute on year '+str(year)
            break

    output_years_html(years)

main()
