from notion.client import NotionClient
from safe.transaction import SafeTransactionHandler
from safe.api import SafeAPI
from dotenv import load_dotenv
import os
import ipdb

def main():
    # 加载环境变量
    load_dotenv()
    
    try:
        # 1. 从Notion获取已审核的交易
        notion_client = NotionClient()
        transactions = notion_client.get_approved_transactions()
        
        if not transactions:
            print("没有找到需要处理的交易")
            return
            
        print(f"找到 {len(transactions)} 笔待处理交易")
        
        # 2. 准备Safe交易数据
        safe_handler = SafeTransactionHandler()
        safe_api = SafeAPI()
        
        # 在这里添加调试信息
        print("\n交易数据:")
        for tx in transactions:
            print(f"地址: {tx['address']}")
            print(f"金额: {tx['amount']}")
        
        # 准备批量转账数据
        batch_tx = safe_handler.prepare_batch_transfers(transactions)   
        
        # 3. 签名并提议交易
        signature = safe_handler.sign_transaction(batch_tx)
        result = safe_api.propose_transaction(batch_tx, signature)
        
        print("交易已提议:")
        print(f"Safe Tx Hash: {result['safeTxHash']}")
        print("请在Safe钱包中确认交易")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        # 添加更详细的错误信息
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 