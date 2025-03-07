from typing import List, Dict
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
from web3 import Web3
from eth_account import Account
from hexbytes import HexBytes

# 导入safe-eth-py相关库
from safe_eth.eth import EthereumClient, EthereumNetwork
from safe_eth.safe.api.transaction_service_api import TransactionServiceApi
from safe_eth.safe import Safe
from safe_eth.safe.multi_send import MultiSend, MultiSendTx, MultiSendOperation

load_dotenv()

class SafeTransactionHandler:
    def __init__(self):
        """
        初始化Safe交易处理器
        """
        # 配置信息
        self.network = os.getenv("NETWORK", "sepolia")
        self.rpc_url = os.getenv("RPC_URL")
        self.safe_address = os.getenv("SAFE_ADDRESS")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.usdt_contract_address = os.getenv("USDT_CONTRACT")
        
        print(f"网络: {self.network}")
        print(f"Safe地址: {self.safe_address}")
        print(f"USDT合约地址: {self.usdt_contract_address}")
        
        # 初始化Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        print(f"Web3连接状态: {'成功' if self.w3.is_connected() else '失败'}")
        
        # 初始化以太坊客户端
        self.ethereum_client = EthereumClient(self.rpc_url)
        
        # 设置网络
        if self.network.lower() == 'mainnet':
            self.ethereum_network = EthereumNetwork.MAINNET
            # MultiSendCallOnly合约地址 (mainnet)
            self.multisend_address = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"
        elif self.network.lower() == 'sepolia':
            self.ethereum_network = EthereumNetwork.SEPOLIA
            # MultiSendCallOnly合约地址 (sepolia)
            self.multisend_address = "0x9641d764fc13c8B624c04430C7356C1C7C8102e2"
        else:
            raise ValueError(f"不支持的网络: {self.network}")
        
        print(f"使用MultiSendCallOnly合约地址: {self.multisend_address}")
        
        # 初始化MultiSend
        self.multisend = MultiSend(ethereum_client=self.ethereum_client, address=self.multisend_address)
        
        # 初始化Safe
        self.safe = Safe(self.safe_address, self.ethereum_client)
        
        # 初始化交易服务API
        self.transaction_service_api = TransactionServiceApi(
            network=self.ethereum_network,
            ethereum_client=self.ethereum_client
        )
        
        # USDT ABI
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
        
        # 初始化USDT合约
        self.usdt_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.usdt_contract_address),
            abi=self.usdt_abi
        )
    
    def prepare_batch_transfers(self, transactions: List[Dict]) -> Dict:
        """
        准备批量USDT转账交易，使用MultiSendCallOnly合约
        
        Args:
            transactions: 交易列表，每个交易包含address和amount
            
        Returns:
            构建好的交易数据字典
        """
        print(f"\n找到 {len(transactions)} 笔待处理交易:")
        
        # 先检查USDT余额
        safe_balance = self.usdt_contract.functions.balanceOf(self.safe_address).call()
        print(f"Safe钱包当前USDT余额: {safe_balance / 10**6}")  # USDT有6位小数
        
        total_amount = sum(tx["amount"] for tx in transactions)
        print(f"需要转账的总金额: {total_amount} USDT")
        
        if safe_balance < total_amount * 10**6:
            raise Exception(f"USDT余额不足. 需要: {total_amount} USDT, 当前余额: {safe_balance / 10**6} USDT")
        
        # 准备多个交易
        print("准备多笔USDT转账交易...")
        multi_send_txs = []
        
        for i, tx in enumerate(transactions):
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
                amount_wei = int(Decimal(amount) * Decimal(10**6))  # USDT有6位小数
                print(f"转账金额: {amount} USDT ({amount_wei} 最小单位)")
                
                # 生成USDT转账数据
                print(f"生成USDT转账数据...")
                transfer_data = self.usdt_contract.functions.transfer(
                    address,
                    amount_wei
                ).build_transaction({
                    'chainId': self.w3.eth.chain_id,
                    'gas': 0,
                    'gasPrice': 0,
                    'nonce': 0
                })['data']
                
                print(f"转账数据生成成功: {transfer_data[:10]}...（长度：{len(transfer_data)}）")
                
                # 创建MultiSendTx对象
                multi_send_tx = MultiSendTx(
                    operation=MultiSendOperation.CALL,  # 标准调用
                    to=self.usdt_contract.address,  # USDT合约地址
                    value=0,  # 不发送ETH
                    data=HexBytes(transfer_data)  # 转账数据
                )
                
                multi_send_txs.append(multi_send_tx)
                print(f"交易 {i+1}: 发送 {amount} USDT 给 {address}")
                
            except Exception as e:
                print(f"处理交易时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        if not multi_send_txs:
            raise Exception("没有可执行的交易")
        
        # 获取Safe信息
        print("\n获取Safe信息...")
        safe_info = self.safe.retrieve_all_info()
        print(f"Safe信息: {safe_info}")
        
        # 编码MultiSend数据
        print("编码MultiSend数据...")
        multisend_data = self.multisend.build_tx_data(multi_send_txs)
        print(f"MultiSend数据长度: {len(multisend_data)}")
        
        # 创建Safe交易
        print("创建Safe交易...")
        safe_tx = self.safe.build_multisig_tx(
            to=self.multisend_address,  # MultiSendCallOnly合约地址
            value=0,  # 不发送ETH
            data=HexBytes(multisend_data),  # MultiSend数据
            operation=0  # 0表示标准CALL
        )
        
        print(f"Safe交易哈希: {safe_tx.safe_tx_hash.hex()}")
        
        # 构造API需要的交易数据
        tx_data = {
            "to": self.multisend_address,
            "value": "0",
            "data": multisend_data.hex(),
            "operation": 0,
            "safeTxGas": str(safe_tx.safe_tx_gas),
            "baseGas": str(safe_tx.base_gas),
            "gasPrice": str(safe_tx.gas_price),
            "gasToken": safe_tx.gas_token or "0x0000000000000000000000000000000000000000",
            "refundReceiver": safe_tx.refund_receiver or "0x0000000000000000000000000000000000000000",
            "nonce": str(safe_tx.safe_nonce)
        }
        
        print("\n最终交易数据:")
        print(json.dumps(tx_data, indent=2))
        
        return tx_data
    
    def sign_transaction(self, safe_tx: Dict) -> str:
        """
        使用私钥签名Safe交易
        
        Args:
            safe_tx: 交易数据字典
            
        Returns:
            签名结果字符串
        """
        print("\n开始签名交易...")
        
        try:
            # 确保data是十六进制字符串
            data = safe_tx["data"]
            if isinstance(data, str) and not data.startswith('0x'):
                data = '0x' + data
            
            # 构建SafeTx对象
            tx = self.safe.build_multisig_tx(
                to=self.w3.to_checksum_address(safe_tx["to"]),
                value=int(safe_tx["value"]),
                data=HexBytes(data),
                operation=int(safe_tx["operation"]),
                safe_tx_gas=int(safe_tx["safeTxGas"]),
                base_gas=int(safe_tx["baseGas"]),
                gas_price=int(safe_tx["gasPrice"]),
                gas_token=safe_tx["gasToken"],
                refund_receiver=safe_tx["refundReceiver"],
                safe_nonce=int(safe_tx["nonce"])
            )
            
            # 打印交易哈希
            safe_tx_hash = tx.safe_tx_hash.hex()
            print(f"交易哈希: {safe_tx_hash}")
            
            # 使用私钥签名
            signature = tx.sign(self.private_key)
            print(f"签名成功: {signature}")
            
            return signature
            
        except Exception as e:
            print(f"签名失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def propose_transaction(self, safe_tx: Dict, signature: str) -> str:
        """
        向Safe交易服务提议交易
        
        Args:
            safe_tx: 交易数据字典
            signature: 交易签名
            
        Returns:
            交易哈希
        """
        print("提议Safe交易...")
        
        try:
            # 获取Safe信息
            safe_info = self.safe.retrieve_all_info()
            print(f"Safe阈值: {safe_info.threshold}")
            print(f"所有者数量: {len(safe_info.owners)}")
            
            # 构建SafeTx对象
            data = safe_tx["data"]
            if isinstance(data, str) and not data.startswith('0x'):
                data = '0x' + data
            
            # 使用与sign_transaction相同的方式构建SafeTx对象
            tx = self.safe.build_multisig_tx(
                to=self.w3.to_checksum_address(safe_tx["to"]),
                value=int(safe_tx["value"]),
                data=HexBytes(data),
                operation=int(safe_tx["operation"]),
                safe_tx_gas=int(safe_tx["safeTxGas"]),
                base_gas=int(safe_tx["baseGas"]),
                gas_price=int(safe_tx["gasPrice"]),
                gas_token=safe_tx["gasToken"],
                refund_receiver=safe_tx["refundReceiver"],
                safe_nonce=int(safe_tx["nonce"])
            )
            
            # 使用私钥签名交易
            print("使用私钥签名交易...")
            tx.sign(self.private_key)
            
            # 发送到交易服务
            print("发送交易到Safe交易服务...")
            result = self.transaction_service_api.post_transaction(tx)
            
            if result:
                print("交易已成功提议到Safe服务")
                # 返回我们之前计算的交易哈希
                return tx.safe_tx_hash.hex()
            else:
                raise Exception("交易提议失败")
                
        except Exception as e:
            print(f"提议交易失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        