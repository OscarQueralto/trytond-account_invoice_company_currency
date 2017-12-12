=================================
Invoice Scenario Company Currency
=================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Install account_invoice_company_currency::

    >>> config = activate_modules('account_invoice_company_currency')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'EUR')])
    >>> if not currencies:
    ...     eur = Currency(name='Euro', symbol=u'€', code='EUR',
    ...         rounding=Decimal('0.01'))
    ...     eur.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('2.0'), currency=eur).save()
    ... else:
    ...     eur, = currencies

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create tax::

    >>> tax = set_tax_code(create_tax(Decimal('.10')))
    >>> tax.save()
    >>> invoice_base_code = tax.invoice_base_code
    >>> invoice_tax_code = tax.invoice_tax_code
    >>> credit_note_base_code = tax.credit_note_base_code
    >>> credit_note_tax_code = tax.credit_note_tax_code

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.customer_taxes.append(tax)
    >>> template.save()
    >>> product, = template.products

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create invoice with alternate currency::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.payment_term = payment_term
    >>> invoice.currency = eur
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('80')
    >>> line.amount
    Decimal('400.00')
    >>> line = invoice.lines.new()
    >>> line.account = revenue
    >>> line.description = 'Test'
    >>> line.quantity = 1
    >>> line.unit_price = Decimal(20)
    >>> line.amount
    Decimal('20.00')
    >>> invoice.save()
    >>> invoice.untaxed_amount
    Decimal('420.00')
    >>> invoice.tax_amount
    Decimal('40.00')
    >>> invoice.total_amount
    Decimal('460.00')
    >>> invoice.company_untaxed_amount
    Decimal('210.00')
    >>> invoice.company_tax_amount
    Decimal('20.00')
    >>> invoice.company_total_amount
    Decimal('230.00')
    >>> invoice.click('post')
    >>> invoice.different_currencies
    True
    >>> invoice.state
    u'posted'
    >>> invoice.untaxed_amount
    Decimal('420.00')
    >>> invoice.tax_amount
    Decimal('40.00')
    >>> invoice.total_amount
    Decimal('460.00')
    >>> invoice.company_untaxed_amount
    Decimal('210.00')
    >>> invoice.company_tax_amount
    Decimal('20.00')
    >>> invoice.company_total_amount
    Decimal('230.00')
    >>> tax, = invoice.taxes
    >>> tax.base, tax.amount
    (Decimal('400.00'), Decimal('40.00'))
    >>> tax.company_base, tax.company_amount
    (Decimal('200.00'), Decimal('20.00'))
    >>> line1, line2 = invoice.lines
    >>> line1.amount, line1.company_amount
    (Decimal('400.00'), Decimal('200.00'))
    >>> line1.amount, line1.company_amount
    (Decimal('400.00'), Decimal('200.00'))
    >>> line2.amount, line2.company_amount
    (Decimal('20.00'), Decimal('10.00'))
