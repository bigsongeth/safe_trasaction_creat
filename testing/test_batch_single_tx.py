#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
from typing import List

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
    from hexbytes import HexBytes
    from web3 import Web3
    from web3.contract import Contract
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

# BatchTransfer ABI - 假设有这样一个帮助合约用于批量转账
BATCH_TRANSFER_ABI = [
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "token",
                "type": "address"
            },
            {
                "internalType": "address[]",
                "name": "recipients",
                "type": "address[]"
            },
            {
                "internalType": "uint256[]",
                "name": "amounts",
                "type": "uint256[]"
            }
        ],
        "name": "disperseToken",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# USDT ABI - ERC20转账函数和授权函数
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
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"}
        ],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def test_batch_single_tx():
    """
    测试创建单个Safe交易批量执行USDT转账，包含三笔转账：
    1. 0.88 USDT 给 0xe8dB51eeFd0D9ad2c4f23BD063043cEfCa3cCe77
    2. 0.5 USDT 给 0x5AFa5a4ff6A6a6e79Ab0D90a300541f69b3De17D
    3. 0.3 USDT 给 0x85d85d2d404f6d1970e694090bbeafe2804951e3
    """
    print("开始测试Safe单笔批量交易...")
    
    # 打印配置信息
    print(f"网络: {config['NETWORK']}")
    print(f"Safe地址: {config['SAFE_ADDRESS']}")
    print(f"USDT合约地址: {config['USDT_CONTRACT']}")
    
    try:
        # 设置网络
        print("步骤5: 设置网络...")
        if config['NETWORK'].lower() == 'mainnet':
            network = EthereumNetwork.MAINNET
            # Disperse合约地址 (Mainnet)
            disperse_address = "0xD152f549545093347A162Dce210e7293f1452150"
        elif config['NETWORK'].lower() == 'sepolia':
            network = EthereumNetwork.SEPOLIA
            # Disperse合约地址 (Sepolia)
            disperse_address = "0xD152f549545093347A162Dce210e7293f1452150"  # 注意: 这是假设的地址，需要更新为实际Sepolia上的地址
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
        
        # 创建Web3实例
        print("步骤10: 创建Web3实例...")
        w3 = Web3(Web3.HTTPProvider(config["RPC_URL"]))
        
        # 解析地址
        print("步骤11: 解析地址...")
        usdt_contract_address = w3.to_checksum_address(config["USDT_CONTRACT"])
        disperse_contract_address = w3.to_checksum_address(disperse_address)
        
        # 创建合约实例
        print("步骤12: 创建合约实例...")
        usdt_contract = w3.eth.contract(address=usdt_contract_address, abi=USDT_ABI)
        disperse_contract = w3.eth.contract(address=disperse_contract_address, abi=BATCH_TRANSFER_ABI)
        
        # 准备接收地址和金额 (USDT有6位小数)
        recipients = [
            w3.to_checksum_address("0xe8dB51eeFd0D9ad2c4f23BD063043cEfCa3cCe77"),
            w3.to_checksum_address("0x5AFa5a4ff6A6a6e79Ab0D90a300541f69b3De17D"),
            w3.to_checksum_address("0x85d85d2d404f6d1970e694090bbeafe2804951e3")
        ]
        
        amounts = [
            int(Decimal("0.88") * Decimal(10**6)),  # 0.88 USDT
            int(Decimal("0.5") * Decimal(10**6)),   # 0.5 USDT
            int(Decimal("0.3") * Decimal(10**6))    # 0.3 USDT
        ]
        
        total_amount = sum(amounts)
        
        print("步骤13: 准备批量交易数据...")
        print(f"转账总额: {total_amount / 10**6} USDT")
        
        for i, (recipient, amount) in enumerate(zip(recipients, amounts)):
            print(f"交易 {i+1}: 发送 {amount / 10**6} USDT 给 {recipient}")
        
        # 方法1: 使用两步交易实现批量转账
        # 第一步: 授权Disperse合约使用USDT
        # 第二步: 调用Disperse合约进行批量转账
        
        print("步骤14: 构建授权交易数据...")
        approve_data = usdt_contract.functions.approve(
            disperse_contract_address,
            total_amount
        ).build_transaction({
            'nonce': 0,
            'gas': 0,
            'gasPrice': 0
        })['data']
        
        print("步骤15: 构建批量转账数据...")
        batch_transfer_data = disperse_contract.functions.disperseToken(
            usdt_contract_address,
            recipients,
            amounts
        ).build_transaction({
            'nonce': 0,
            'gas': 0,
            'gasPrice': 0
        })['data']
        
        print("步骤16: 创建Safe交易...")
        
        # 先执行授权交易
        print("步骤16.1: 创建授权交易...")
        safe_tx_approve = safe.build_multisig_tx(
            to=usdt_contract_address,  # USDT合约地址
            value=0,  # 不发送ETH
            data=HexBytes(approve_data),  # 授权数据
            operation=0  # 0表示标准CALL
        )
        
        print(f"授权交易哈希: {safe_tx_approve.safe_tx_hash.hex()}")
        
        # 再执行批量转账交易
        print("步骤16.2: 创建批量转账交易...")
        safe_tx_batch = safe.build_multisig_tx(
            to=disperse_contract_address,  # Disperse合约地址
            value=0,  # 不发送ETH
            data=HexBytes(batch_transfer_data),  # 批量转账数据
            operation=0  # 0表示标准CALL
        )
        
        print(f"批量转账交易哈希: {safe_tx_batch.safe_tx_hash.hex()}")
        
        # 实例化交易服务API
        print("步骤17: 实例化交易服务API...")
        transaction_service_api = TransactionServiceApi(
            network=network,
            ethereum_client=ethereum_client
        )
        
        # 如果Safe有多个所有者且阈值大于1，则需要多重签名
        if safe_info.threshold > 1:
            print(f"此Safe需要{safe_info.threshold}个签名")
            
            # 处理授权交易
            print("处理授权交易...")
            safe_tx_approve.sign(config["PRIVATE_KEY"])
            result_approve = transaction_service_api.post_transaction(safe_tx_approve)
            print(f"授权交易已发送到交易服务: {result_approve}")
            
            # 处理批量转账交易
            print("处理批量转账交易...")
            safe_tx_batch.sign(config["PRIVATE_KEY"])
            result_batch = transaction_service_api.post_transaction(safe_tx_batch)
            print(f"批量转账交易已发送到交易服务: {result_batch}")
            
            print("所有交易已提交，请其他所有者通过交易服务完成签名")
            print("注意: 执行顺序很重要 - 先执行授权交易，再执行批量转账交易")
        else:
            # 如果Safe只需要一个签名，可以直接执行交易
            print("Safe只需要一个签名，直接执行交易")
            
            # 执行授权交易
            print("执行授权交易...")
            safe_tx_approve.sign(config["PRIVATE_KEY"])
            result_approve = safe_tx_approve.execute(config["PRIVATE_KEY"])
            tx_hash_approve = result_approve.hex()
            print(f"授权交易已执行，交易哈希: {tx_hash_approve}")
            
            # 等待授权交易确认
            print("等待授权交易确认...")
            tx_receipt_approve = ethereum_client.w3.eth.wait_for_transaction_receipt(tx_hash_approve)
            print(f"授权交易状态: {'成功' if tx_receipt_approve.status == 1 else '失败'}")
            
            if tx_receipt_approve.status == 1:
                # 执行批量转账交易
                print("执行批量转账交易...")
                safe_tx_batch.sign(config["PRIVATE_KEY"])
                result_batch = safe_tx_batch.execute(config["PRIVATE_KEY"])
                tx_hash_batch = result_batch.hex()
                print(f"批量转账交易已执行，交易哈希: {tx_hash_batch}")
                
                # 等待批量转账交易确认
                print("等待批量转账交易确认...")
                tx_receipt_batch = ethereum_client.w3.eth.wait_for_transaction_receipt(tx_hash_batch)
                print(f"批量转账交易状态: {'成功' if tx_receipt_batch.status == 1 else '失败'}")
            else:
                print("授权交易失败，无法执行批量转账交易")
    
    except Exception as e:
        print(f"交易失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_single_tx() 