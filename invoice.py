# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Invoice', 'InvoiceTax']
__metaclass__ = PoolMeta


class Invoice:
    __name__ = 'account.invoice'

    different_currencies = fields.Function(
        fields.Boolean('Different Currencies'),
        'on_change_with_different_currencies')
    company_currency_digits = fields.Function(
        fields.Integer('Company Currency Digits'),
        'on_change_with_company_currency_digits')
    company_untaxed_amount_cache = fields.Numeric('Untaxed (Company Currency)',
        digits=(16, Eval('company_currency_digits', 2)), readonly=True,
        depends=['company_currency_digits'])
    company_untaxed_amount = fields.Function(
        fields.Numeric('Untaxed (Company Currency)',
            digits=(16, Eval('company_currency_digits', 2)), states={
                'invisible': ~Eval('different_currencies', False),
                },
            depends=['different_currencies', 'company_currency_digits']),
        'get_amount')
    company_tax_amount_cache = fields.Numeric('Tax (Company Currency)',
        digits=(16, Eval('company_currency_digits', 2)), readonly=True,
        depends=['company_currency_digits'])
    company_tax_amount = fields.Function(
        fields.Numeric('Tax (Company Currency)',
            digits=(16, Eval('company_currency_digits', 2)), states={
                'invisible': ~Eval('different_currencies', False),
                },
            depends=['different_currencies', 'company_currency_digits']),
        'get_amount')
    company_total_amount_cache = fields.Numeric('Total (Company Currency)',
        digits=(16, Eval('company_currency_digits', 2)), readonly=True,
        depends=['company_currency_digits'])
    company_total_amount = fields.Function(
        fields.Numeric('Total (Company Currency)',
            digits=(16, Eval('company_currency_digits', 2)), states={
                'invisible': ~Eval('different_currencies', False),
                },
            depends=['different_currencies', 'company_currency_digits']),
        'get_amount')

    @fields.depends('company', 'currency')
    def on_change_with_different_currencies(self, name=None):
        if self.company and self.company.currency and self.currency:
            return self.company.currency.id != self.currency.id
        return False

    @fields.depends('company')
    def on_change_with_company_currency_digits(self, name=None):
        if self.company and self.company.currency:
            return self.company.currency.digits
        return 2

    @classmethod
    def get_amount(cls, invoices, names):
        pool = Pool()
        Currency = pool.get('currency.currency')

        new_names = [n for n in names if not n.startswith('company_')]
        for fname in ('untaxed_amount', 'tax_amount', 'total_amount'):
            if 'company_%s' % fname in names and fname not in new_names:
                new_names.append(fname)
        result = super(Invoice, cls).get_amount(invoices, new_names)

        company_names = [n for n in names if n.startswith('company_')]
        if company_names:
            for invoice in invoices:
                for fname in company_names:
                    if getattr(invoice, '%s_cache' % fname):
                        value = getattr(invoice, '%s_cache' % fname)
                    else:
                        with Transaction().set_context(
                                date=invoice.currency_date):
                            value = Currency.compute(invoice.currency,
                                result[fname[8:]][invoice.id],
                                invoice.company.currency, round=True)
                    result.setdefault(fname, {})[invoice.id] = value
        for key in result.keys():
            if key not in names:
                del result[key]
        return result

    @classmethod
    def validate_invoice(cls, invoices):
        for invoice in invoices:
            if invoice.type in ('in_invoice', 'in_credit_note'):
                invoice._save_company_currency_amounts()
        super(Invoice, cls).validate_invoice(invoices)

    @classmethod
    def post(cls, invoices):
        for invoice in invoices:
            invoice._save_company_currency_amounts()
        super(Invoice, cls).post(invoices)

    def _save_company_currency_amounts(self):
        pool = Pool()
        Currency = pool.get('currency.currency')
        with Transaction().set_context(date=self.currency_date):
            for fname in ('untaxed_amount', 'tax_amount', 'total_amount'):
                value = Currency.compute(self.currency, getattr(self, fname),
                    self.company.currency, round=True)
                setattr(self, 'company_%s_cache' % fname, value)
        self.save()


class InvoiceTax:
    __name__ = 'account.invoice.tax'
    company_base_cache = fields.Numeric('Base (Company Currency)',
        digits=(16, Eval('_parent_invoice',
                {}).get('company_currency_digits', 2)), readonly=True)
    company_base = fields.Function(fields.Numeric('Base (Company Currency)',
            digits=(16, Eval('_parent_invoice',
                    {}).get('company_currency_digits', 2)),
            states={
                'invisible': ~Eval('_parent_invoice',
                        {}).get('different_currencies', False),
                }),
        'get_amount')
    company_amount_cache = fields.Numeric('Amount (Company Currency)',
        digits=(16, Eval('_parent_invoice',
                {}).get('company_currency_digits', 2)), readonly=True)
    company_amount = fields.Function(
        fields.Numeric('Amount (Company Currency)',
            digits=(16, Eval('_parent_invoice',
                    {}).get('company_currency_digits', 2)),
            states={
                'invisible': ~Eval('_parent_invoice',
                        {}).get('different_currencies', False),
                }),
        'get_amount')

    @classmethod
    def get_amount(cls, invoice_taxes, names):
        pool = Pool()
        Currency = pool.get('currency.currency')

        result = {}
        for invoice_tax in invoice_taxes:
            for fname in names:
                if getattr(invoice_tax, '%s_cache' % fname):
                    value = getattr(invoice_tax, '%s_cache' % fname)
                else:
                    with Transaction().set_context(
                            date=invoice_tax.invoice.currency_date):
                        value = Currency.compute(invoice_tax.invoice.currency,
                            getattr(invoice_tax, fname[8:]),
                            invoice_tax.invoice.company.currency, round=True)
                result.setdefault(fname, {})[invoice_tax.id] = value
        return result

    @classmethod
    def copy(cls, invoice_taxes, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default['company_base_cache'] = None
        default['company_amount_cache'] = None
        return super(InvoiceTax, cls).copy(invoice_taxes, default=default)
