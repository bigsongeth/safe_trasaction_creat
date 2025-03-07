#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
import time

print("步骤1: 开始导入模块...")

# 添加项目根目录到路径，以便可以导入safe-eth-py
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "safe-eth-py"))

try:
    # 导入所需的库
    print("步骤2: 尝试导入 safe-eth 模块...")
    from safe_eth.eth import EthereumClient, EthereumNetwork
    from safe_eth.safe.api.transaction_service_api import TransactionServiceApi
    from safe_eth.safe import Safe
    from safe_eth.safe.multi_send import MultiSend, MultiSendTx, MultiSendOperation
    from hexbytes import HexBytes
    from web3 import Web3
    from eth_account import Account
    import requests
    print("步骤2: 成功导入所有模块")
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)

# 加载环境变量
print("步骤3: 加载环境变量...")
load_dotenv()
print(f"当前路径: {os.getcwd()}")
print(f"环境变量文件路径: {Path(os.getcwd()) / '.env'}")

# 打印环境变量，但隐藏私钥的大部分内容
print("步骤4: 读取环境变量...")
private_key = os.getenv("PRIVATE_KEY")
masked_private_key = private_key[:6] + "..." + private_key[-4:] if private_key else None

print(f"NETWORK: {os.getenv('NETWORK')}")
print(f"RPC_URL: {os.getenv('RPC_URL')}")
print(f"SAFE_ADDRESS: {os.getenv('SAFE_ADDRESS')}")
print(f"PRIVATE_KEY: {masked_private_key}")
print(f"USDT_CONTRACT: {os.getenv('USDT_CONTRACT')}")

# 配置信息
config = {
    "NETWORK": os.getenv("NETWORK"),
    "RPC_URL": os.getenv("RPC_URL"),
    "SAFE_ADDRESS": os.getenv("SAFE_ADDRESS"),
    "PRIVATE_KEY": os.getenv("PRIVATE_KEY"),
    "USDT_CONTRACT": os.getenv("USDT_CONTRACT")
}

# USDT ABI - ERC20转账函数
USDT_ABI = [
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

def test_multisend_web():
    """
    测试模拟网页界面行为，尝试执行批量转账
    """
    print("开始测试模拟网页界面批量转账...")
    
    # 打印配置信息
    print(f"网络: {config['NETWORK']}")
    print(f"Safe地址: {config['SAFE_ADDRESS']}")
    print(f"USDT合约地址: {config['USDT_CONTRACT']}")
    
    try:
        # 设置网络
        print("步骤5: 设置网络...")
        if config['NETWORK'].lower() == 'mainnet':
            network = EthereumNetwork.MAINNET
            tx_service_url = "https://safe-transaction-mainnet.safe.global"
            multisend_address = "0xA238CBeb142c10Ef7Ad8442C6D1f9E89e07e7761"  # Mainnet MultiSend合约地址
        elif config['NETWORK'].lower() == 'sepolia':
            network = EthereumNetwork.SEPOLIA
            tx_service_url = "https://safe-transaction-sepolia.safe.global"
            multisend_address = "0xA238CBeb142c10Ef7Ad8442C6D1f9E89e07e7761"  # Sepolia MultiSend合约地址
        else:
            raise ValueError(f"不支持的网络: {config['NETWORK']}")
        
        # 初始化以太坊客户端
        print("步骤6: 初始化以太坊客户端...")
        ethereum_client = EthereumClient(config["RPC_URL"])
        
        # 验证连接
        print("步骤7: 验证连接...")
        block_number = ethereum_client.w3.eth.block_number
        print(f"当前区块高度: {block_number}")
        
        # 实例化Safe
        print("步骤8: 实例化Safe...")
        safe = Safe(config["SAFE_ADDRESS"], ethereum_client)
        
        # 获取Safe信息
        print("步骤9: 获取Safe信息...")
        safe_info = safe.retrieve_all_info()
        print(f"Safe信息: {safe_info}")
        
        # 创建Web3实例用于编码USDT转账数据
        print("步骤10: 创建Web3实例...")
        w3 = Web3(Web3.HTTPProvider(config["RPC_URL"]))
        
        # 解析USDT合约地址
        print("步骤11: 解析合约地址...")
        usdt_contract_address = w3.to_checksum_address(config["USDT_CONTRACT"])
        
        # 创建USDT合约实例
        print("步骤12: 创建合约实例...")
        usdt_contract = w3.eth.contract(address=usdt_contract_address, abi=USDT_ABI)
        
        # 准备接收地址和金额 (USDT有6位小数)
        recipients = [
            {
                "address": w3.to_checksum_address("0xe8dB51eeFd0D9ad2c4f23BD063043cEfCa3cCe77"),
                "amount": int(Decimal("0.88") * Decimal(10**6))  # 0.88 USDT
            },
            {
                "address": w3.to_checksum_address("0x5AFa5a4ff6A6a6e79Ab0D90a300541f69b3De17D"),
                "amount": int(Decimal("0.5") * Decimal(10**6))   # 0.5 USDT
            },
            {
                "address": w3.to_checksum_address("0x85d85d2d404f6d1970e694090bbeafe2804951e3"),
                "amount": int(Decimal("0.3") * Decimal(10**6))   # 0.3 USDT
            }
        ]
        
        print("步骤13: 准备MultiSend交易数据...")
        
        # 创建MultiSend实例
        multisend = MultiSend(ethereum_client, address=multisend_address)
        
        # 准备多个交易
        print("准备多笔USDT转账交易...")
        multi_send_txs = []
        
        for i, recipient in enumerate(recipients):
            # 生成USDT转账数据
            transfer_data = usdt_contract.functions.transfer(
                recipient["address"],
                recipient["amount"]
            ).build_transaction({
                'chainId': w3.eth.chain_id,
                'gas': 0,
                'gasPrice': 0,
                'nonce': 0
            })['data']
            
            # 创建MultiSendTx对象
            multi_send_tx = MultiSendTx(
                operation=MultiSendOperation.CALL,  # 标准调用
                to=usdt_contract_address,  # USDT合约地址
                value=0,  # 不发送ETH
                data=HexBytes(transfer_data)  # 转账数据
            )
            
            multi_send_txs.append(multi_send_tx)
            print(f"交易 {i+1}: 发送 {recipient['amount'] / 10**6} USDT 给 {recipient['address']}")
        
        # 编码MultiSend数据
        print("步骤14: 编码MultiSend数据...")
        multisend_data = multisend.build_tx_data(multi_send_txs)
        
        print("步骤15: 创建Safe交易...")
        
        # 创建Safe交易 - 使用delegatecall调用MultiSend合约
        safe_tx = safe.build_multisig_tx(
            to=multisend_address,  # MultiSend合约地址
            value=0,  # 不发送ETH
            data=HexBytes(multisend_data),  # MultiSend数据
            operation=1  # 1表示DELEGATE_CALL
        )
        
        print(f"Safe交易哈希: {safe_tx.safe_tx_hash.hex()}")
        
        # 使用私钥签名交易
        print("步骤16: 使用私钥签名交易...")
        signer = Account.from_key(config["PRIVATE_KEY"])
        print(f"签名者地址: {signer.address}")
        
        # 获取签名
        signature = safe_tx.sign(config["PRIVATE_KEY"])
        signature_hex = signature.hex()
        print(f"签名: {signature_hex}")
        
        # 准备API请求数据（模拟网页界面行为）
        print("步骤17: 准备API请求数据...")
        safe_address = config["SAFE_ADDRESS"]
        
        # 构建请求数据
        # 注意：这里直接使用了Web API的格式和字段，而不是通过SDK
        payload = {
            "to": multisend_address,
            "value": "0",
            "data": multisend_data.hex(),
            "operation": 1,  # DELEGATE_CALL
            "safeTxGas": str(safe_tx.safe_tx_gas),
            "baseGas": str(safe_tx.base_gas),
            "gasPrice": str(safe_tx.gas_price),
            "gasToken": safe_tx.gas_token or "0x0000000000000000000000000000000000000000",
            "refundReceiver": safe_tx.refund_receiver or "0x0000000000000000000000000000000000000000",
            "nonce": safe_tx.safe_nonce,
            "contractTransactionHash": safe_tx.safe_tx_hash.hex(),
            "sender": signer.address,
            "signature": signature_hex,
            "origin": "Python SDK Test"
        }
        
        print(f"请求数据: {json.dumps(payload, indent=2)}")
        
        # 尝试通过TransactionService发送交易
        print("步骤18A: 使用SDK的交易服务API发送交易...")
        transaction_service_api = TransactionServiceApi(
            network=network,
            ethereum_client=ethereum_client
        )
        
        try:
            result = transaction_service_api.post_transaction(safe_tx)
            print(f"通过SDK发送交易成功: {result}")
        except Exception as e:
            print(f"通过SDK发送交易失败: {str(e)}")
            
            # 尝试直接使用HTTP请求
            print("步骤18B: 尝试使用HTTP请求直接调用API...")
            url = f"{tx_service_url}/api/v1/safes/{safe_address}/multisig-transactions/"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                print(f"HTTP状态码: {response.status_code}")
                print(f"HTTP响应: {response.text}")
                
                if response.status_code == 201 or response.status_code == 200:
                    print("交易已成功提交到交易服务")
                else:
                    print("提交交易失败")
            except Exception as http_e:
                print(f"HTTP请求失败: {str(http_e)}")
                
        print("步骤19: 测试完成")
        print("请访问Safe Web界面查看交易状态")
        print(f"https://app.safe.global/sepolia:{config['SAFE_ADDRESS']}/transactions/queue")
        
    except Exception as e:
        print(f"交易失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multisend_web() 