import os
import requests
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class SafeAPI:
    def __init__(self):
        self.network = os.getenv("NETWORK", "sepolia")
        self.base_url = f"https://safe-transaction-{self.network}.safe.global/api"
        self.safe_address = os.getenv("SAFE_ADDRESS")

    def get_current_nonce(self) -> int:
        """获取Safe当前nonce"""
        response = requests.get(
            f"{self.base_url}/v1/safes/{self.safe_address}/"
        )
        response.raise_for_status()
        return int(response.json()["nonce"])

    def estimate_safe_transaction(self, safe_tx: Dict) -> Dict:
        """估算Safe交易gas"""
        response = requests.post(
            f"{self.base_url}/v1/safes/{self.safe_address}/multisig-transactions/estimations/",
            json=safe_tx
        )
        response.raise_for_status()
        return response.json()

    def propose_transaction(self, safe_tx: Dict, signature: str) -> Dict:
        """提议新的Safe交易"""
        tx_data = {
            **safe_tx,
            "signature": signature,
            "safe": self.safe_address,
        }
        
        response = requests.post(
            f"{self.base_url}/v1/safes/{self.safe_address}/multisig-transactions/",
            json=tx_data
        )
        response.raise_for_status()
        return response.json() 