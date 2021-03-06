#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the intern project.

If you have any questions, please contact Amanda at:
    amanda@britecore.com
#######################################################
"""


class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    """
     Returns the balance due on a policy as of a given date
    """
    def return_account_balance(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    """
     Record a payment made on the policy
    """
    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    """
     Check if non-pay notice should be sent
    """
    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.due_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.due_date):
                continue
            else:
                print "THIS POLICY SHOULD HAVE A NON-PAY NOTICE"
                break
        else:
            print "THIS POLICY SHOULD NOT BE IN NON-PAY STATUS"

    """
     Check if policy should be cancelled due to non-pay
    """
    def evaluate_cancel(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                self.cancel_policy(code='Non-Pay', description='Cancelled due to non-payment')
                break
        else:
            print "THIS POLICY SHOULD NOT CANCEL"

    """
     Puts a policy into Canceled status, setting date and descriptions
    """
    def cancel_policy(self, code=None, description=None):
        if not code:
            print "PLEASE PROVIDE A CANCEL CODE (Non-Pay, Underwriting, or Insured Request)"
            return None

        self.policy.status = 'Canceled'
        self.policy.cancel_code = code
        self.policy.cancel_description = description
        self.policy.cancel_date = datetime.now().date()

        db.session.add(self.policy)
        db.session.commit()
        print "POLICY {} CANCELLED".format(self.policy.id)

    """
     Create schedule of invoices based on payment plan
    """
    def make_invoices(self):
        for invoice in self.policy.invoices:
            invoice.deleted = True

        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Quarterly': 4, 'Monthly': 12}

        invoices = []
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date,  # bill_date
                                self.policy.effective_date + relativedelta(months=1),  # due
                                self.policy.effective_date + relativedelta(months=1, days=14),  # cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        schedule = self.policy.billing_schedule
        if schedule == "Annual":
            pass
        elif schedule in billing_schedules:
            num_payments = billing_schedules.get(schedule)
            # desire full-dollar bill amounts, but not always divisible, so add remainder to first installment
            first_invoice.amount_due = first_invoice.amount_due / num_payments + first_invoice.amount_due % num_payments

            for i in range(1, billing_schedules.get(schedule)):
                months_after_eff_date = i*12/num_payments
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)

                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(schedule))
                invoices.append(invoice)
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

################################
# The functions below are for the db and
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

