from typing import List, Dict
import os
from web3 import Web3
from eth_account import Account
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe, SafeTx
from dotenv import load_dotenv
import requests
import json

load_dotenv()

class SafeTransactionHandler:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.safe_address = os.getenv("SAFE_ADDRESS")
        self.usdt_contract = os.getenv("USDT_CONTRACT")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        # 使用Safe Transaction Service API
        self.network = os.getenv("NETWORK", "sepolia")  # 默认使用 sepolia 测试网
        self.base_url = f"https://safe-transaction-{self.network}.safe.global/api/v1"
        
        # 初始化 Safe SDK 客户端
        self.ethereum_client = EthereumClient(self.w3)
        
        # USDT ABI - 添加 balanceOf 方法
        self.usdt_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        self.usdt_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.usdt_contract),
            abi=self.usdt_abi
        )

    def prepare_batch_transfers(self, transactions: List[Dict]) -> Dict:
        """
        准备批量USDT转账交易
        """
        multisend_txs = []
        
        print(f"\n找到 {len(transactions)} 笔待处理交易:")
        
        # 先检查USDT余额
        safe_balance = self.usdt_contract.functions.balanceOf(self.safe_address).call()
        print(f"Safe钱包当前USDT余额: {safe_balance / 10**6}")  # USDT有6位小数
        
        total_amount = sum(tx["amount"] for tx in transactions)
        print(f"需要转账的总金额: {total_amount} USDT")
        
        if safe_balance < total_amount * 10**6:
            raise Exception(f"USDT余额不足. 需要: {total_amount} USDT, 当前余额: {safe_balance / 10**6} USDT")
        
        for tx in transactions:
            try:
                raw_address = tx["address"]
                print("\nSafe处理:")
                print(f"1. 收到的原始地址: {raw_address}")
                
                clean_address = raw_address.split()[0]
                print(f"2. 清理后的地址: {clean_address}")
                
                try:
                    address = self.w3.to_checksum_address(clean_address)
                    print(f"3. 校验后的地址: {address}")
                except Exception as e:
                    print(f"地址格式验证失败 ({clean_address}): {str(e)}")
                    continue
                    
                amount = tx["amount"]
                print(f"转账金额: {amount} USDT")
                
                # 构造USDT transfer数据
                transfer_data = self.usdt_contract.functions.transfer(
                    address,
                    int(amount * 10**6)  # USDT有6位小数
                ).build_transaction({
                    "from": self.safe_address,
                    "nonce": 0
                })
                
                multisend_txs.append({
                    "to": self.usdt_contract.address,
                    "data": transfer_data["data"],
                    "value": 0,
                    "operation": 0
                })
                print(f"已添加交易: {amount} USDT -> {address}")
                
            except Exception as e:
                print(f"处理交易时出错: {str(e)}")
                continue

        if not multisend_txs:
            raise Exception("没有可执行的交易")

        try:
            # 使用Safe API获取当前nonce
            response = requests.get(f"{self.base_url}/safes/{self.safe_address}/")
            response.raise_for_status()
            nonce = response.json()["nonce"]
            
            # 构造交易数据
            tx_data = {
                "to": self.usdt_contract.address,
                "value": "0",  # API 期望字符串格式的数字
                "data": multisend_txs[0]["data"],
                "operation": 0,
                "safeTxGas": "0",
                "baseGas": "0",
                "gasPrice": "0",
                "gasToken": "0x0000000000000000000000000000000000000000",
                "refundReceiver": "0x0000000000000000000000000000000000000000",
                "nonce": str(nonce)  # 转换为字符串
            }
            
            # 确保data是十六进制字符串
            if isinstance(tx_data["data"], int):
                tx_data["data"] = hex(tx_data["data"])
            elif not isinstance(tx_data["data"], str) or not tx_data["data"].startswith('0x'):
                tx_data["data"] = '0x' + tx_data["data"] if isinstance(tx_data["data"], str) else '0x'
            
            print("\n发送给API的数据:")
            print(json.dumps(tx_data, indent=2))
            
            # 获取gas估算
            response = requests.post(
                f"{self.base_url}/safes/{self.safe_address}/multisig-transactions/estimations/",
                json=tx_data
            )
            response.raise_for_status()
            gas_estimated = response.json()
            
            print("Gas估算结果:", gas_estimated)
            
            # 更新gas信息
            tx_data.update({
                "safeTxGas": gas_estimated.get("safeTxGas", "0"),
                # 其他gas参数保持为"0"
                "baseGas": "0",
                "gasPrice": "0"
            })
            
            # 打印最终的交易数据
            print("\n最终交易数据:")
            print(json.dumps(tx_data, indent=2))
            
            return tx_data
            
        except Exception as e:
            print(f"创建Safe交易失败: {str(e)}")
            raise
        
    def sign_transaction(self, safe_tx: Dict) -> str:
        """
        使用私钥签名Safe交易
        """
        account = Account.from_key(self.private_key)
        
        # 打印调试信息
        print("\n开始签名交易:")
        print("交易数据:", json.dumps(safe_tx, indent=2))
        
        try:
            # 重新初始化 ethereum_client，使用 RPC URL
            ethereum_client = EthereumClient(os.getenv("RPC_URL"))
            
            # 确保data是十六进制字符串
            data = safe_tx["data"]
            if isinstance(data, int):
                data = hex(data)
            elif not isinstance(data, (bytes, str)) or (isinstance(data, str) and not data.startswith('0x')):
                data = '0x' + data if isinstance(data, str) else '0x'
                
            tx = SafeTx(
                ethereum_client,  # 使用新创建的 ethereum_client
                self.safe_address,
                safe_tx["to"],
                int(safe_tx["value"]),
                data,  # 使用处理后的data
                safe_tx["operation"],
                int(safe_tx["safeTxGas"]),
                int(safe_tx["baseGas"]),
                int(safe_tx["gasPrice"]),
                safe_tx["gasToken"],
                safe_tx["refundReceiver"],
                int(safe_tx["nonce"])
            )
            
            # 打印交易哈希信息
            safe_tx_hash = tx.safe_tx_hash.hex()
            print(f"交易哈希: {safe_tx_hash}")
            print(f"签名者地址: {account.address}")
            
            # 使用私钥的十六进制表示进行签名
            signature = tx.sign(account.key.hex())
            print("签名成功:", signature)
            return signature
            
        except Exception as e:
            print(f"签名失败: {str(e)}")
            raise 

        