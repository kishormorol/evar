def send_charge(amount):
    return {"charged": amount}


def charge(amount):
    return send_charge(amount)
