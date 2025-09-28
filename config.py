#!/usr/bin/env python3
"""
AsterDex 增强交易系统配置文件
请根据您的实际情况修改以下配置
"""

# ==================== API 配置 ====================
API_CONFIG = {
    "API_KEY": "",  # 请在此处填入您的API密钥
    "SECRET_KEY": "",  # 请在此处填入您的API密钥 (与API_SECRET相同)
    "API_SECRET": "",  # 请在此处填入您的API密钥
    "BASE_URL": "https://fapi.asterdex.com",  # 正确的API地址
    "API_VERSION": "v1",  # API版本
    "ALTERNATIVE_ENDPOINTS": {
        "WEBSITE": "https://www.asterdex.com",
        "DOCS": "https://docs.asterdex.com",
        "GITHUB_DOCS": (
            "https://github.com/asterdex/api-docs/blob/master/aster-finance-api.md"
        ),
    },
    "TIMEOUT": 30,
    "MAX_RETRIES": 3,
    "RETRY_DELAY": 1,
    "USE_PROXY": True,  # 是否使用代理
    "PROXY_HTTP": "http://127.0.0.1:7890",  # HTTP代理地址
    "PROXY_HTTPS": "http://127.0.0.1:7890",  # HTTPS代理地址
    "VERIFY_SSL": False,  # 是否验证SSL证书
}

# ==================== WebSocket 配置 ====================
WEBSOCKET_CONFIG = {
    "WS_URL": "wss://fstream.asterdex.com/ws",
    "STREAM_URL": "wss://fstream.asterdex.com/stream",
    "ALTERNATIVE_WS_URLS": [
        "wss://fstream.asterdex.com/ws",
        "wss://fstream.asterdex.com/stream",
    ],
    # 连接配置
    "PING_INTERVAL": 20,
    "PING_TIMEOUT": 10,
    "RECONNECT_INTERVAL": 5,
    "RECONNECT_DELAY": 5,  # 重连延迟 (与RECONNECT_INTERVAL相同)
    "MAX_RECONNECT_ATTEMPTS": 10,
    # 代理配置 - 暂时禁用WebSocket代理以避免连接问题
    "USE_PROXY": False,  # 禁用WebSocket代理
    "PROXY_TYPE": "http",  # http, socks4, socks5
    "PROXY_HOST": "127.0.0.1",
    "PROXY_PORT": 7890,
}

# ==================== 交易配置 ====================
TRADING_CONFIG = {
    # 基础交易参数
    "SYMBOLS": ["BTCUSDT"],  # 交易对列表
    "SYMBOL": "BTCUSDT",  # 主要交易对
    "MIN_SPREAD": 0.001,  # 最小价差 (0.1%)
    "MIN_SPREAD_THRESHOLD": 0.001,  # 最小价差阈值 (与MIN_SPREAD相同)
    "MAX_SPREAD": 0.01,  # 最大价差 (1%)
    "TRADE_AMOUNT": 0.0034,  # 每次交易数量 - 调整为0.002以满足最小名义价值
    "TRADE_QUANTITY": 0.0035,  # 交易数量 - 调整为0.002 (约100 USDT名义价值)
    "MIN_ORDER_SIZE": 0.001,  # 最小订单大小
    "TRADE_INTERVAL": 1.0,  # 交易间隔 (秒)
    # 风险管理
    "MAX_DAILY_LOSS": 100,  # 每日最大亏损 (USDT)
    "MAX_CONSECUTIVE_LOSSES": 700,  # 最大连续亏损次数
    "POSITION_LIMIT": 0.1,  # 最大持仓限制
    "MAX_DAILY_TRADES": 10000,  # 每日最大交易次数
    # 新增：仓位回撤控制
    "MAX_POSITION_DRAWDOWN": 0.02,  # 最大仓位回撤 (2%)
    "DRAWDOWN_WARNING_THRESHOLD": 0.016,  # 回撤警告阈值 (1.6% = 80% * 2%)
    "FORCE_CLOSE_ON_DRAWDOWN": True,  # 回撤超限时强制平仓
    "POSITION_MONITORING_INTERVAL": 1.0,  # 仓位监控间隔 (秒)
    # 交易频率控制
    "MIN_TRADE_INTERVAL": 1,  # 最小交易间隔 (秒)
    "MAX_TRADES_PER_HOUR": 100,  # 每小时最大交易次数
    "MAX_TRADES_PER_DAY": 1000,  # 每日最大交易次数
    # 价格监控
    "PRICE_CHECK_INTERVAL": 0.5,  # 价格检查间隔 (秒)
    "DEPTH_LEVELS": 5,  # 订单簿深度级别
}

# ==================== 日志配置 ====================
LOGGING_CONFIG = {
    "LEVEL": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "FILE": "logs/trading.log",  # 日志文件路径
    "FILE_PATH": "logs/trading.log",  # 备用字段名
    "MAX_FILE_SIZE": 10 * 1024 * 1024,  # 10MB
    "BACKUP_COUNT": 5,
    "CONSOLE_OUTPUT": True,
    "COLOR_OUTPUT": True,
}

# ==================== 策略配置 ====================
STRATEGY_CONFIG = {
    # 策略选择
    "PREFERRED_STRATEGY": "limit",  # "limit" 或 "market"
    # 限价单策略配置
    "LIMIT_ORDER": {
        "BUY_PRICE_OFFSET": 0.0001,  # 买入价格偏移 (0.01%)
        "SELL_PRICE_OFFSET": 0.0001,  # 卖出价格偏移 (0.01%)
        "TIME_IN_FORCE": "IOC",  # IOC, GTC, FOK
        "MAX_WAIT_TIME": 5,  # 最大等待时间(秒)
        "RETRY_COUNT": 3,  # 重试次数
        "PRICE_ADJUSTMENT": 0.00005,  # 价格调整步长
    },
    # 市价单策略配置
    "MARKET_ORDER": {
        "DELAY_BETWEEN_ORDERS": 0.1,  # 订单间延迟(秒)
        "MAX_SLIPPAGE": 0.001,  # 最大滑点 (0.1%)
    },
    # 趋势交易配置
    "TREND_TRADING": {
        "ENABLED": True,  # 启用趋势交易
        "MIN_CONFIDENCE": 0.2,  # 最小趋势置信度
        "DIRECTIONAL_RATIO": 0.7,  # 方向性交易比例 (70%趋势交易, 30%传统刷单)
        "TREND_ANALYSIS": {
            "WINDOW_SIZE": 30,  # 价格历史窗口大小
            "SHORT_MA": 5,  # 短期移动平均
            "LONG_MA": 20,  # 长期移动平均
            "RSI_PERIOD": 14,  # RSI周期
            "VOLATILITY_THRESHOLD": 0.02,  # 波动率阈值
            "MOMENTUM_THRESHOLD": 0.001,  # 动量阈值
        },
        "POSITION_MANAGEMENT": {
            "MAX_POSITION_SIZE": 0.01,  # 最大持仓大小
            "STOP_LOSS": 0.02,  # 止损比例 (2%)
            "TAKE_PROFIT": 0.05,  # 止盈比例 (5%)
            "POSITION_TIMEOUT": 300,  # 持仓超时时间(秒)
        },
    },
    # 手续费优化配置
    "FEE_OPTIMIZATION": {
        "ENABLED": True,  # 启用手续费优化
        "TARGET_MAKER_RATIO": 0.8,  # 目标Maker比例 (80%)
        "FEE_TRACKING": True,  # 启用手续费跟踪
        "DYNAMIC_PRICING": True,  # 动态定价
        "PRICE_OFFSET_ADJUSTMENT": {
            "MIN_OFFSET": 0.00005,  # 最小价格偏移
            "MAX_OFFSET": 0.0005,  # 最大价格偏移
            "ADJUSTMENT_STEP": 0.00001,  # 调整步长
        },
    },
}

# ==================== 数据库配置 ====================
DATABASE_CONFIG = {
    "TYPE": "sqlite",  # sqlite, mysql, postgresql
    "PATH": "data/trading.db",  # SQLite数据库路径
    # 如果使用MySQL/PostgreSQL
    "HOST": "localhost",
    "PORT": 3306,
    "USERNAME": "",
    "PASSWORD": "",
    "DATABASE": "asterdex_trading",
}

# ==================== 通知配置 ====================
NOTIFICATION_CONFIG = {
    "ENABLED": False,
    "WEBHOOK_URL": "",  # Discord/Slack webhook URL
    "EMAIL_ENABLED": False,
    "EMAIL_SMTP": "smtp.gmail.com",
    "EMAIL_PORT": 587,
    "EMAIL_USERNAME": "",
    "EMAIL_PASSWORD": "",
    "EMAIL_TO": "",
}

# ==================== 高级配置 ====================
ADVANCED_CONFIG = {
    # 性能优化
    "ASYNC_ENABLED": True,
    "THREAD_POOL_SIZE": 4,
    "CONNECTION_POOL_SIZE": 10,
    # 数据保存
    "SAVE_TRADE_HISTORY": True,
    "SAVE_PRICE_DATA": True,
    "DATA_RETENTION_DAYS": 30,
    # 调试模式
    "DEBUG_MODE": False,
    "SIMULATION_MODE": True,  # 模拟交易模式
    "DRY_RUN": True,  # 干运行模式（不执行实际交易）
}

# ==================== API状态说明 ====================
API_STATUS_NOTE = """
重要提示：根据连接测试结果，AsterDex API当前可能不可用或需要特殊配置。

测试结果显示：
1. 所有AsterDex API端点都返回SSL错误或连接重置
2. WebSocket连接也失败
3. 代理配置工作正常（Binance API测试成功）

建议的解决方案：
1. 检查AsterDex官方文档获取最新的API端点
2. 联系AsterDex技术支持确认API状态
3. 确认是否需要特殊的API访问权限
4. 考虑使用其他兼容的交易所API进行测试

在API问题解决之前，系统将运行在模拟模式下。
"""


def validate_config():
    """验证配置文件的完整性"""
    errors = []

    # 检查必需的API配置
    if not API_CONFIG.get("API_KEY"):
        errors.append("API_KEY 未配置")

    if not API_CONFIG.get("API_SECRET"):
        errors.append("API_SECRET 未配置")

    # 检查交易配置
    if TRADING_CONFIG["MIN_SPREAD"] >= TRADING_CONFIG["MAX_SPREAD"]:
        errors.append("MIN_SPREAD 必须小于 MAX_SPREAD")

    if TRADING_CONFIG["TRADE_AMOUNT"] < TRADING_CONFIG["MIN_ORDER_SIZE"]:
        errors.append("TRADE_AMOUNT 必须大于等于 MIN_ORDER_SIZE")

    # 检查代理配置
    if API_CONFIG["USE_PROXY"] and not API_CONFIG.get("PROXY_HTTP"):
        errors.append("启用代理但未配置代理地址")

    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("配置验证通过")
    return True


if __name__ == "__main__":
    print("AsterDex 增强交易系统配置")
    print("=" * 50)
    print(API_STATUS_NOTE)
    print("=" * 50)
    validate_config()
