# You will probably need more methods from flask but this one is a good start.
from flask import render_template, abort, request

# Import things from Flask that we need.
from accounting import app
from tools import PolicyAccounting

# Import our models
from models import Policy

import datetime


# Routing for the server.
@app.route("/")
def index():
    policies = Policy.query.all()
    policy_numbers = []
    for pol in policies:
        policy_numbers.append(pol.policy_number)
    return render_template('index.html', policy_numbers=policy_numbers)


@app.route("/policy")
def view_policy():
    policy_number = request.args['policy_number']
    date = request.args['date']
    date = datetime.datetime.strptime(date, '%Y%m%d').date()
    policy = Policy.query.filter_by(policy_number=policy_number).one()
    pa = PolicyAccounting(policy.id)
    if policy is None:
        abort(404)

    return render_template('view-policy.html', policy=policy, date=date, pa=pa)
