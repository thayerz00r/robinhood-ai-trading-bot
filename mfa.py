import pyotp
from onepassword import Client
from config import ROBINHOOD_MFA_SECRET, OP_SERVICE_ACCOUNT_NAME, OP_SERVICE_ACCOUNT_TOKEN, OP_VAULT_NAME, OP_ITEM_NAME
from log import log_debug, log_error

# Get MFA code from 1Password
async def get_from_1password():
    try:
        log_debug("Attempting to login to 1Password to get MFA code...")
        onePasswordClient = await Client.authenticate(
            auth=OP_SERVICE_ACCOUNT_TOKEN,
            integration_name=OP_SERVICE_ACCOUNT_NAME,
            integration_version="v1.0.0",
        )
        mfa_code = await onePasswordClient.secrets.resolve("op://" + OP_VAULT_NAME + "/" + OP_ITEM_NAME + "/one-time password?attribute=otp")
        return mfa_code
    except Exception as e:
        log_error(f"Failed to get MFA code from 1Password: {e}")
        return None

# Get MFA code from secret if configured
def get_from_secret():
    if ROBINHOOD_MFA_SECRET:
        mfa_code = pyotp.TOTP(ROBINHOOD_MFA_SECRET).now()
        log_debug(f"Generated MFA code based on MFA secret: {mfa_code}")
        return mfa_code
    return None
