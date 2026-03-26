from . import models
from . import controllers
from . import const

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    """Post-install hook to setup payment provider."""
    setup_provider(env, 'paystack')


def uninstall_hook(env):
    """Uninstall hook to reset payment provider."""
    reset_payment_provider(env, 'paystack')