This guide shows how to interact with the Safe Transaction Service API to create, sign, and execute transactions with the owners of a Safe account.

The different steps are implemented using Curl requests, the Safe{Core} SDK TypeScript library and the safe-eth-py Python library.

# Prerequisites
- Node.js and npm when using the Safe{Core} SDK.
- Python >= 3.9 when using safe-eth-py.
- Have a Safe account configured with a threshold of 2, where two signatures are needed.




# Steps
## Install dependencies

```bash
pip install safe-eth-py web3 hexbytes
```

## Imports

```bash
from safe_eth.eth import EthereumClient, EthereumNetwork
from safe_eth.safe.api.transaction_service_api import TransactionServiceApi
from safe_eth.safe import Safe
from hexbytes import HexBytes

```

## Create a Safe transaction

```bash
ethereum_client = EthereumClient(config.get("RPC_URL"))

# Instantiate a Safe
safe = Safe(config.get("SAFE_ADDRESS"), ethereum_client)

# Create a Safe transaction
safe_tx = safe.build_multisig_tx(
    config.get("TO"),
    config.get("VALUE"),
    HexBytes(""))

```

## Sign the transaction

```bash
# Sign the transaction with Owner A
safe_tx.sign(config.get("OWNER_A_PRIVATE_KEY"))
```

## Send the transaction to the service

```bash
# Instantiate the Transaction Service API
transaction_service_api = TransactionServiceApi(
    network=EthereumNetwork.SEPOLIA,
    ethereum_client=ethereum_client)

# Send the transaction to the Transaction Service with the signature from Owner A
transaction_service_api.post_transaction(safe_tx)

```

## Collect missing signatures
### Get the pending transaction

```bash
(safe_tx_from_tx_service, _) = transaction_service_api.get_safe_transaction(
    safe_tx_hash)
```

### Add missing signatures

```bash
# Sign the transaction with Owner B
owner_b_signature = safe_tx_from_tx_service.sign(
    config.get("OWNER_B_PRIVATE_KEY"))

# Send the transaction to the Transaction Service with the signature from Owner B
transaction_service_api.post_signatures(
    safe_tx_from_tx_service.safe_tx_hash,
    owner_b_signature)
```

## Execute the transaction

```bash
result = safe_tx_from_tx_service.execute(config.get("OWNER_A_PRIVATE_KEY"))
```

## Get the executed transaction

```bash
transactions = transaction_service_api.get_transactions(
    config.get("SAFE_ADDRESS"))

last_executed_tx = next(
    (x for x in transactions if x.get('isExecuted')),
    None)
```