import asyncio
import os
from onepassword.client import Client
from config import OP_SERVICE_ACCOUNT_NAME, OP_SERVICE_ACCOUNT_TOKEN, OP_VAULT_NAME, OP_ITEM_NAME
from ..utils import logger


# Get MFA code from 1Password
async def get_mfa_code_from_1password():
    try:
        logger.debug("Attempting to login to 1Password to get MFA code...")
        
        # Create client with service account token
        client = await Client.authenticate(
            auth=OP_SERVICE_ACCOUNT_TOKEN,
            integration_name=OP_SERVICE_ACCOUNT_NAME,
            integration_version="v1.0.0",
        )
        
        # Resolve the OTP secret using the op:// URI format
        secret_reference = f"op://{OP_VAULT_NAME}/{OP_ITEM_NAME}/one-time password?attribute=otp"
        mfa_code = await client.secrets.resolve(secret_reference)
        
        logger.debug("Successfully retrieved MFA code from 1Password")
        return mfa_code
        
    except Exception as e:
        logger.error(f"Failed to get MFA code from 1Password: {e}")
        return None