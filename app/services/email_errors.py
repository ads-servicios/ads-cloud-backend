class EmailDeliveryError(Exception):
    pass


class EmailNotConfiguredError(EmailDeliveryError):
    pass
