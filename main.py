""" Theiding-Jones Retirement calculator
    Mostly to prove we could have retired several years ago
"""
import argparse
import ast
import copy
import datetime
import json

# Configuration keys
CONFIG_INFLATION = 'inflation' # annual inflation percentage
CONFIG_BIRTH_YEAR = 'birthYear'

CONFIG_START_YEAR = 'startYear'
CONFIG_END_YEAR = 'endYear'
CONFIG_NAME = 'name'
CONFIG_TYPE = 'type'
CONFIG_AMOUNT = 'amount'
CONFIG_PERCENT = 'percent'

CONFIG_CAPITAL_GAINS_TAX_RATE = "capitalGainsTaxRate"
CONFIG_FEDERAL_INCOME_TAX_RATE = "federalIncomeTaxRate"
CONFIG_STATE_INCOME_TAX_RATE = "stateIncomeTaxRate"
CONFIG_REALTOR_FEE_PERCENT = "realtorFeePercent"

CONFIG_INCOME_EXPENSES = 'incomeExpenses'
CONFIG_INCOME__EXPENSES_NAME = CONFIG_NAME
CONFIG_INCOME_EXPENSE_AMOUNT = 'amount'
CONFIG_INCOME_EXPENSE_INFLATION_ADJUST = 'inflationAdjust'
CONFIG_INCOME_EXPENSE_INCREASE = 'increase'
CONFIG_INCOME_START_AGE = 'startAge' # TBD keep this here or handle with startYear?
CONFIG_INCOME_END_AGE = 'endAge' # TBD keep this here or handle with startYear?

CONFIG_ACCTS = 'accounts'
CONFIG_ACCT_BALANCE = 'balance'
CONFIG_ACCT_TARGET_BALANCE = 'targetBalance'
CONFIG_ACCT_RETURN_RATE = 'returnRate'
CONFIG_ACCT_SELL = 'sell'
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

OUTPUT_CELL = "<TD>{}</TD>"
OUTPUT_CELL_RIGHT = "<TD style=\"text-align:right\">{}</TD>"
OUTPUT_CURRENCY = "${:,.0f}"

#------------------ Account class

class Account():
    # pylint: disable=too-many-instance-attributes
    """ Representation of a bookkeeping account for a given year """
    def __init__(self, acct_name, cfg, year):

        # Validate account config
        assert Config.eval(CONFIG_ACCT_BALANCE, cfg) is not None
        assert (CONFIG_ACCT_RETURN_RATE not in cfg
                or Config.eval(CONFIG_ACCT_RETURN_RATE, cfg) >= 0.0
               )
        assert (CONFIG_ACCT_TARGET_BALANCE not in cfg
                or Config.eval(CONFIG_ACCT_TARGET_BALANCE, cfg) >= 0.0
               )

        # Set initial state from config
        self.name = acct_name
        self.year = year
        self.balance = Config.eval(CONFIG_ACCT_BALANCE, cfg)
        self.return_rate = Config.eval(CONFIG_ACCT_RETURN_RATE, cfg)
        self.target_balance = Config.eval(CONFIG_ACCT_TARGET_BALANCE, cfg)
        self.sell_year = Config.eval(CONFIG_ACCT_SELL, cfg)

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

    def process(self):
        """ Check if it's time to sell account """
        if self.sell_year == self.year.year:
            self.sell()

    def process_income_and_expenses(self):
        """ Basic account books income from return rate if one is defined """
        if self.return_rate:
            # TBD Better not to have a base implementation at all?
            self.year.book(self, self.balance * self.return_rate, "Gains", self, True)

    def sell(self):
        """ Cash in the entire account """
        self.transfer_to(self.year.get_savings_account(), self.balance)

    @staticmethod
    def create_account(name, cfg, year):
        """ Poor man's account factory """

        type_mapping = {CONFIG_ACCOUNT_TYPE_BASIC : Account,
                        CONFIG_ACCOUNT_TYPE_MORTGAGE : Mortgage,
                        CONFIG_ACCOUNT_TYPE_INVESTMENT : Investment}

        # TBD better error message for unsupported type
        return type_mapping[cfg[CONFIG_TYPE]](name, cfg, year)

#------------------ Investment class

class Investment(Account):
    """ Investment account manages basis and tax consequences from sales. """
    def __init__(self, acct_name, cfg, year):
        Account.__init__(self, acct_name, cfg, year)
        self.basis = Config.eval(CONFIG_INVESTMENT_BASIS, cfg)

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
        assert Config.eval(CONFIG_MORTGAGE_MONTHLY_PAYMENT, cfg) is not None
        self.monthly_payment = Config.eval(CONFIG_MORTGAGE_MONTHLY_PAYMENT, cfg)

    def process_income_and_expenses(self):
        """ Pay the mortgage and reduce principal """
        # TBD Need to stop when mortgage is paid off
        # TBD calculate principal_reduction correctly based on monthly payment and mortgage
        # interest rate

        # Reduce outstanding principal
        principal_reduction = 10000
        self.year.book(self, principal_reduction, "Mortgage Principal Reduction", self)
        # Mortgage payments over the year
        self.year.book(None, self.monthly_payment * -12, "Mortgage Payment", self)

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
        # Trigger account specific annual processing tasks
        for account in self.accounts.values():
            account.process()

        self.process_income_and_expenses()
        self.tax(True)
        self.rebalance_accounts()
        # Post process any remaining capital gains tax from rebalancing
        self.tax(False)

    def init_accounts(self):
        """ Get accounts ready for the year """
        # TBD Knowledge of account configuration should go under the Account class
        if not self.previous:
            for acct_name in Config.cfg[CONFIG_ACCTS]:
                acct_cfg = Config.cfg[CONFIG_ACCTS][acct_name]
                self.accounts[acct_name] = Account.create_account(acct_name, acct_cfg, self)
        else:
            self.accounts = copy.deepcopy(self.previous.accounts) # pylint tag?pylint: disable=unsubscriptable-object
            for account in self.accounts.values():
                account.year = self

    def get_savings_account(self):
        """ Return the savings account """
        return self.accounts[KEY_SAVINGS_ACCT]

    def process_income_and_expenses(self):
        """ Create all income and expenses originating explicitly from configured entries or from
        accounts """
        # Start with income and expenses that are individually configured
        for source in Config.cfg[CONFIG_INCOME_EXPENSES]:
            previous_book_entry = self.get_previous_book_entry(source[CONFIG_NAME])
            if source[CONFIG_TYPE] == CONFIG_LINE_ITEM_TYPE_BASIC:
                book_entry_helper = BasicBookEntryHelper(source, previous_book_entry)
            else:
                assert False # TBD how to raise error if income type not supported
            if Config.filter(source, self.year):
                amount = book_entry_helper.get_amount(self.year)
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
            account = self.get_savings_account()
        account.deposit(amount, appreciation)
        self.books.append(BookEntry(account, amount, name, from_account))

        # Print summary of booking
        if amount > 0:
            expense_income = "Income "
        else:
            expense_income = "Expense"
        from_account_str = ''
        if from_account is not None:
            from_account_str = '(initiated by {})'.format(from_account.name)
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
        for unbal_name in Config.cfg[CONFIG_ACCTS]:
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
                   or account == self.get_savings_account():
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
                                                 self.get_savings_account())
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

    def get_amount(self, year):
        """ Return the configured amount """
        if self.previous_book_entry is not None:
            amount = self.previous_book_entry.amount
        else:
            amount = Config.eval(CONFIG_INCOME_EXPENSE_AMOUNT, self.cfg)

        increase_tuple = Config.eval_multi_value(CONFIG_INCOME_EXPENSE_INCREASE, self.cfg, year,
                                                 True)
        # Process percent increase
        increase_percent = 0
        if CONFIG_INCOME_EXPENSE_INFLATION_ADJUST in self.cfg:
            increase_percent += Config.eval(CONFIG_INFLATION, Config.cfg)
        for income_expense_increase_percent in increase_tuple[0]:
            increase_percent += income_expense_increase_percent
        amount *= 1 + increase_percent
        # Process absolute increase
        for income_expense_increase_absolute in increase_tuple[1]:
            amount += income_expense_increase_absolute

        return amount

    def get_tax_type(self):
        """ All income is reported as taxable income """
        tax_type = None
        if Config.eval(CONFIG_INCOME_EXPENSE_AMOUNT, self.cfg) > 0:
            tax_type = TAX_INCOME
        return tax_type

#------------------ Config class

class Config(ast.NodeTransformer):
    """ Access and evaluate configuration """
    cfg = None # global configuration data

    @staticmethod
    def init(config_file):
        """Loads user preferences from json configuration file"""
        with open(config_file, "r") as infile:
            Config.cfg = json.load(infile)
        Config.validate()

    @staticmethod
    def validate():
        """ Reviews configuration settings for correctness """
        # TBD Need consistent validation and align with validations spread out in other areas
        assert Config.eval(CONFIG_INFLATION, Config.cfg) >= 0 and \
               Config.eval(CONFIG_INFLATION, Config.cfg) <= 1
        assert Config.eval(CONFIG_BIRTH_YEAR, Config.cfg) >= 0 and \
               Config.eval(CONFIG_BIRTH_YEAR, Config.cfg) <= datetime.datetime.now().year

        assert (Config.cfg[CONFIG_INCOME_EXPENSES] is not None
                and len(Config.cfg[CONFIG_INCOME_EXPENSES]) > 0
               )
        for income in Config.cfg[CONFIG_INCOME_EXPENSES]:
            assert income[CONFIG_INCOME__EXPENSES_NAME] is not None
            assert Config.eval(CONFIG_INCOME_EXPENSE_AMOUNT, income) is not None

        assert Config.cfg[CONFIG_ACCTS] is not None and len(Config.cfg[CONFIG_ACCTS]) > 0

    @staticmethod
    def eval(key, cfg):
        """ Evaluate the key's value, resolving variables from global configuration as needed. """
        if key in cfg:
            tree = Config.parse(str(cfg[key]))
            ast.fix_missing_locations(tree)
            return eval(compile(tree, '', mode='eval')) # pylint: disable=eval-used
        return None

    @staticmethod
    def eval_multi_value(key, cfg, year, single_arg_is_percent):
        """ Evaluate the key's value. Multiple values, each with an optional filter are supported.
        Values can be percent or absolute values.
        Values are returned as a tuple of a list of percent values and a list of absolute
        values.
        Values are configured as a list of dictionaries. For simplicity a single dictionary is
        supported as well.
        As a special case a single configurationvalue is also allowed. in that case the argument
        single_arg_is_percent determines whether the value is returned as a percent or absolute
        amount. """
        values_percent = []
        values_absolute = []

        if key in cfg:
            cfg_values = cfg[key]
            # We allow just a single value or a single list of value/config data.
            # Convert these to the general case of a list of dictionaries.
            if not isinstance(cfg_values, list):
                if not isinstance(cfg_values, dict):
                    # Single value
                    if single_arg_is_percent:
                        value_key = CONFIG_PERCENT
                    else:
                        value_key = CONFIG_AMOUNT
                    cfg_values = [{value_key : cfg_values}]
                else:
                    # Single dictionary
                    cfg_values = [cfg_values]
            for cfg_dict in cfg_values:
                if Config.filter(cfg_dict, year):
                    if CONFIG_AMOUNT in cfg_dict:
                        values = values_absolute
                        value_key = CONFIG_AMOUNT
                    elif CONFIG_PERCENT in cfg_dict:
                        values = values_percent
                        value_key = CONFIG_PERCENT
                    else:
                        assert False # TBD better error handling
                    values.append(Config.eval(value_key, cfg_dict))
        return (values_percent, values_absolute)

    @staticmethod
    def parse(expression):
        """ Returns the AST for the provided expression.
        Any variables are resolved from configuration recursively. """
        tree = ast.parse(expression, mode='eval')
        # Walk tree to replace any variables with configuration value
        return Config().visit(tree)

    def visit_Name(self, node): # pylint: disable=invalid-name,no-self-use
        """ Replace variables with configuration values """
        tree = Config.parse(str(Config.cfg[node.id]))
        return ast.copy_location(tree.body, node)

    @staticmethod
    def filter(cfg, year):
        """ Check if year is filtered out via configuration.
        Return False to filter out an entry. """
        start_year = Config.eval(CONFIG_START_YEAR, cfg)
        end_year = Config.eval(CONFIG_END_YEAR, cfg)
        return ((start_year is None or start_year <= year) and
                (end_year is None or end_year >= year)
               )

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
            final_net_worth = years[-1].get_net_worth()
            if final_net_worth < 0:
                color = "red"
            else:
                color = "green"
            outf.write("Final net worth: <FONT COLOR={}>{}</FONT>". \
                format(color, OUTPUT_CURRENCY.format(final_net_worth)))
            outf.write("<HTML><BODY><TABLE>\n")

            # Table header
            outf.write("<TR>")
            outf.write("<TH>Year</TH>")
            outf.write("<TH>Age</TH>")
            outf.write("<TH>Net Worth</TH>")
            for acct_name in Config.cfg[CONFIG_ACCTS]:
                outf.write("<TH>Balance (Year End) {}</TH>".format(acct_name))
            for income_expense_type in income_expense_types:
                if not ~income_expense_types[income_expense_type] & (INCOME|EXPENSE):
                    column_header = "Income/Expense"
                elif income_expense_types[income_expense_type] & EXPENSE:
                    column_header = "Expense"
                elif income_expense_types[income_expense_type] & INCOME:
                    column_header = "Income"
                else:
                    assert False # TBD how to raise error if type not set right
                column_header = "{} {}".format(column_header, income_expense_type[0])
                if income_expense_type[1] is not None:
                    column_header += " (from {})".format(income_expense_type[1])
                outf.write("<TH>{}</TH>".format(column_header))
            outf.write("<TH>Total Income</TH>")
            outf.write("<TH>Total Expenses</TH>")
            outf.write("</TR>\n")

            # Table rows
            for year in years:
                outf.write("<TR>")
                outf.write(OUTPUT_CELL.format(year.year))
                outf.write(OUTPUT_CELL.
                           format(year.year - Config.eval(CONFIG_BIRTH_YEAR, Config.cfg)))
                outf.write(OUTPUT_CELL_RIGHT.format(OUTPUT_CURRENCY.format(year.get_net_worth())))
                for acct_name in Config.cfg[CONFIG_ACCTS]:
                    outf.write(OUTPUT_CELL_RIGHT.
                               format(OUTPUT_CURRENCY.format(year.accounts[acct_name].balance)))
                for income_expense_type in income_expense_types:
                    book_entry = year.get_book_entry(income_expense_type[0]
                                                     , income_expense_type[1])
                    if book_entry is not None:
                        outf.write(OUTPUT_CELL_RIGHT.
                                   format(OUTPUT_CURRENCY.format(book_entry.amount)))
                    else:
                        outf.write(OUTPUT_CELL_RIGHT.format("-"))
                outf.write(OUTPUT_CELL_RIGHT.
                           format(OUTPUT_CURRENCY.format(year.get_total_income())))
                outf.write(OUTPUT_CELL_RIGHT.
                           format(OUTPUT_CURRENCY.format(year.get_total_expenses())))
                outf.write("</TR>\n")

            outf.write("</TABLE></BODY></HTML>\n")

#------------------ Main loop

def main():
    """ Program main entry point """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="configuration file", default="Configuration.json")
    parser.add_argument("-a", "--age", help="age when simulation ends", default=100)
    args = parser.parse_args()

    Config.init(args.config)
    years = []
    previous = None
    for year in range(datetime.datetime.now().year,
                      Config.eval(CONFIG_BIRTH_YEAR, Config.cfg) + int(args.age) + 1):

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
