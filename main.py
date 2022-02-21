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
CONFIG_INCOME_EXPENSE_INFLATION_ADJUST = 'inflationAdjust'
CONFIG_INCOME_START_AGE = 'startAge' # TBD keep this here or handle with startYear?
CONFIG_INCOME_END_AGE = 'endAge' # TBD keep this here or handle with startYear?

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

INCOME = 1
EXPENSE = 2

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

    # pylint: disable=unused-argument
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
                print 'Investment sale of ${} triggered capital gains of ${}' \
                    .format(-amount, taxable)
                self.year.book_tax(taxable, TAX_CAPITAL_GAINS, "Investment Gains")
            else:
                self.basis += amount

        Account.deposit(self, amount, appreciation)

    def transfer_to_plus_tax(self, account, amount, account_for_tax):
        """ For positive amounts we take into account that selling investments will cause capital
        gains taxes. We will sell more and transfer those additional funds into account_for_tax to
        proactively cover the tax liability."""
        if amount < 0:
            # No tax implications
            self.transfer_to(account, amount)
        else:
            pre_capital_gains_investment_amount = \
                amount / \
                (1 - (1 - self.basis / self.balance) * \
                 self.year.get_capital_gains_tax_percentage())
            self.deposit(-pre_capital_gains_investment_amount, False)
            account.deposit(amount, False)
            account_for_tax.deposit(pre_capital_gains_investment_amount - amount, False)

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

    def __init__(self, year, previous):
        self.year = year
        self.previous = previous
        self.books = [] # tracking of all income and expenses
        self.tax_books = [] # tracking of all taxable events
        self.accounts = {}

    def process(self):
        """ Processes the year's results """
        print self.year
        self.init_accounts()
        self.process_income_and_expenses()
        self.tax(True)
        self.rebalance_accounts()
        # Post process any remaining capital gains tax from rebalancing
        self.tax(False)

    def init_accounts(self):
        """ Get accounts ready for the year """
        if not self.previous:
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
            self.accounts = copy.deepcopy(self.previous.accounts) # pylint tag?pylint: disable=unsubscriptable-object
            for account in self.accounts.values():
                account.year = self

    def process_income_and_expenses(self):
        """ Create all income and expenses originating explicitly from configured entries or from
        accounts """
        # Start with income and expenses that are individually configured
        for source in config[CONFIG_INCOME_EXPENSES]:
            previous_book_entry = self.get_previous_book_entry(source[CONFIG_NAME])
            if source[CONFIG_TYPE] == CONFIG_LINE_ITEM_TYPE_BASIC:
                book_entry_helper = BasicBookEntryHelper(source, previous_book_entry)
            else:
                assert False # TBD how to raise error if income type not supported
            if book_entry_helper.filter(self.year):
                amount = book_entry_helper.get_amount()
                tax_type = book_entry_helper.get_tax_type()
                self.book(None, amount, source[CONFIG_NAME], None)
                if tax_type is not None:
                    self.book_tax(amount, tax_type, source[CONFIG_NAME])
        # Add more income and expenses that originate from accounts
        for account in self.accounts.values():
            account.process_income_and_expenses()

    # pylint: disable=too-many-arguments
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

    def get_previous_book_entry(self, name):
        """ Return the BookEntry from the previous year """
        if self.previous is not None:
            for book_entry in self.previous.books:
                if book_entry.name == name:
                    return book_entry
        return None

    def get_book_entry(self, name, from_account_name):
        """ Return the BookEntry for a given name and from_account_name """
        for book_entry in self.books:
            book_entry_from_account_name = None
            if book_entry.from_account is not None:
                book_entry_from_account_name = book_entry.from_account.name
            if book_entry.name == name and book_entry_from_account_name == from_account_name:
                return book_entry
        return None

    def book_tax(self, amount, tax_type, name):
        """ Record all taxable events """
        self.tax_books.append(TaxBookEntry(amount, tax_type, name))

    def get_capital_gains_tax_percentage(self):
        """ Return capital gains tax percentage. """
        # TBD Note for simplicity we assume this is a constant independent of other taxable
        # events, which is not true. This needs refinement.
        # This code needs to be shared with "tax" to ensure actual taxation will match exactly
        # pylint: disable=no-self-use
        return 0.34

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
                    # TBD For now this only supports balancing from the Investment account
                    account.transfer_to_plus_tax(unbalanced, transfer,
                                                 self.accounts[KEY_SAVINGS_ACCT])
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
    # pylint: disable=too-few-public-methods
    """ Represents an entry in the books for all accounts changes """
    def __init__(self, account, amount, name, from_account):
        self.account = account
        self.amount = amount
        self.name = name
        self.from_account = from_account

#------------------ TaxBookEntry class

class TaxBookEntry():
    # pylint: disable=too-few-public-methods
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
    def __init__(self, cfg, previous_book_entry):
        self.cfg = cfg
        self.previous_book_entry = previous_book_entry

    def get_amount(self):
        """ Return the configured amount """
        if self.previous_book_entry is not None:
            amount = self.previous_book_entry.amount
            if CONFIG_INCOME_EXPENSE_INFLATION_ADJUST in self.cfg:
                amount *= 1.02 # TDB Make configurable
        else:
            amount = self.cfg[CONFIG_INCOME_EXPENSE_AMOUNT]
        return amount

    def get_tax_type(self):
        """ All income is reported as taxable income """
        tax_type = None
        if self.cfg[CONFIG_INCOME_EXPENSE_AMOUNT] > 0:
            tax_type = TAX_INCOME
        return tax_type

    def filter(self, year):
        """ Return False to filter out an entry.
        Check if year is filtered out via configuration """
        return ((CONFIG_START_YEAR not in self.cfg or self.cfg[CONFIG_START_YEAR] <= year) and
                (CONFIG_END_YEAR not in self.cfg or self.cfg[CONFIG_END_YEAR] >= year)
               )

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

#------------------ Output

class Output():
    # pylint: disable=no-init
    """ Manages output of the simulation data """

    @staticmethod
    def get_income_expense_types(years):
        """ Get all the income and expense types we encountered throughout the years.
        An income and expense type is represented by a tuple of:
        - income/expense name
        - the account name if the income/expense was generated by an account or None otherwise
        For each income and expense type we store
        - INCOME if the type was only used for income
        - EXPENSE if the type was only used for expenses
        - INCOME | EXPENSe if the type was used for both income and expenses """
        income_expense_types = {}
        for year in years:
            for book_entry in year.books:
                if book_entry.amount > 0:
                    book_entry_type = INCOME
                else:
                    book_entry_type = EXPENSE
                account_name = None
                if book_entry.from_account is not None:
                    account_name = book_entry.from_account.name
                if (book_entry.name, account_name) in income_expense_types:
                    income_expense_types[(book_entry.name, account_name)] |= book_entry_type
                else:
                    income_expense_types[(book_entry.name, account_name)] = book_entry_type
        # TBD better grouping of types
        return income_expense_types

    @staticmethod
    def output_years_html(years):
        """ Generates HTML output summarizing the key calculations for each year """
        income_expense_types = Output.get_income_expense_types(years)
        with open('Results.html', "w") as outf:
            outf.write("<HTML><BODY><TABLE>\n")

            # Table header
            outf.write("<TR>")
            outf.write("<TH>Year</TH>")
            outf.write("<TH>Net Worth</TH>")
            for acct_name in config[CONFIG_ACCTS]:
                outf.write("<TH>Balance (Year End) %s</TH>" % acct_name)
            for income_expense_type in income_expense_types:
                if not ~income_expense_types[income_expense_type] & (INCOME|EXPENSE):
                    column_header = "Income/Expense"
                elif income_expense_types[income_expense_type] & EXPENSE:
                    column_header = "Expense"
                elif income_expense_types[income_expense_type] & INCOME:
                    column_header = "Income"
                else:
                    assert False # TBD how to raise error if type not set right
                column_header = "%s %s" % (column_header, income_expense_type[0])
                if income_expense_type[1] is not None:
                    column_header += " (from %s)" % income_expense_type[1]
                outf.write("<TH>%s</TH>" % column_header)
            outf.write("<TH>Total Income</TH>")
            outf.write("<TH>Total Expenses</TH>")
            outf.write("</TR>\n")

            # Table rows
            for year in years:
                outf.write("<TR>")
                outf.write("<TD>%d</TD>" % year.year)
                outf.write("<TD>%.2f</TD>" % year.get_net_worth())
                for acct_name in config[CONFIG_ACCTS]:
                    outf.write("<TD>%.2f</TD>" % year.accounts[acct_name].balance)
                for income_expense_type in income_expense_types:
                    book_entry = year.get_book_entry(income_expense_type[0], income_expense_type[1])
                    if book_entry is not None:
                        outf.write("<TD>%.2f</TD>" % book_entry.amount)
                    else:
                        outf.write("<TD>-</TD>")
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
    for year in range(2022, 2026):

        # Instantiate new year, copying from previous
        current = Year(year, previous)
        current.process()

        # Store results of all years
        years.append(current)
        previous = current
        if current.get_net_worth() < 0:
            print 'Destitute on year {}'.format(year)
            break

    Output.output_years_html(years)

main()
