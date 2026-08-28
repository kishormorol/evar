def send_charge_5(amount):
    return {'charged': amount}


def charge_5(amount):
    if amount < 0:
        raise ValueError('amount must be non-negative')
    return send_charge_5(amount)
