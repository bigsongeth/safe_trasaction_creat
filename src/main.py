from notion.client import NotionClient
from safe.transaction import SafeTransactionHandler
from safe.api import SafeAPI
from dotenv import load_dotenv
import os
import sys
import traceback

def main():
    # 加载环境变量
    load_dotenv()
    
    try:
        # 1. 从Notion获取已审核的交易
        print("步骤1: 从Notion获取已审核的交易...")
        notion_client = NotionClient()
        transactions = notion_client.get_approved_transactions()
        
        if not transactions:
            print("没有找到需要处理的交易")
            return
            
        print(f"找到 {len(transactions)} 笔待处理交易")
        
        # 2. 准备Safe交易处理器
        print("步骤2: 初始化Safe交易处理器...")
        safe_handler = SafeTransactionHandler()
        
        # 打印交易信息
        print("\n交易数据:")
        for tx in transactions:
            print(f"地址: {tx['address']}")
            print(f"金额: {tx['amount']}")
        
        # 3. 准备批量转账数据
        print("步骤3: 准备批量转账数据...")
        try:
            batch_tx = safe_handler.prepare_batch_transfers(transactions)   
        except Exception as e:
            print(f"准备批量转账数据失败: {str(e)}")
            raise
        
        # 4. 签名交易
        print("步骤4: 签名交易...")
        try:
            signature = safe_handler.sign_transaction(batch_tx)
        except Exception as e:
            print(f"签名交易失败: {str(e)}")
            raise
        
        # 5. 提议或执行交易
        print("步骤5: 提议交易...")
        try:
            # 使用新的方法提议交易
            tx_hash = safe_handler.propose_transaction(batch_tx, signature)
            print(f"交易已提议，哈希: {tx_hash}")
            print("请在Safe钱包中查看和确认交易")
        except Exception as e:
            print(f"提议交易失败: {str(e)}")
            raise
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    main() 