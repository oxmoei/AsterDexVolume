# AsterDex 交易机器人配置指南

## 🔑 API 配置

### 方法一：直接修改配置文件

编辑 `config.py` 文件，将以下值替换为您的真实 API 密钥：

```python
API_CONFIG = {
    "API_KEY": "您的真实API密钥",
    "SECRET_KEY": "您的真实SECRET密钥",
    "API_SECRET": "您的真实SECRET密钥",
    # ... 其他配置
}
```

### 方法二：使用环境变量（推荐）

1. 创建环境变量文件：
```bash
# 创建 .env 文件
cat > .env << EOF
ASTERDEX_API_KEY=您的真实API密钥
ASTERDEX_SECRET_KEY=您的真实SECRET密钥
ASTERDEX_API_SECRET=您的真实SECRET密钥
EOF
```

2. 或者直接设置环境变量：
```bash
export ASTERDEX_API_KEY="您的真实API密钥"
export ASTERDEX_SECRET_KEY="您的真实SECRET密钥"
export ASTERDEX_API_SECRET="您的真实SECRET密钥"
```

## 🚀 运行程序

配置完成后，运行程序：

```bash
# 使用 Poetry 运行
poetry run python enhanced_volume_trader.py

# 或者直接运行
python enhanced_volume_trader.py
```

## ⚠️ 安全提醒

1. **永远不要**将真实的 API 密钥提交到版本控制系统
2. 建议使用环境变量方式配置 API 密钥
3. 定期轮换您的 API 密钥
4. 确保 API 密钥权限最小化（只开启必要的权限）

## 🔧 故障排除

### API 认证错误
如果看到 `API-key format invalid` 错误：
1. 检查 API 密钥是否正确配置
2. 确认 API 密钥格式是否正确
3. 验证 API 密钥是否已激活

### 网络连接问题
如果遇到连接问题：
1. 检查代理设置是否正确
2. 确认网络连接正常
3. 验证 API 服务器状态
