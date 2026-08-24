def send_charge(amount):
    return {"charged": amount}


def charge(amount):
    if amount < 0:
        raise ValueError("amount must be non-negative")
    return send_charge(amount)
