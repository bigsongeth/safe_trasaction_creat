from datetime import datetime
from typing import List, Dict

from notion_client import Client
from dotenv import load_dotenv
import os

load_dotenv()

class NotionClient:
    def __init__(self):
        self.client = Client(auth=os.getenv("NOTION_API_KEY"))
        self.database_id = os.getenv("NOTION_DATABASE_ID")

    def get_approved_transactions(self) -> List[Dict]:
        """
        获取已审核的交易数据
        筛选条件：
        1. 月份为2025.2
        2. "审核完毕，Signer"为BigSong
        3. 创建时间在2025.2.1之后
        """
        current_date = datetime.now()
        target_date = datetime(2025, 2, 1)

        query = {
            "database_id": self.database_id,
            "filter": {
                "and": [
                    {
                        "property": "Created time",
                        "date": {
                            "on_or_after": target_date.isoformat()
                        }
                    },
                    {
                        "property": "审核完毕，Signer",
                        "people": {
                            "is_not_empty": True
                        }
                    },
                    {
                        "property": "月份",
                        "select": {
                            "equals": "2025.2"
                        }
                    }
                ]
            }
        }

        results = []
        response = self.client.databases.query(**query)
       #print("Query response:", response)
        
        for page in response["results"]:
            try:
                signer = page["properties"]["审核完毕，Signer"]["people"]
                if signer and any(person["name"] == "BigSong" for person in signer):
                    address = page["properties"]["地址"]["rich_text"][0]["text"]["content"]
                    amount = float(page["properties"]["USDT"]["number"])
                    
                    print("\nNotion数据:")
                    print(f"原始地址内容: {address}")
                    print(f"金额: {amount}")
                    
                    results.append({
                        "address": address,
                        "amount": amount
                    })
            except (KeyError, IndexError) as e:
                print(f"Error processing page {page['id']}: {str(e)}")
                continue

        return results 