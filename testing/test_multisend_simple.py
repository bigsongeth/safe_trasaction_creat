#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from hexbytes import HexBytes

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 加载环境变量
load_dotenv()

try:
    # 导入safe-eth-py相关库
    from safe_eth.eth import EthereumClient, EthereumNetwork
    from safe_eth.safe import Safe
    from safe_eth.safe.multi_send import MultiSend, MultiSendTx, MultiSendOperation

    print("成功导入safe-eth-py库")
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)

def test_multisend_simple():
    """
    测试最简单的MultiSendCallOnly功能
    """
    print("开始简化版MultiSendCallOnly测试...")
    
    # 配置信息
    rpc_url = os.getenv("RPC_URL")
    safe_address = os.getenv("SAFE_ADDRESS")
    usdt_contract_address = os.getenv("USDT_CONTRACT")
    network = os.getenv("NETWORK", "sepolia")
    
    print(f"RPC URL: {rpc_url}")
    print(f"Safe地址: {safe_address}")
    print(f"USDT合约地址: {usdt_contract_address}")
    print(f"网络: {network}")
    
    try:
        # 初始化Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        print(f"连接状态: {'成功' if w3.is_connected() else '失败'}")
        print(f"当前区块: {w3.eth.block_number}")
        
        # 初始化以太坊客户端
        ethereum_client = EthereumClient(rpc_url)
        print("成功初始化EthereumClient")
        
        # 设置MultiSendCallOnly合约地址
        if network.lower() == 'mainnet':
            multisend_address = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"
        elif network.lower() == 'sepolia':
            multisend_address = "0x9641d764fc13c8B624c04430C7356C1C7C8102e2"
        else:
            raise ValueError(f"不支持的网络: {network}")
        
        print(f"MultiSendCallOnly合约地址: {multisend_address}")
        
        # 初始化MultiSend
        multisend = MultiSend(ethereum_client=ethereum_client, address=multisend_address)
        print("成功初始化MultiSend")
        
        # USDT ABI - 只包含transfer函数
        usdt_abi = [
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
        usdt_contract = w3.eth.contract(
            address=w3.to_checksum_address(usdt_contract_address),
            abi=usdt_abi
        )
        print("成功初始化USDT合约")
        
        # 准备测试交易
        recipients = [
            {
                "address": w3.to_checksum_address("0xe8dB51eeFd0D9ad2c4f23BD063043cEfCa3cCe77"),
                "amount": 100000  # 0.1 USDT (6位小数)
            }
        ]
        
        # 创建多笔交易
        multi_send_txs = []
        
        for recipient in recipients:
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
            
            print(f"转账数据: {transfer_data[:10]}...（长度：{len(transfer_data)}）")
            
            # 创建MultiSendTx对象
            tx = MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=usdt_contract.address,
                value=0,
                data=HexBytes(transfer_data)
            )
            
            multi_send_txs.append(tx)
            print(f"添加交易: 发送 {recipient['amount'] / 10**6} USDT 到 {recipient['address']}")
        
        # 编码MultiSend数据
        print("编码MultiSend数据...")
        multisend_data = multisend.build_tx_data(multi_send_txs)
        print(f"MultiSend数据长度: {len(multisend_data)}")
        
        # 测试成功
        print("MultiSend数据生成成功!")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multisend_simple() 