# Safe交易测试

本测试脚本用于测试使用Safe多签钱包创建和执行交易的功能。特别是，脚本测试创建一笔10 USDT的转账交易到指定地址。

## 测试环境

- 网络: Sepolia测试网
- Safe多签地址: 配置在.env文件中
- USDT合约: Sepolia测试网上的USDT合约地址（配置在.env文件中）
- 目标接收地址: 0xe8dB51eeFd0D9ad2c4f23BD063043cEfCa3cCe77

## 测试步骤

1. 连接到指定的网络（Sepolia）
2. 获取Safe信息，包括所有者和阈值（签名数量要求）
3. 构建USDT转账交易数据
4. 创建Safe交易
5. 使用一个私钥签名交易
6. 根据Safe的阈值决定:
   - 如果阈值>1，则发送到交易服务等待更多签名
   - 如果阈值=1，则直接执行交易

## 运行方法

在Anaconda `safe_env` 环境中运行：

```bash
cd /path/to/safe_trasaction_creat
/opt/anaconda3/envs/safe_env/bin/python testing/test_safe_transaction.py
```

或者在VSCode中使用配置的运行环境。

## 注意事项

1. 确保.env文件包含正确的配置信息
2. 确保私钥有足够的ETH支付gas费
3. 确保用于签名的私钥对应Safe的一个所有者
4. 如果Safe需要多个签名，其他所有者需要通过交易服务完成签名

## 测试结果

如果脚本成功运行，将会:
1. 打印交易哈希
2. 将交易发送到交易服务（如果需要多签）
3. 或者直接执行交易（如果只需要一个签名）

如果出现错误，将打印详细的错误信息。 