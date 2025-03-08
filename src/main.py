from notion.client import NotionClient
from safe.transaction import SafeTransactionHandler
from safe.api import SafeAPI
from dotenv import load_dotenv
from utils.logger import logger
import os
import sys
import traceback

def main():
    # 加载环境变量
    load_dotenv()
    
    try:
        # 1. 从Notion获取已审核的交易
        logger.section("从Notion获取交易")
        notion_client = NotionClient()
        transactions = notion_client.get_approved_transactions()
        
        if not transactions:
            logger.info("没有找到需要处理的交易")
            return
            
        logger.info(f"找到 {len(transactions)} 笔待处理交易")
        
        # 2. 准备Safe交易处理器
        safe_handler = SafeTransactionHandler()
        
        # 打印交易信息
        logger.section("交易数据概览")
        for i, tx in enumerate(transactions):
            logger.transaction_info(tx['address'], tx['amount'])
        
        # 3. 准备批量转账数据
        try:
            batch_tx = safe_handler.prepare_batch_transfers(transactions)   
        except Exception as e:
            logger.error(f"准备批量转账数据失败: {str(e)}")
            raise
        
        # 4. 签名交易
        try:
            signature = safe_handler.sign_transaction(batch_tx)
        except Exception as e:
            logger.error(f"签名交易失败: {str(e)}")
            raise
        
        # 5. 提议或执行交易
        try:
            # 使用新的方法提议交易
            tx_hash = safe_handler.propose_transaction(batch_tx, signature)
            logger.info(f"交易已提议，哈希: {tx_hash}")
            logger.info("请在Safe钱包中查看和确认交易")
        except Exception as e:
            logger.error(f"提议交易失败: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        logger.error("详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    main() 