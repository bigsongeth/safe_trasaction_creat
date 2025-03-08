from typing import List, Dict
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxReceipt, Wei
from eth_account import Account
from eth_typing import ChecksumAddress
from hexbytes import HexBytes

# 导入safe-eth-py相关库
from safe_eth.eth import EthereumClient, EthereumNetwork
from safe_eth.safe import Safe, SafeTx
from safe_eth.safe.api.transaction_service_api import TransactionServiceApi
from safe_eth.safe.multi_send import MultiSend, MultiSendOperation, MultiSendTx

# 导入自定义日志工具
from utils.logger import logger

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
        
        logger.section("初始化Safe交易处理器")
        logger.info(f"网络: {self.network}")
        logger.info(f"Safe地址: {self.safe_address}")
        logger.info(f"USDT合约地址: {self.usdt_contract_address}")
        
        # 初始化Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        logger.info(f"Web3连接状态: {'成功' if self.w3.is_connected() else '失败'}")
        
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
        
        logger.info(f"使用MultiSendCallOnly合约地址: {self.multisend_address}")
        
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
        logger.section("准备批量转账")
        logger.info(f"找到 {len(transactions)} 笔待处理交易")
        
        # 先检查USDT余额
        safe_balance = self.usdt_contract.functions.balanceOf(self.safe_address).call()
        safe_balance_decimal = safe_balance / 10**6  # USDT有6位小数
        
        total_amount = sum(tx["amount"] for tx in transactions)
        logger.info(f"Safe钱包当前USDT余额: {safe_balance_decimal}")
        logger.info(f"需要转账的总金额: {total_amount} USDT")
        
        if safe_balance < total_amount * 10**6:
            raise Exception(f"USDT余额不足. 需要: {total_amount} USDT, 当前余额: {safe_balance_decimal} USDT")
        
        # 准备多个交易
        logger.info("准备多笔USDT转账交易...")
        multi_send_txs = []
        
        for tx in transactions:
            try:
                to_address = tx["address"]
                
                # 检查是否是ENS域名，如果是则解析
                if to_address.endswith(".eth"):
                    try:
                        logger.info(f"检测到ENS域名: {to_address}，尝试解析...")
                        resolved_address = self.w3.ens.address(to_address)
                        if not resolved_address:
                            raise Exception(f"无法解析ENS域名: {to_address}")
                        logger.info(f"成功解析ENS域名 {to_address} 为地址: {resolved_address}")
                        to_address = resolved_address
                    except Exception as e:
                        logger.error(f"ENS域名解析失败 ({to_address}): {str(e)}")
                        raise Exception(f"ENS域名解析失败: {to_address}")
                
                # 确保地址是校验和格式
                to_address = self.w3.to_checksum_address(to_address)
                
                # USDT金额（USDT有6位小数）
                amount = int(tx["amount"] * 10**6)
                
                # 创建USDT转账数据
                transfer_data = self.usdt_contract.functions.transfer(
                    to_address, 
                    amount
                ).build_transaction({
                    'chainId': self.ethereum_network.value,
                    'gas': 100000,
                    'gasPrice': 0,
                    'nonce': 0
                })['data']
                
                # 创建MultiSendTx对象
                multi_send_tx = MultiSendTx(
                    operation=MultiSendOperation.CALL,  # 标准调用
                    to=self.usdt_contract.address,  # USDT合约地址
                    value=0,  # 不发送ETH
                    data=HexBytes(transfer_data)  # 转账数据
                )
                
                multi_send_txs.append(multi_send_tx)
                logger.transaction_info(to_address, tx["amount"])
            except Exception as e:
                logger.error(f"地址格式验证失败 ({tx['address']}): {str(e)}")
                raise
        
        if not multi_send_txs:
            raise Exception("没有可执行的交易")
        
        # 获取Safe信息
        logger.debug("获取Safe信息...")
        safe_info = self.safe.retrieve_all_info()
        logger.debug(f"Safe信息: 阈值={safe_info.threshold}, 所有者数量={len(safe_info.owners)}")
        
        # 编码MultiSend数据
        logger.debug("编码MultiSend数据...")
        multisend_data = self.multisend.build_tx_data(multi_send_txs)
        logger.debug(f"MultiSend数据长度: {len(multisend_data)}")
        
        # 创建Safe交易
        logger.info("创建Safe交易...")
        safe_tx = self.safe.build_multisig_tx(
            to=self.multisend_address,  # MultiSendCallOnly合约地址
            value=0,  # 不发送ETH
            data=HexBytes(multisend_data),  # MultiSend数据
            operation=1  # 1表示DELEGATE_CALL
        )
        
        logger.info(f"Safe交易哈希: {safe_tx.safe_tx_hash.hex()}")
        
        # 构造API需要的交易数据
        tx_data = {
            "to": self.multisend_address,
            "value": "0",
            "data": multisend_data.hex(),
            "operation": 1,  # 修改为1表示DELEGATE_CALL
            "safeTxGas": str(safe_tx.safe_tx_gas),
            "baseGas": str(safe_tx.base_gas),
            "gasPrice": str(safe_tx.gas_price),
            "gasToken": safe_tx.gas_token or "0x0000000000000000000000000000000000000000",
            "refundReceiver": safe_tx.refund_receiver or "0x0000000000000000000000000000000000000000",
            "nonce": str(safe_tx.safe_nonce),
            "safe_tx_hash": safe_tx.safe_tx_hash.hex()
        }
        
        logger.debug("最终交易数据已准备完成")
        
        return tx_data
    
    def sign_transaction(self, safe_tx: Dict) -> str:
        """
        使用私钥签名Safe交易
        
        Args:
            safe_tx: 交易数据字典
            
        Returns:
            签名结果字符串
        """
        logger.section("签名交易")
        
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
            
            # 签名交易
            logger.info("使用私钥签名交易...")
            signature = tx.sign(self.private_key)
            logger.info(f"签名完成: {signature}")
            
            return signature
            
        except Exception as e:
            logger.error(f"签名交易失败: {str(e)}")
            raise
    
    def propose_transaction(self, tx: Dict, signature: bytes) -> str:
        """
        提议Safe交易，将其发送到Safe Transaction Service以便其他所有者可以签名
        
        Args:
            tx: 准备好的交易数据
            signature: 交易的签名
            
        Returns:
            交易哈希
        """
        try:
            logger.section("提议交易")
            
            # 获取发送者地址 - 使用正确的方法
            sender_address = Account.from_key(self.private_key).address
            logger.info(f"发送者地址: {sender_address}")
            
            # 准备交易数据
            tx_data = {
                "to": tx["to"],
                "value": tx["value"],
                "data": tx["data"],
                "operation": tx["operation"],
                "safeTxGas": tx["safeTxGas"],
                "baseGas": tx["baseGas"],
                "gasPrice": tx["gasPrice"],
                "gasToken": tx["gasToken"],
                "refundReceiver": tx["refundReceiver"],
                "nonce": tx["nonce"],
                "contractTransactionHash": tx["safe_tx_hash"],
                "sender": sender_address,
                "signature": signature.hex(),
                "origin": "Safe-CLI",
            }
            
            # 发送交易提议
            logger.info("提交交易到Safe服务...")
            
            # 创建SafeTx对象，这是post_transaction方法所需的
            from safe_eth.safe import SafeTx
            
            safe_tx = SafeTx(
                self.ethereum_client,
                self.safe_address,
                tx["to"],
                tx["value"],
                bytes.fromhex(tx["data"].replace("0x", "")),
                tx["operation"],
                tx["safeTxGas"],
                tx["baseGas"],
                tx["gasPrice"],
                tx["gasToken"],
                tx["refundReceiver"],
                signatures=signature,
                safe_nonce=tx["nonce"],
                chain_id=self.ethereum_network.value,
            )
            
            # 使用正确的方法名称：post_transaction
            result = self.transaction_service_api.post_transaction(safe_tx)
            
            # 检查响应
            if result:
                tx_hash = tx["safe_tx_hash"]
                logger.info(f"交易已成功提议，交易哈希: {tx_hash}")
                logger.info("请在Safe钱包中查看和确认交易")
                return tx_hash
            else:
                logger.error("提议交易失败，服务返回False")
                raise Exception("提议交易失败")
            
        except Exception as e:
            logger.error(f"提议交易失败: {str(e)}")
            raise
        