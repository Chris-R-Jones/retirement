""" Theiding-Jones Retirement calculator
    Mostly to prove we could have retired several years ago
"""
import json
import copy

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
CONFIG_ACCT_BALANCE = 'balance'
CONFIG_ACCT_TARGET_BALANCE = 'targetBalance'
CONFIG_ACCT_RETURN_RATE = 'returnRate'
CONFIG_ACCT_MORTGAGE_RATE = 'mortgageRate'
CONFIG_ACCT_MORTGAGE_PAYMENT = 'mortgagePayment'
CONFIG_ACCT_PRINCIPAL = 'principal'
CONFIG_ACCT_VALUATION = 'valuation'
CONFIG_ACCT_VAL_GROWTH_RATE = 'valuationGrowthRate'

KEY_INCOME_PER_CATEGORY = 'incomeCategory'
KEY_ACCOUNT_BALANCES = 'accountBalances'
# TBD need to cleanup when to use CONFIG and KEY prefix

# Output-only keys
KEY_ACCTS = "accounts"
KEY_YEAR = 'year'
KEY_INCOME_TOTAL = 'incomeTotal'
KEY_EXPENSES = 'expenses'

#------------------ Account class

class Account():
    # pylint: disable=too-many-instance-attributes
    """ Representation of a financial account """
    def __init__(self, acct_name, cfg):

        # Validate account config
        assert cfg[CONFIG_ACCT_BALANCE] is not None
        assert cfg[CONFIG_ACCT_BALANCE] >= 0
        assert cfg[CONFIG_ACCT_RETURN_RATE] is not None
        assert cfg[CONFIG_ACCT_RETURN_RATE] >= 0
        assert (CONFIG_ACCT_TARGET_BALANCE not in cfg
                or cfg[CONFIG_ACCT_TARGET_BALANCE] >= 0.0
               )

        # Set initial state from config
        self.name = acct_name
        self.balance = cfg[CONFIG_ACCT_BALANCE]
        if CONFIG_ACCT_TARGET_BALANCE in cfg:
            self.target_balance = float(cfg[CONFIG_ACCT_TARGET_BALANCE])
        else:
            self.target_balance = None
        self.return_rate = cfg[CONFIG_ACCT_RETURN_RATE]

        self.principal = None
        if CONFIG_ACCT_PRINCIPAL in cfg:
            self.principal = cfg[CONFIG_ACCT_PRINCIPAL]

        self.valuation = None
        if CONFIG_ACCT_VALUATION in cfg:
            self.valuation = cfg[CONFIG_ACCT_VALUATION]

        self.val_growth_rate = None
        if CONFIG_ACCT_VAL_GROWTH_RATE in cfg:
            self.val_growth_rate = cfg[CONFIG_ACCT_VAL_GROWTH_RATE]

        self.mortgage_rate = None
        if CONFIG_ACCT_MORTGAGE_RATE in cfg:
            self.mortgage_rate = cfg[CONFIG_ACCT_MORTGAGE_RATE]

        self.mortgage_payment = None
        if CONFIG_ACCT_MORTGAGE_PAYMENT in cfg:
            self.mortgage_payment = cfg[CONFIG_ACCT_MORTGAGE_PAYMENT]

        if self.mortgage_rate is not None or self.principal is not None \
            or self.mortgage_payment is not None:
            assert self.mortgage_rate and self.mortgage_rate > 0.0
            assert self.mortgage_payment and self.mortgage_payment > 0.0
            assert self.principal and self.principal >= 0.0
            assert self.target_balance == 0.0

        if self.valuation is not None or self.val_growth_rate is not None:
            assert self.valuation and self.valuation > 0.0
            assert self.val_growth_rate and self.val_growth_rate >= 0.0

    def apply_account_return(self, year):
        """ Applies yearly account grwoth by estimated return rate """
        year_return = self.balance * self.return_rate
        year[KEY_INCOME_PER_CATEGORY][self.name] = year_return
        year[KEY_INCOME_TOTAL] += year_return
        self.balance += year_return

    def apply_income(self, year, source, amount):
        """ Applies yearly expenses """
        year[KEY_INCOME_PER_CATEGORY][source] = amount
        year[KEY_INCOME_TOTAL] += amount
        self.balance += amount

    def apply_expenses(self, expense):
        """ Applies yearly expenses """
        self.balance -= expense

    def transfer_to(self, account, amount):
        """ Transfers amount from this account to target account """
        self.balance -= amount
        account.balance += amount

    def has_mortgage(self):
        """ Returns true if this account has a mortgage """
        return self.mortgage_rate and self.principal > 0.0

    def apply_mortgage(self):
        """ Calculates interest and principal from mortgage payments """
        mon_int_rate = self.mortgage_rate / 12
        for _ in range(0, 12):
            interest = self.principal * mon_int_rate
            assert interest < self.mortgage_payment
            if self.mortgage_payment > self.principal:
                self.balance -= self.principal
                self.principal = 0.0
            else:
                self.balance -= self.mortgage_payment
                self.principal -= (self.mortgage_payment - interest)

    def apply_valuation_gains(self):
        """ Applies unrealized gains on valuation """
        if not self.valuation or not self.val_growth_rate:
            return
        year_gains = self.valuation * self.val_growth_rate
        self.valuation += year_gains

#------------------ Config

def config_validate():
    """ Reviews configuration settings for correctness """
    assert config[CONFIG_EXPENSES] >= 0
    assert config[CONFIG_INFLATION] >= 0 and config[CONFIG_INFLATION] <= 1

    assert (config[CONFIG_INCOME_SOURCES] is not None
            and len(config[CONFIG_INCOME_SOURCES]) > 0
           )
    for income in config[CONFIG_INCOME_SOURCES]:
        assert income[CONFIG_INCOME_NAME] is not None
        assert income[CONFIG_INCOME_AMOUNT] is not None

    assert config[CONFIG_ACCTS] is not None and len(config[CONFIG_ACCTS]) > 0

def config_load():
    """Loads user preferences from json configuration file"""
    with open("Configuration.json", "r") as infile:
        global config
        config = json.load(infile)
    config_validate()


def config_instantiate_accts():
    """ Instantiates initial account objects based on config """
    accounts = {}
    for acct_name in config[CONFIG_ACCTS]:
        acct_cfg = config[CONFIG_ACCTS][acct_name]
        accounts[acct_name] = Account(acct_name, acct_cfg)
    return accounts

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
        expense = current[KEY_EXPENSES] = config[CONFIG_EXPENSES]
    else:
        expense = current[KEY_EXPENSES] = previous[KEY_EXPENSES] * (1 + config[CONFIG_INFLATION])

    savings = current[KEY_ACCTS]["savings"]
    savings.apply_expenses(expense)

    for acct_name in config[CONFIG_ACCTS]:
        account = current[KEY_ACCTS][acct_name]
        if account.has_mortgage():
            account.apply_mortgage()

#------------------ Income

def calc_income(current):
    """ Calculates all types of yearly income """
    calc_income_sources(current)
    calc_accounts(current)

def calc_income_sources(current):
    """ Calculates yearly income from configured sources """
    savings = current[KEY_ACCTS]["savings"]

    for source in config[CONFIG_INCOME_SOURCES]:
        income = 0
        if filter_year(current[KEY_YEAR], source):
            # TBD -- need to adjust income for raises
            income = source[CONFIG_INCOME_AMOUNT]
            savings.apply_income(current, source[CONFIG_NAME], income)
        else:
            savings.apply_income(current, source[CONFIG_NAME], 0)

def calc_accounts(current):
    """ Calculates annual gains on accounts """
    for acct_name in config[CONFIG_ACCTS]:
        account = current[KEY_ACCTS][acct_name]
        account.apply_account_return(current)
        account.apply_valuation_gains()

#------------------ Account balances

def calc_rebalance_accounts(current):
    """ Transfers cash between accounts to match target balances
    """

    # Draw/Push funds from accounts to match their balance targets.
    # TBD to add priorities or similar to control ordering
    for unbal_name in config[CONFIG_ACCTS]:
        unbalanced = current[KEY_ACCTS][unbal_name]

        if unbalanced.target_balance is None or \
           unbalanced.balance == unbalanced.target_balance:
            continue

        deficit = unbalanced.target_balance - unbalanced.balance
        for acct_name in config[CONFIG_ACCTS]:
            if acct_name == unbal_name or deficit == 0:
                continue
            account = current[KEY_ACCTS][acct_name]
            if account.balance == account.target_balance \
               and not account.name == "savings":
                continue
            if account.target_balance == 0.0:
                continue
            if deficit < 0:
                unbalanced.transfer_to(account, -deficit)
                deficit = 0
            elif deficit > 0 and account.balance > 0:
                transfer = min(deficit, account.balance)
                account.transfer_to(unbalanced, transfer)
                deficit -= transfer

def calc_year(current, previous):
    """ Calculates the next year's results, given global configuration
        and the previous year
    """
    calc_expenses(current, previous)
    calc_income(current)
    calc_rebalance_accounts(current)

#------------------ Output

def get_output_keys():
    """ Assembles keys for output table """
    output_keys = [(KEY_YEAR, "%d"),
                   (KEY_EXPENSES, "%.2f"),
                   (KEY_INCOME_TOTAL, "%.2f")
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
            outf.write("<TH>balance (%s)</TH>" % acct_name)
        for acct_name in config[CONFIG_ACCTS]:
            if CONFIG_ACCT_PRINCIPAL in config[CONFIG_ACCTS][acct_name]:
                outf.write("<TH>principal (%s)</TH>" % acct_name)
        for acct_name in config[CONFIG_ACCTS]:
            if CONFIG_ACCT_VALUATION in config[CONFIG_ACCTS][acct_name]:
                outf.write("<TH>valuation (%s)</TH>" % acct_name)
        outf.write("</TR>\n")

        for year in years:
            outf.write("<TR>")
            for keytup in output_keys:
                outf.write("<TD>"+(keytup[1] % year[keytup[0]])+"</TD>")
            for source in config[CONFIG_INCOME_SOURCES]:
                name = source[CONFIG_NAME]
                outf.write("<TD>%.2f</TD>" % year[KEY_INCOME_PER_CATEGORY][name])
            for acct_name in config[CONFIG_ACCTS]:
                outf.write("<TD>%.2f</TD>" % year[KEY_INCOME_PER_CATEGORY][acct_name])
            for acct_name in config[CONFIG_ACCTS]:
                account = year[KEY_ACCTS][acct_name]
                outf.write("<TD>%.2f</TD>"%account.balance)
            for acct_name in config[CONFIG_ACCTS]:
                if CONFIG_ACCT_PRINCIPAL in config[CONFIG_ACCTS][acct_name]:
                    account = year[KEY_ACCTS][acct_name]
                    outf.write("<TD>%.2f</TD>" % account.principal)
            for acct_name in config[CONFIG_ACCTS]:
                if CONFIG_ACCT_VALUATION in config[CONFIG_ACCTS][acct_name]:
                    account = year[KEY_ACCTS][acct_name]
                    outf.write("<TD>%.2f</TD>" % account.valuation)

            outf.write("</TR>\n")

        outf.write("</TABLE></BODY></HTML>\n")

#------------------ Main loop

def main():
    """ Program main entry point """
    config_load()

    years = []
    previous = None
    for year in range(2021, 2071):

        # Instantiate new year, copying from previous
        current = {KEY_YEAR : year, \
                   KEY_INCOME_PER_CATEGORY : {},
                   KEY_INCOME_TOTAL : 0.0
                  }
        if not previous:
            current[KEY_ACCTS] = config_instantiate_accts()
        else:
            current[KEY_ACCTS] = copy.deepcopy(previous[KEY_ACCTS]) # pylint: disable=unsubscriptable-object

        # Update the yearly calculations
        calc_year(current, previous)

        # Store results of all years
        years.append(current)
        previous = current
        if current[KEY_ACCTS]["savings"].balance < 0:
            print('Destitute on year '+str(year))
            break

    output_years_html(years)

main()
