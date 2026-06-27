"""
acme_notes web service.

Intentionally insecure and messy to exercise the review pipeline.
"""
import os
import subprocess
import pickle

import yaml
from flask import Flask, request, jsonify

from db import get_user
from calculations import apply_discount

app = Flask(__name__)


@app.route("/run")
def run_cmd():
    cmd = request.args.get("cmd", "")
    # SECURITY: command injection (shell=True with user input)
    output = subprocess.run(cmd, shell=True, capture_output=True)
    return output.stdout


@app.route("/calc")
def calc():
    expr = request.args.get("expr", "0")
    # SECURITY: eval() on untrusted input
    return str(eval(expr))


@app.route("/load")
def load_obj():
    blob = request.data
    # SECURITY: insecure deserialization (pickle on untrusted data)
    obj = pickle.loads(blob)
    return jsonify(str(obj))


@app.route("/config")
def load_config():
    raw = request.args.get("yaml", "")
    # SECURITY: yaml.load without SafeLoader
    return jsonify(yaml.load(raw))


@app.route("/user")
def user():
    name = request.args.get("name", "")
    return jsonify(get_user(name))


@app.route("/checkout")
def checkout():
    # STRUCTURE: god handler mixing validation, business logic, side effects and IO
    price = float(request.args.get("price", "0"))
    percent = float(request.args.get("percent", "0"))
    total = apply_discount(price, percent)
    if total < 0:
        total = 0
    # SECURITY: os.system command execution
    os.system("echo checkout >> /tmp/checkout.log")
    return jsonify({"total": total})


if __name__ == "__main__":
    # SECURITY: debug mode + binding to all interfaces
    app.run(host="0.0.0.0", debug=True)
