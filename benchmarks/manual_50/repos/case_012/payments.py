def send_charge_1(amount):
    return {'charged': amount}


def charge_1(amount):
    if amount < 0:
        raise ValueError('amount must be non-negative')
    return send_charge_1(amount)
