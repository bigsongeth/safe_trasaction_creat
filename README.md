# Notion到Safe多签钱包交易批量处理工具

这是一个集成化工具，用于从Notion数据库获取已审核的交易信息，并自动创建Safe多签钱包的批量转账交易。本工具支持USDT转账交易的批量处理，大大提高了多签钱包管理的效率。

## 📋 功能特点

- **Notion集成**: 直接从Notion数据库获取已审核的交易信息
- **批量交易处理**: 支持多笔USDT转账交易的批量创建
- **MultiSendCallOnly**: 利用Safe的MultiSendCallOnly合约进行高效的批量操作
- **离链签名**: 支持交易的离链签名，提高交易处理的灵活性
- **智能日志系统**: 优化的日志输出，减少冗余信息，提高可读性

## 🛠️ 技术架构

项目由以下主要模块组成:

1. **Notion模块**: 负责与Notion API交互，获取已审核的交易数据
2. **Safe模块**: 处理Safe多签钱包的交易创建、签名和提交
3. **Utils工具**: 包含日志系统等辅助功能

## 📊 日志系统

本项目实现了一个智能的日志系统，具有以下特点:

1. **避免重复信息**: 相同的日志消息只会输出一次，减少终端噪音
2. **分级日志**: 支持DEBUG、INFO、WARNING、ERROR四种日志级别
3. **格式化输出**: 支持简单模式和详细模式两种输出格式
4. **交易信息格式化**: 标准化显示地址和金额信息
5. **分节显示**: 使用分节标题使输出更加清晰

### 配置日志

可以通过环境变量配置日志系统:

```bash
# 在.env文件中设置
LOG_LEVEL=INFO        # 可选: DEBUG, INFO, WARNING, ERROR
VERBOSE_LOGGING=False # 设置为True以显示时间戳和日志级别
```

### 使用方法

```python
from utils.logger import logger

# 基本使用
logger.info("这是一条信息")
logger.error("这是一条错误")

# 分节显示
logger.section("开始处理交易")

# 交易信息格式化
logger.transaction_info("0x1234567890abcdef", 100, "USDT")
```

## 🚀 安装和配置

### 1. 克隆仓库

```bash
git clone https://github.com/bigsongeth/safe_trasaction_creat.git

```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建一个`.env`文件，包含以下配置:

```
# Notion配置
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id

# 以太坊配置
NETWORK=mainnet  # 或 sepolia 等测试网络
RPC_URL=https://your-ethereum-rpc-url

# 私钥配置 (用于签名交易)
PRIVATE_KEY=your_ethereum_private_key

# Safe配置
SAFE_ADDRESS=your_safe_wallet_address
USDT_CONTRACT=usdt_contract_address

# 日志配置
LOG_LEVEL=INFO
VERBOSE_LOGGING=False
```

## 🔧 使用方法

1. **准备Notion数据库**:
   - 创建一个包含交易信息的Notion数据库
   - 确保数据库包含必要的字段: 地址、金额、状态等

2. **运行程序**:

```bash
python src/main.py
```

3. **查看结果**:
   - 程序会自动获取Notion中已审核的交易
   - 创建并签名批量转账交易
   - 将交易提交到Safe Transaction Service
   - 在Safe钱包界面中查看并确认交易

## 📝 离链签名流程

本工具支持Safe交易的离链签名流程:

1. 创建Safe交易
2. 使用第一个所有者私钥签名交易
3. 将交易发送到Safe Transaction Service
4. 其他所有者通过Safe Transaction Service收集并添加签名
5. 达到阈值后执行交易

## 🔗 依赖项

- python-dotenv: 环境变量管理
- notion-client: Notion API客户端
- web3: 与以太坊区块链交互
- eth-account: 以太坊账户管理
- requests: HTTP请求处理
- 其他eth相关依赖

## 📄 许可证

[MIT License](LICENSE) 