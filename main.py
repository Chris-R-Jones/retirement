""" Theiding-Jones Retirement calculator
    Mostly to prove we could have retired several years ago
"""
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

def calc_returns(current, previous):
    """Calculates annual gains on invetment accounts, adjusting balances"""
    current[CONFIG_ACCTS] = {}
    for acct_name in config[CONFIG_ACCTS]:
        cfgacct = config[CONFIG_ACCTS][acct_name]
        if previous is None:
            newacct = cfgacct
            newacct[CONFIG_ACCT_BALANCE] = (cfgacct[CONFIG_ACCT_BALANCE]
                                            * (1.0 + cfgacct[CONFIG_ACCT_RETURN_RATE])
                                           )
        else:
            prvacct = previous[CONFIG_ACCTS][acct_name]
            newacct = prvacct.copy()
            newacct[CONFIG_ACCT_BALANCE] = (prvacct[CONFIG_ACCT_BALANCE]
                                            * (1.0 + cfgacct[CONFIG_ACCT_RETURN_RATE])
                                           )
        current[CONFIG_ACCTS][acct_name] = newacct

def calc_expenses(current, previous):
    """ Calculates yearly expenses, based on user configuration """
    if previous is None:
        current[KEY_EXPENSES] = config[CONFIG_EXPENSES]
    else:
        current[KEY_EXPENSES] = previous[KEY_EXPENSES] * (1 + config[CONFIG_INFLATION])

def calc_income(current):
    """ Calculates yearly income from configured sources """
    current[CONFIG_INCOME_TOTAL] = 0

    for source in config[CONFIG_INCOME_SOURCES]:
        if (CONFIG_INCOME_START_YEAR in source
                and CONFIG_INCOME_END_YEAR in source
                and current[KEY_YEAR] >= source[CONFIG_INCOME_START_YEAR]
                and current[KEY_YEAR] <= source[CONFIG_INCOME_END_YEAR]
           ):
            current[CONFIG_INCOME_TOTAL] += source[CONFIG_INCOME_AMOUNT]
    # TBD -- need to adjust the above for inflation

def calc_balance_adjust(current):
    """ Adjusts balances of savings account to add yearly income
        and remove yearly expenses.

        TBD: to not hardcode "savings"...
    """

    savings = current[CONFIG_ACCTS]["savings"]
    savings[CONFIG_ACCT_BALANCE] += current[CONFIG_INCOME_TOTAL]
    savings[CONFIG_ACCT_BALANCE] -= current[KEY_EXPENSES]

    deficit = savings[CONFIG_ACCT_TARGET_BALANCE] - savings[CONFIG_ACCT_BALANCE]

    # Draw/Push funds from other accounts to match savings target.
    # TBD to add priorities or similar to control ordering
    for acct_name in current[CONFIG_ACCTS]:
        if acct_name == "savings" or deficit == 0:
            continue
        acct = current[CONFIG_ACCTS][acct_name]

        if deficit < 0:
            acct[CONFIG_ACCT_BALANCE] += -deficit
            savings[CONFIG_ACCT_BALANCE] += deficit
            deficit = 0
        elif deficit > 0 and acct[CONFIG_ACCT_BALANCE] > 0:
            transfer = min(deficit, acct[CONFIG_ACCT_BALANCE])
            savings[CONFIG_ACCT_BALANCE] += transfer
            acct[CONFIG_ACCT_BALANCE] -= transfer
            deficit -= transfer


def calc_year(current, previous):
    """ Calculates the next year's results, given global configuration
        and the previous year
    """
    calc_returns(current, previous)
    calc_expenses(current, previous)
    calc_income(current)
    calc_balance_adjust(current)

def output_years_html(years):
    """ Generates HTML output summarizing the key calculations for each year """
    with open('Results.html', "w") as outf:
        outf.write("<HTML><BODY><TABLE>\n")

        outf.write("<TR>")
        for keytup in OUTPUT_KEYS:
            outf.write("<TH>"+keytup[0]+"</TH>")
        for acct_name in config[CONFIG_ACCTS]:
            outf.write("<TH>"+acct_name+"</TH>")
        outf.write("</TR>\n")

        for year in years:
            outf.write("<TR>")
            for keytup in OUTPUT_KEYS:
                outf.write("<TD>"+(keytup[1] % year[keytup[0]])+"</TD>")

            for acct_name in config[CONFIG_ACCTS]:
                acct = year[CONFIG_ACCTS][acct_name]
                outf.write("<TD>"
                           +"%.2f" % acct[CONFIG_ACCT_BALANCE]
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
        if current[CONFIG_ACCTS]["savings"][CONFIG_ACCT_BALANCE] < 0:
            print 'Destitute on year '+str(year)
            break

    output_years_html(years)

main()
