""" Theiding-Jones Retirement calculator
    Mostly to prove we could have retired several years ago
"""
import json
import copy

# Configuration keys
CONFIG_INFLATION = 'inflation' # annual inflation percentage

CONFIG_START_YEAR = 'startYear'
CONFIG_END_YEAR = 'endYear'
CONFIG_NAME = 'name'
CONFIG_TYPE = 'type'

CONFIG_CAPITAL_GAINS_TAX_RATE = "capitalGainsTaxRate"
CONFIG_FEDERAL_INCOME_TAX_RATE = "federalIncomeTaxRate"
CONFIG_STATE_INCOME_TAX_RATE = "stateIncomeTaxRate"
CONFIG_REALTOR_FEE_PERCENT = "realtorFeePercent"

CONFIG_INCOME_EXPENSES = 'incomeExpenses'
CONFIG_INCOME__EXPENSES_NAME = CONFIG_NAME
CONFIG_INCOME_EXPENSE_AMOUNT = 'amount'
CONFIG_INCOME_START_AGE = 'startAge'
CONFIG_INCOME_END_AGE = 'endAge'

CONFIG_ACCTS = 'accounts'
CONFIG_ACCT_BALANCE = 'balance'
CONFIG_ACCT_TARGET_BALANCE = 'targetBalance'
CONFIG_ACCT_RETURN_RATE = 'returnRate'
CONFIG_ACCT_MORTGAGE_RATE = 'mortgageRate'
CONFIG_ACCT_MORTGAGE_PAYMENT = 'mortgagePayment'
CONFIG_ACCT_PRINCIPAL = 'principal'
CONFIG_ACCT_VALUATION = 'valuation'

CONFIG_MORTGAGE_MONTHLY_PAYMENT = "monthlyPayment"

CONFIG_INVESTMENT_BASIS = "basis"

CONFIG_LINE_ITEM_TYPE_BASIC = 'basic'

CONFIG_ACCOUNT_TYPE_BASIC = 'basic'
CONFIG_ACCOUNT_TYPE_MORTGAGE = 'mortgage'
CONFIG_ACCOUNT_TYPE_INVESTMENT = 'investment'

# TBD need to cleanup when to use CONFIG and KEY prefix
KEY_SAVINGS_ACCT = "Savings"

# Types of taxes
TAX_INCOME = 'Income'
TAX_CAPITAL_GAINS = 'CapitalGains'

#------------------ Account class

class Account():
    # pylint: disable=too-many-instance-attributes
    """ Representation of a bookkeeping account for a given year """
    def __init__(self, acct_name, cfg, year):

        # Validate account config
        assert cfg[CONFIG_ACCT_BALANCE] is not None
        assert (CONFIG_ACCT_RETURN_RATE not in cfg
                or cfg[CONFIG_ACCT_RETURN_RATE] >= 0.0
               )
        assert (CONFIG_ACCT_TARGET_BALANCE not in cfg
                or cfg[CONFIG_ACCT_TARGET_BALANCE] >= 0.0
               )

        # Set initial state from config
        self.name = acct_name
        self.year = year
        self.balance = cfg[CONFIG_ACCT_BALANCE]
        if CONFIG_ACCT_TARGET_BALANCE in cfg:
            self.target_balance = float(cfg[CONFIG_ACCT_TARGET_BALANCE])
        else:
            self.target_balance = None

        if CONFIG_ACCT_RETURN_RATE in cfg:
            self.return_rate = float(cfg[CONFIG_ACCT_RETURN_RATE])
        else:
            self.return_rate = None

    def deposit(self, amount, appreciation):
        """ Deposit funds into account. Negative amount is a withdrawl.
        appreciation is a boolean flag that indicates whether the deposit represents
        a change in appreciation. """
        self.balance += amount

    def transfer_to(self, account, amount):
        """ Transfers amount from this account to target account """
        print 'Transfer ${} from {} to {}'.format(amount, self.name, account.name)
        self.deposit(-amount, False)
        account.deposit(amount, False)

    def process_income_and_expenses(self):
        """ Basic account books income from return rate if one is defined """
        if self.return_rate:
            # TBD Better not to have a base implementation at all?
            self.year.book(self, self.balance * self.return_rate, "Gains", self, True)

#------------------ Investment class

class Investment(Account):
    """ Investment account manages basis and tax consequences from sales. """
    def __init__(self, acct_name, cfg, year):
        Account.__init__(self, acct_name, cfg, year)
        self.basis = cfg[CONFIG_INVESTMENT_BASIS]

    def deposit(self, amount, appreciation):
        """ Non-appreciation withdrawl triggers partial basis reduction and capital gains.
        Non-appreciation deposit increases basis with no capital gains.
        Appreciation only changes balance without basis or capital gains impact. """
        if not appreciation:
            if amount < 0:
                taxable = -amount + (self.basis * amount) / self.balance
                self.basis += (self.basis * amount) / self.balance
                # Book capital gains incurred from sale
                print 'Investment sale triggered capital gains of ${}'.format(taxable)
                self.year.book_tax(taxable, TAX_CAPITAL_GAINS, "Investment Gains")
            else:
                self.basis += amount

        Account.deposit(self, amount, appreciation)

#------------------ Mortgage class

class Mortgage(Account):
    """ Mortage principal is represented by balance. Creates mortgage payment and applies principal
    reduction to balance. """
    def __init__(self, acct_name, cfg, year):
        Account.__init__(self, acct_name, cfg, year)
        assert cfg[CONFIG_MORTGAGE_MONTHLY_PAYMENT] is not None
        self.monthly_payment = float(cfg[CONFIG_MORTGAGE_MONTHLY_PAYMENT])

    def process_income_and_expenses(self):
        """ Pay the mortgage and reduce principal """
        # TBD Need to stop when mortgage is paid off
        # TBD calculate principal_reduction correctly based on monthly payment and mortgage
        # interest rate

        # Reduce outstanding principal
        principal_reduction = 10000
        self.year.book(self, principal_reduction, "Mortgage Principal Reduction", self)
        # Mortgage payments over the year
        self.year.book(None, -self.monthly_payment * 12, "Mortgage Payment", self)

#------------------ Year class

class Year():
    """ Represents a year in the budget. It triggers everything that happens throughout a year
    including taxes and holds the results """

    def __init__(self, year):
        self.year = year
        self.books = [] # tracking of all income and expenses
        self.tax_books = [] # tracking of all taxable events
        self.accounts = {}

    def process(self, previous):
        """ Processes the year's results """
        print self.year
        self.init_accounts(previous)
        self.process_income_and_expenses()
        self.tax(True)
        self.rebalance_accounts()
        # Post process any remaining capital gains tax from rebalancing
        self.tax(False)

    def init_accounts(self, previous):
        """ Get accounts ready for the year """
        if not previous:
            for acct_name in config[CONFIG_ACCTS]:
                acct_cfg = config[CONFIG_ACCTS][acct_name]
                # TBD Instantiate account from type to class name mapping
                if acct_cfg[CONFIG_TYPE] == CONFIG_ACCOUNT_TYPE_BASIC:
                    self.accounts[acct_name] = Account(acct_name, acct_cfg, self)
                elif acct_cfg[CONFIG_TYPE] == CONFIG_ACCOUNT_TYPE_MORTGAGE:
                    self.accounts[acct_name] = Mortgage(acct_name, acct_cfg, self)
                elif acct_cfg[CONFIG_TYPE] == CONFIG_ACCOUNT_TYPE_INVESTMENT:
                    self.accounts[acct_name] = Investment(acct_name, acct_cfg, self)
                else:
                    assert False # TBD how to raise error if account type not supported
        else:
            self.accounts = copy.deepcopy(previous.accounts) # pylint tag?pylint: disable=unsubscriptable-object
            for account in self.accounts.values():
                account.year = self

    def process_income_and_expenses(self):
        """ Create all income and expenses originating explicitly from configured entries or from
        accounts """
        # Start with income and expenses that are individually configured
        for source in config[CONFIG_INCOME_EXPENSES]:
            if source[CONFIG_TYPE] == CONFIG_LINE_ITEM_TYPE_BASIC:
                book_entry_helper = BasicBookEntryHelper(source)
            else:
                assert False # TBD how to raise error if income type not supported
            self.book(None, book_entry_helper.get_amount(), source[CONFIG_NAME], None)
            if book_entry_helper.get_tax_type() is not None:
                self.book_tax(book_entry_helper.get_amount(), book_entry_helper.get_tax_type(),
                              source[CONFIG_NAME])
        # Add more income and expenses that originate from accounts
        for account in self.accounts.values():
            account.process_income_and_expenses()

    def book(self, account, amount, name, from_account, appreciation=False):
        """ Add transaction to books and transfer funds to account accordingly """
        if account is None:
            # If account not specified default to savings account
            account = self.accounts[KEY_SAVINGS_ACCT]
        account.deposit(amount, appreciation)
        self.books.append(BookEntry(account, amount, name, from_account))

        # Print summary of booking
        if amount > 0:
            expense_income = "Income "
        else:
            expense_income = "Expense"
        from_account_str = ''
        if from_account is not None:
            from_account_str = '(initiated by %s)' %from_account.name
        print '{}: {} applied to {} for {} {}' \
            .format(expense_income, amount, account.name, name, from_account_str)

    def book_tax(self, amount, tax_type, name):
        """ Record all taxable events """
        self.tax_books.append(TaxBookEntry(amount, tax_type, name))

    def tax(self, full):
        """ Calculate tax return and pay taxes """
        label = "Tax return"
        if not full:
            label += " (post processing)"
        print label
        tax_income = 0
        tax_capital_gains = 0
        print "Taxable income"
        for tax_book_entry in self.tax_books:
            if not tax_book_entry.processed and tax_book_entry.tax_type == TAX_INCOME:
                if full:
                    tax_income += tax_book_entry.amount
                    tax_book_entry.processed = True
                    print '{}: {}'.format(tax_book_entry.name, tax_book_entry.amount)
                else:
                    # TBD how to raise error if income was reported outside of full tax return
                    assert False
        print 'Total taxable income: {}'.format(tax_income)
        print "Capital gains"
        for tax_book_entry in self.tax_books:
            if not tax_book_entry.processed and tax_book_entry.tax_type == TAX_CAPITAL_GAINS:
                tax_capital_gains += tax_book_entry.amount
                tax_book_entry.processed = True
                print '{}: {}'.format(tax_book_entry.name, tax_book_entry.amount)
        print 'Total capital gains: {}'.format(tax_capital_gains)
        # TBD calculate tax more correctly taking tax brackets and various other rules into account
        tax = -tax_income * 0.45 - tax_capital_gains * 0.34
        print 'Tax: {}'.format(tax)
        self.book(None, tax, label, None)

    def rebalance_accounts(self):
        """ Transfers cash between accounts to match target balances
        """

        # Draw/Push funds from accounts to match their balance targets.
        # TBD to add priorities or similar to control ordering

        # Find an account that doesn't match its target balance
        print 'Rebalance'
        for unbal_name in config[CONFIG_ACCTS]:
            unbalanced = self.accounts[unbal_name]

            if unbalanced.target_balance is None or \
               unbalanced.balance == unbalanced.target_balance:
                continue
            deficit = unbalanced.target_balance - unbalanced.balance

            # Find an account to draw funds from (or send to)
            for acct_name in self.accounts:
                # TBD For now we are only balancing into the investment account
                if acct_name != 'Investment':
                    continue
                if acct_name == unbal_name or deficit == 0:
                    continue
                account = self.accounts[acct_name]
                if account.balance == account.target_balance \
                   or account.name == KEY_SAVINGS_ACCT:
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

    def get_net_worth(self):
        """ Return net worth as the sum of all account balances """
        return sum(account.balance for account in self.accounts.values())

    def get_total_income(self):
        """ Sums up all line items with an amount > 0 """
        return sum(book_entry.amount for book_entry in self.books if book_entry.amount > 0)

    def get_total_expenses(self):
        """ Sums up all line items with an amount < 0 """
        return sum(book_entry.amount for book_entry in self.books if book_entry.amount < 0)

#------------------ BookEntry class

class BookEntry():
    """ Represents an entry in the books for all accounts changes """
    def __init__(self, account, amount, name, from_account):
        self.account = account
        self.amount = amount
        self.name = name
        self.from_account = from_account

#------------------ TaxBookEntry class

class TaxBookEntry():
    """ Represents an entry in the tax books for all taxable events """
    def __init__(self, amount, tax_type, name):
        self.amount = amount
        self.tax_type = tax_type
        self.name = name
        self.processed = False

#------------------ BasicBookEntryHelper class

class BasicBookEntryHelper():
    """ Determines a basic income or expense amount from configuration that remains constant and
    optionally applies to a certain year range """
    def __init__(self, cfg):
        self.amount = cfg[CONFIG_INCOME_EXPENSE_AMOUNT]
        self.name = cfg[CONFIG_NAME]

    def get_amount(self):
        """ Return the configured amount """
        return self.amount #TBD add support for year filter and inflation

    def get_tax_type(self):
        """ All income is reported as taxable income """
        tax_type = None
        if self.amount > 0:
            tax_type = TAX_INCOME
        return tax_type

#------------------ Config

def config_validate():
    """ Reviews configuration settings for correctness """
    assert config[CONFIG_INFLATION] >= 0 and config[CONFIG_INFLATION] <= 1

    assert (config[CONFIG_INCOME_EXPENSES] is not None
            and len(config[CONFIG_INCOME_EXPENSES]) > 0
           )
    for income in config[CONFIG_INCOME_EXPENSES]:
        assert income[CONFIG_INCOME__EXPENSES_NAME] is not None
        assert income[CONFIG_INCOME_EXPENSE_AMOUNT] is not None

    assert config[CONFIG_ACCTS] is not None and len(config[CONFIG_ACCTS]) > 0

def config_load():
    """Loads user preferences from json configuration file"""
    with open("Configuration.json", "r") as infile:
        global config
        config = json.load(infile)
    config_validate()

#------------------ Util

def filter_year(year, src): #TBD find the right place for this
    """ Checks specified dictionary for CONFIG_START_YEAR / END_YEAR keys """
    return ((CONFIG_START_YEAR not in src or src[CONFIG_START_YEAR] <= year) and
            (CONFIG_END_YEAR not in src or src[CONFIG_END_YEAR] >= year)
           )

#------------------ Output

def output_years_html(years):
    """ Generates HTML output summarizing the key calculations for each year """
    with open('Results.html', "w") as outf:
        outf.write("<HTML><BODY><TABLE>\n")

        # Table header
        year_for_header = Year(0) # sample to infer header
        year_for_header.process(None) # sample run
        outf.write("<TR>")
        outf.write("<TH>Year</TH>")
        outf.write("<TH>Net Worth</TH>")
        for acct_name in year_for_header.accounts:
            outf.write("<TH>Balance (Year End) %s</TH>" % acct_name)
        for book_entry in year_for_header.books:
            if book_entry.amount < 0:
                column_header = "Expense"
            else:
                column_header = "Income"
            column_header = "%s %s" % (column_header, book_entry.name)
            if book_entry.from_account:
                column_header = "%s (from %s)" % (column_header, book_entry.from_account.name)
            outf.write("<TH>%s</TH>" % column_header)
        outf.write("<TH>Total Income</TH>")
        outf.write("<TH>Total Expenses</TH>")
        outf.write("</TR>\n")

        # Table rows
        for year in years:
            outf.write("<TR>")
            outf.write("<TD>%d</TD>" % year.year)
            outf.write("<TD>%.2f</TD>" % year.get_net_worth())
            for account in year.accounts.values():
                outf.write("<TD>%.2f</TD>" % account.balance)
            for book_entry in year.books:
                outf.write("<TD>%.2f</TD>" % book_entry.amount)
            outf.write("<TD>%.2f</TD>" % year.get_total_income())
            outf.write("<TD>%.2f</TD>" % year.get_total_expenses())
            outf.write("</TR>\n")

        outf.write("</TABLE></BODY></HTML>\n")

#------------------ Main loop

def main():
    """ Program main entry point """
    config_load()

    years = []
    previous = None
    for year in range(2022, 2024):

        # Instantiate new year, copying from previous
        current = Year(year)
        current.process(previous)

        # Store results of all years
        years.append(current)
        previous = current
        if current.get_net_worth() < 0:
            print 'Destitute on year {}'.format(year)
            break

    output_years_html(years)

main()
