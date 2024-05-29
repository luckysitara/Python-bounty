# Import necessary libraries
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.rpc.types import TokenAccountOpts
from solana.token_program import token
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import base64

# Step 1: Generate keypair using bip_utils
# Generate a 12-word mnemonic
mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12)  
print(f"Generated Mnemonic: {mnemonic}")

# Generate seed from mnemonic
seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

# Derive the keypair using BIP44 for Solana
bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
account = bip44_mst_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)

# Extract private and public keys
private_key = account.PrivateKey().Raw().ToBytes()
public_key = account.PublicKey().RawCompressed().ToBytes()
print(f"Public Key: {public_key.hex()}")

# Load the keypair in solana-py format
solana_keypair = Keypair.from_secret_key(private_key)

# Step 2: Set up Solana client
client = Client("https://api.devnet.solana.com")

# Step 3: Prepare token transfer details
recipient_address = "RecipientPublicKeyHere"
token_mint_address = PublicKey("TokenMintAddressHere")
source_token_account_address = PublicKey("SourceTokenAccountAddressHere")
destination_token_account_address = PublicKey("DestinationTokenAccountAddressHere")
amount_to_transfer = 1_000_000  # Amount in smallest unit of the token

# Fetch recent blockhash
recent_blockhash = client.get_recent_blockhash()["result"]["value"]["blockhash"]

# Step 4: Create the transfer instruction
transfer_instruction = token.TransferCheckedParams(
    program_id=token.TOKEN_PROGRAM_ID,
    source=source_token_account_address,
    mint=token_mint_address,
    dest=destination_token_account_address,
    owner=solana_keypair.public_key,
    amount=amount_to_transfer,
    decimals=6  # Token decimal places, adjust as needed
)

# Build transaction
transaction = Transaction().add(
    token.transfer_checked(transfer_instruction)
)
transaction.recent_blockhash = recent_blockhash
transaction.sign(solana_keypair)

# Step 5: Send the transaction
response = client.send_transaction(transaction, solana_keypair)
print("Transaction response:", response)
