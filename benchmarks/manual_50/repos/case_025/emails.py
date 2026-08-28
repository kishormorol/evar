def build_welcome_email_3(user):
    return f'Welcome {user}'


def build_password_reset_email_3(user):
    return f'Reset password for {user}'


def send(message):
    return {'sent': message}


def send_welcome_email_3(user):
    return send(build_password_reset_email_3(user))
