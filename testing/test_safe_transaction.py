#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal

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

def test_safe_transaction():
    """
    测试创建并执行一笔10USDT的交易
    """
    print("开始测试Safe交易...")
    
    # 打印配置信息
    print(f"网络: {config['NETWORK']}")
    print(f"Safe地址: {config['SAFE_ADDRESS']}")
    print(f"USDT合约地址: {config['USDT_CONTRACT']}")
    
    try:
        # 设置网络
        print("步骤5: 设置网络...")
        if config['NETWORK'].lower() == 'mainnet':
            network = EthereumNetwork.MAINNET
        elif config['NETWORK'].lower() == 'sepolia':
            network = EthereumNetwork.SEPOLIA
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
        
        # 交易接收地址
        recipient = w3.to_checksum_address("0xe8dB51eeFd0D9ad2c4f23BD063043cEfCa3cCe77")
        
        # 创建USDT合约实例
        print("步骤12: 创建合约实例...")
        contract = w3.eth.contract(address=usdt_contract_address, abi=USDT_ABI)
        
        # 准备USDT转账数据 (10 USDT，注意USDT有6位小数)
        amount = int(Decimal("10") * Decimal(10**6))
        
        # 编码转账函数调用
        print("步骤13: 编码转账数据...")
        # 正确使用web3合约方法构建数据
        data = contract.functions.transfer(recipient, amount).build_transaction({
            'chainId': w3.eth.chain_id,
            'gas': 0,  # 这里设置为0，因为Safe会自动计算
            'gasPrice': w3.eth.gas_price,
            'nonce': 0  # 这里设置为0，因为Safe会自动计算
        })['data']
        
        print(f"编码后的数据: {data}")
        
        # 打印交易信息
        print(f"交易接收地址: {recipient}")
        print(f"交易金额: 10 USDT")
        
        # 创建Safe交易
        print("步骤14: 创建Safe交易...")
        safe_tx = safe.build_multisig_tx(
            usdt_contract_address,  # 交易发送到USDT合约
            0,  # ETH数量为0
            HexBytes(data)  # USDT转账数据
        )
        
        # 打印交易哈希
        print(f"Safe交易哈希: {safe_tx.safe_tx_hash.hex()}")
        
        # 验证交易所需的签名数量
        print(f"需要的签名数量: {safe_info.threshold}")
        
        # 实例化交易服务API
        print("步骤15: 实例化交易服务API...")
        transaction_service_api = TransactionServiceApi(
            network=network,
            ethereum_client=ethereum_client
        )
        
        # 如果Safe有多个所有者且阈值大于1，则需要多重签名
        if safe_info.threshold > 1:
            print("此Safe需要多重签名，仅使用当前私钥签名并发送到交易服务")
            
            # 使用提供的私钥签名交易
            print("步骤16: 使用私钥签名交易...")
            safe_tx.sign(config["PRIVATE_KEY"])
            
            # 发送到交易服务
            print("步骤17: 发送到交易服务...")
            result = transaction_service_api.post_transaction(safe_tx)
            print(f"交易已发送到交易服务: {result}")
            print("请其他所有者通过交易服务完成签名")
        else:
            # 如果Safe只需要一个签名，可以直接执行交易
            print("Safe只需要一个签名，直接执行交易")
            
            # 签名并执行交易
            print("步骤16: 签名并执行交易...")
            safe_tx.sign(config["PRIVATE_KEY"])
            result = safe_tx.execute(config["PRIVATE_KEY"])
            
            tx_hash = result.hex()
            print(f"交易已执行，交易哈希: {tx_hash}")
            
            # 等待交易确认
            print("步骤17: 等待交易确认...")
            tx_receipt = ethereum_client.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"交易状态: {'成功' if tx_receipt.status == 1 else '失败'}")
    
    except Exception as e:
        print(f"交易失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_safe_transaction() 