import time
import logging
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.rpc.commitment import Confirmed, Finalized
from spl.token.instructions import get_associated_token_address, create_associated_token_account, transfer_checked, TransferCheckedParams
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from solana.rpc.types import TxOpts

# Set up logging
logging.basicConfig(level=logging.INFO)

# Step 1: Generate keypair using bip_utils
mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)
logging.info(f"Generated Mnemonic: {mnemonic}")

seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
account = bip44_mst_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)

private_key = account.PrivateKey().Raw().ToBytes()
solana_keypair = Keypair.from_secret_key(private_key)

logging.info(f"Public Key: {solana_keypair.public_key}")

# Step 2: Set up Solana client
client = Client("https://api.devnet.solana.com")

# Check the balance of the source account
source_balance = client.get_balance(solana_keypair.public_key)
logging.info(f"Source Balance: {source_balance}")

if source_balance['result']['value'] == 0:
    logging.error("Source account does not have enough SOL to cover transaction fees.")
    exit(1)

# Step 3: Prepare token transfer details
recipient_address = "ByadDW7byVwsyeyoKLmSQRU9cr5129bL8e26EEF7GC2Q"
token_mint_address = PublicKey("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")

source_token_account_address = get_associated_token_address(solana_keypair.public_key, token_mint_address)
logging.info(f"Source Token Account Address: {source_token_account_address}")

destination_token_account_address = get_associated_token_address(PublicKey(recipient_address), token_mint_address)
logging.info(f"Destination Token Account Address: {destination_token_account_address}")

amount_to_transfer = 1_000_000

recent_blockhash_response = client.get_recent_blockhash()
recent_blockhash = recent_blockhash_response["result"]["value"]["blockhash"]
logging.info(f"Recent Blockhash: {recent_blockhash}")

transaction = Transaction()
if not client.get_account_info(source_token_account_address)["result"]["value"]:
    logging.info("Initializing source token account...")
    create_source_account_ix = create_associated_token_account(
        payer=solana_keypair.public_key,
        owner=solana_keypair.public_key,
        mint=token_mint_address
    )
    transaction.add(create_source_account_ix)

if not client.get_account_info(destination_token_account_address)["result"]["value"]:
    logging.info("Initializing destination token account...")
    create_destination_account_ix = create_associated_token_account(
        payer=solana_keypair.public_key,
        owner=PublicKey(recipient_address),
        mint=token_mint_address
    )
    transaction.add(create_destination_account_ix)

transfer_instruction = transfer_checked(
    TransferCheckedParams(
        program_id=PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
        source=source_token_account_address,
        mint=token_mint_address,
        dest=destination_token_account_address,
        owner=solana_keypair.public_key,
        amount=amount_to_transfer,
        decimals=6
    )
)
transaction.add(transfer_instruction)
transaction.recent_blockhash = recent_blockhash
transaction.sign(solana_keypair)

tx_opts = TxOpts(skip_preflight=True, preflight_commitment=Confirmed)
response = client.send_transaction(transaction, solana_keypair, opts=tx_opts)
logging.info("Transaction response: %s", response)

transaction_signature = response['result']
logging.info(f"Transaction Signature: {transaction_signature}")

max_retries = 10
retry_delay = 10

for attempt in range(max_retries):
    transaction_status = client.get_confirmed_transaction(transaction_signature, commitment=Finalized)
    logging.info(f"Attempt {attempt + 1}: Transaction status: {transaction_status}")
    if transaction_status['result'] is not None:
        break
    logging.info(f"Attempt {attempt + 1}: Transaction status not confirmed, retrying in {retry_delay} seconds...")
    time.sleep(retry_delay)

logging.info("Final Transaction status: %s", transaction_status)
