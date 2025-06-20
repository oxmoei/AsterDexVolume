#!/usr/bin/env python3
import websocket
import json
import threading
import time
import hmac
import hashlib
import requests
import urllib.parse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import sys
import signal
import urllib3
import ssl
from config import *
from trend_analyzer_simple import TrendAnalyzer, TrendBasedTradeDecision

# 禁用SSL警告（代理环境下可能需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EnhancedLogger:
    """增强日志系统"""
    
    @staticmethod
    def setup_logger():
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, LOGGING_CONFIG["LEVEL"]))
        
        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 文件处理器 (带轮转)
        file_handler = RotatingFileHandler(
            LOGGING_CONFIG["FILE"],
            maxBytes=LOGGING_CONFIG["MAX_FILE_SIZE"],
            backupCount=LOGGING_CONFIG["BACKUP_COUNT"],
            encoding='utf-8'  # 添加UTF-8编码支持
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 控制台处理器 - 使用UTF-8编码
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger

class TradingStatistics:
    """交易统计"""
    
    def __init__(self):
        self.reset_stats()
    
    def reset_stats(self):
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_volume = 0
        self.total_pnl = 0
        self.start_time = time.time()
        self.daily_trades = 0
        self.daily_pnl = 0
        self.last_reset_date = datetime.now().date()
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        # 手续费统计
        self.total_fees = 0
        self.maker_trades = 0
        self.taker_trades = 0
        self.estimated_fee_savings = 0
        self.daily_fees = 0
    
    def add_trade(self, success, volume, pnl=0, is_maker=False, fee=0):
        self.total_trades += 1
        self.total_volume += volume
        self.total_pnl += pnl
        self.total_fees += fee
        
        # 重置日统计
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_trades = 0
            self.daily_pnl = 0
            self.daily_fees = 0
            self.last_reset_date = current_date
        
        self.daily_trades += 1
        self.daily_pnl += pnl
        self.daily_fees += fee
        
        # Maker/Taker统计
        if is_maker:
            self.maker_trades += 1
        else:
            self.taker_trades += 1
        
        if success:
            self.successful_trades += 1
            self.consecutive_losses = 0
        else:
            self.failed_trades += 1
            self.consecutive_losses += 1
            self.max_consecutive_losses = max(
                self.max_consecutive_losses, 
                self.consecutive_losses
            )
    
    def get_success_rate(self):
        if self.total_trades == 0:
            return 0
        return (self.successful_trades / self.total_trades) * 100
    
    def get_maker_ratio(self):
        """获取Maker订单比例"""
        if self.total_trades == 0:
            return 0
        return (self.maker_trades / self.total_trades) * 100
    
    def get_runtime_hours(self):
        return (time.time() - self.start_time) / 3600
    
    def get_trades_per_hour(self):
        runtime = self.get_runtime_hours()
        if runtime == 0:
            return 0
        return self.total_trades / runtime
    
    def get_average_fee_per_trade(self):
        """获取平均每笔交易手续费"""
        if self.total_trades == 0:
            return 0
        return self.total_fees / self.total_trades
    
    def print_stats(self):
        logging.info("=" * 50)
        logging.info("[交易统计] 交易统计报告")
        logging.info("=" * 50)
        logging.info(f"总交易次数: {self.total_trades}")
        logging.info(f"成功交易: {self.successful_trades}")
        logging.info(f"失败交易: {self.failed_trades}")
        logging.info(f"成功率: {self.get_success_rate():.2f}%")
        logging.info(f"总交易量: {self.total_volume:.6f}")
        logging.info(f"总盈亏: {self.total_pnl:.4f} USDT")
        logging.info(f"今日交易: {self.daily_trades}")
        logging.info(f"今日盈亏: {self.daily_pnl:.4f} USDT")
        logging.info(f"运行时间: {self.get_runtime_hours():.2f} 小时")
        logging.info(f"交易频率: {self.get_trades_per_hour():.2f} 次/小时")
        logging.info(f"连续亏损: {self.consecutive_losses}")
        logging.info(f"最大连续亏损: {self.max_consecutive_losses}")
        
        # 手续费统计
        logging.info("=" * 30)
        logging.info("[费用统计] 手续费分析")
        logging.info("=" * 30)
        logging.info(f"总手续费: {self.total_fees:.6f} USDT")
        logging.info(f"今日手续费: {self.daily_fees:.6f} USDT")
        logging.info(f"平均每笔手续费: {self.get_average_fee_per_trade():.6f} USDT")
        logging.info(f"Maker交易: {self.maker_trades} ({self.get_maker_ratio():.1f}%)")
        logging.info(f"Taker交易: {self.taker_trades} ({100-self.get_maker_ratio():.1f}%)")
        
        # 费用优化建议
        target_maker_ratio = STRATEGY_CONFIG["FEE_OPTIMIZATION"]["TARGET_MAKER_RATIO"] * 100
        current_maker_ratio = self.get_maker_ratio()
        
        if current_maker_ratio < target_maker_ratio:
            logging.warning(f"[费用优化] Maker比例 ({current_maker_ratio:.1f}%) 低于目标 ({target_maker_ratio:.1f}%)")
            logging.warning("[费用优化] 建议: 增加限价单等待时间或调整价格偏移")
        else:
            logging.info(f"[费用优化] Maker比例达标 ({current_maker_ratio:.1f}% >= {target_maker_ratio:.1f}%)")
        
        logging.info("=" * 50)

class RiskManager:
    """风险管理器"""
    
    def __init__(self, stats):
        self.stats = stats
        self.emergency_stop = False
        self.daily_loss = 0
        self.last_reset_date = datetime.now().date()
        
        # 新增：仓位回撤控制 - 从配置文件读取参数
        self.position_peak_value = {}  # 记录每个仓位的峰值
        self.position_entry_value = {}  # 记录仓位开仓时的价值
        self.max_drawdown_percent = TRADING_CONFIG.get("MAX_POSITION_DRAWDOWN", 0.06)  # 从配置读取，默认6%
        self.drawdown_warning_threshold = TRADING_CONFIG.get("DRAWDOWN_WARNING_THRESHOLD", 0.048)  # 从配置读取
        self.force_close_enabled = TRADING_CONFIG.get("FORCE_CLOSE_ON_DRAWDOWN", True)  # 是否启用强制平仓
        self.position_monitoring_enabled = True
        
        logging.info(f"[风险管理] 仓位回撤控制已启用")
        logging.info(f"[风险管理] 最大回撤限制: {self.max_drawdown_percent*100:.1f}%")
        logging.info(f"[风险管理] 回撤警告阈值: {self.drawdown_warning_threshold*100:.1f}%")
        logging.info(f"[风险管理] 强制平仓: {'启用' if self.force_close_enabled else '禁用'}")
    
    def update_position_value(self, symbol, current_price, position_size):
        """更新仓位价值并检查回撤"""
        if abs(position_size) < 0.0001:  # 没有仓位
            if symbol in self.position_peak_value:
                del self.position_peak_value[symbol]
            if symbol in self.position_entry_value:
                del self.position_entry_value[symbol]
            return True
        
        current_value = abs(position_size * current_price)
        
        # 初始化仓位记录
        if symbol not in self.position_entry_value:
            self.position_entry_value[symbol] = current_value
            self.position_peak_value[symbol] = current_value
            logging.info(f"[风险管理] {symbol} 新仓位建立，初始价值: {current_value:.2f} USDT")
            return True
        
        # 更新峰值
        if current_value > self.position_peak_value[symbol]:
            self.position_peak_value[symbol] = current_value
            logging.debug(f"[风险管理] {symbol} 仓位价值创新高: {current_value:.2f} USDT")
        
        # 计算回撤
        peak_value = self.position_peak_value[symbol]
        drawdown = (peak_value - current_value) / peak_value
        drawdown_percent = drawdown * 100
        
        logging.debug(f"[风险管理] {symbol} 当前回撤: {drawdown_percent:.2f}% (峰值: {peak_value:.2f}, 当前: {current_value:.2f})")
        
        # 检查回撤限制
        if drawdown > self.max_drawdown_percent:
            logging.error(f"[风险管理] {symbol} 仓位回撤超限: {drawdown_percent:.2f}% > {self.max_drawdown_percent*100:.1f}%")
            logging.error(f"[风险管理] 峰值价值: {peak_value:.2f} USDT, 当前价值: {current_value:.2f} USDT")
            if self.force_close_enabled:
                logging.error(f"[风险管理] 触发强制平仓保护")
                return False
            else:
                logging.warning(f"[风险管理] 强制平仓已禁用，仅记录风险")
        
        # 回撤警告 - 使用配置的警告阈值
        if drawdown > self.drawdown_warning_threshold:
            logging.warning(f"[风险管理] {symbol} 仓位回撤接近限制: {drawdown_percent:.2f}% (警告阈值: {self.drawdown_warning_threshold*100:.1f}%, 限制: {self.max_drawdown_percent*100:.1f}%)")
            logging.warning(f"[风险管理] 建议关注市场走势，考虑手动调整仓位")
        
        return True
    
    def check_risk_limits(self):
        """检查风险限制"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_loss = 0
            self.last_reset_date = current_date
        
        # 检查日亏损限制
        if abs(self.stats.daily_pnl) > TRADING_CONFIG["MAX_DAILY_LOSS"]:
            logging.error(f"[风险管理] 达到日亏损限制: {abs(self.stats.daily_pnl):.4f} USDT")
            self.emergency_stop = True
            return False
        
        # 检查连续亏损
        if self.stats.consecutive_losses >= TRADING_CONFIG["MAX_CONSECUTIVE_LOSSES"]:
            logging.error(f"[风险管理] 连续亏损次数过多: {self.stats.consecutive_losses}")
            self.emergency_stop = True
            return False
        
        return True
    
    def force_close_position(self, symbol, api_instance):
        """强制平仓"""
        try:
            logging.warning(f"[风险管理] 开始强制平仓 {symbol}")
            
            # 获取当前持仓
            position_info = api_instance.get_position_risk(symbol)
            if not position_info:
                logging.error(f"[风险管理] 无法获取 {symbol} 持仓信息")
                return False
            
            for position in position_info:
                if position['symbol'] == symbol:
                    position_amt = float(position['positionAmt'])
                    if abs(position_amt) > 0.001:
                        # 确定平仓方向
                        side = 'SELL' if position_amt > 0 else 'BUY'
                        quantity = abs(position_amt)
                        
                        # 市价单强制平仓
                        close_order = api_instance.place_market_order(
                            symbol, side, quantity, reduce_only=True
                        )
                        
                        if close_order and 'orderId' in close_order:
                            logging.info(f"[风险管理] {symbol} 强制平仓成功: {side} {quantity}")
                            # 重置仓位记录
                            if symbol in self.position_peak_value:
                                del self.position_peak_value[symbol]
                            if symbol in self.position_entry_value:
                                del self.position_entry_value[symbol]
                            return True
                        else:
                            logging.error(f"[风险管理] {symbol} 强制平仓失败: {close_order}")
                            return False
            
            logging.info(f"[风险管理] {symbol} 无需平仓（无持仓）")
            return True
            
        except Exception as e:
            logging.error(f"[风险管理] 强制平仓异常: {e}")
            return False
    
    def get_position_risk_report(self):
        """获取仓位风险报告"""
        if not self.position_peak_value:
            return "当前无持仓"
        
        report = []
        report.append("=" * 50)
        report.append("[仓位风险] 回撤监控报告")
        report.append("=" * 50)
        
        for symbol in self.position_peak_value:
            peak_value = self.position_peak_value[symbol]
            entry_value = self.position_entry_value.get(symbol, peak_value)
            
            # 这里需要获取当前价格来计算实时回撤
            # 在实际使用中，应该传入当前价格
            report.append(f"{symbol}:")
            report.append(f"  开仓价值: {entry_value:.2f} USDT")
            report.append(f"  峰值价值: {peak_value:.2f} USDT")
            report.append(f"  回撤限制: {self.max_drawdown_percent*100:.1f}%")
        
        report.append("=" * 50)
        return "\n".join(report)
    
    def should_stop_trading(self):
        return self.emergency_stop

class EnhancedAsterDexAPI:
    """增强版AsterDex API"""
    
    def __init__(self):
        self.api_key = API_CONFIG["API_KEY"]
        self.secret_key = API_CONFIG["SECRET_KEY"]
        self.base_url = API_CONFIG["BASE_URL"]
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        # 设置代理
        if API_CONFIG.get("USE_PROXY", False):
            self.session.proxies = {
                'http': API_CONFIG.get("PROXY_HTTP", "http://127.0.0.1:7890"),
                'https': API_CONFIG.get("PROXY_HTTPS", "http://127.0.0.1:7890")
            }
            logging.info(f"[API] 使用代理: {self.session.proxies}")
        
        # SSL验证设置
        self.session.verify = API_CONFIG.get("VERIFY_SSL", True)
        if not self.session.verify:
            logging.warning("[API] SSL验证已禁用")
        
        # API调用统计
        self.api_calls = 0
        self.api_errors = 0
    
    def _generate_signature(self, params):
        """生成HMAC SHA256签名"""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        return int(time.time() * 1000)
    
    def _make_request(self, method, endpoint, params=None, signed=False, retries=3):
        """发送API请求 (带重试机制和详细错误处理)"""
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = self._get_timestamp()
            params['signature'] = self._generate_signature(params)
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries):
            try:
                self.api_calls += 1
                
                # 记录请求详情
                logging.debug(f"[API] 请求 {method} {url}")
                logging.debug(f"[API] 参数: {params}")
                
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=10)
                elif method == 'POST':
                    response = self.session.post(url, data=params, timeout=10)
                elif method == 'DELETE':
                    response = self.session.delete(url, params=params, timeout=10)
                
                # 详细的响应日志
                logging.debug(f"[API] 响应状态: {response.status_code}")
                logging.debug(f"[API] 响应头: {dict(response.headers)}")
                
                if response.status_code == 400:
                    # 解析400错误的详细信息
                    try:
                        error_data = response.json()
                        error_code = error_data.get('code', 'UNKNOWN')
                        error_msg = error_data.get('msg', 'Unknown error')
                        logging.error(f"[API] 400错误详情 - 代码: {error_code}, 消息: {error_msg}")
                        logging.error(f"[API] 请求参数: {params}")
                    except:
                        logging.error(f"[API] 400错误，无法解析响应: {response.text}")
                    return None
                
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.RequestException as e:
                self.api_errors += 1
                logging.error(f"[API] 请求失败 (尝试 {attempt + 1}/{retries}): {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logging.error(f"[API] 响应状态码: {e.response.status_code}")
                    logging.error(f"[API] 响应内容: {e.response.text}")
                
                if attempt < retries - 1:
                    time.sleep(1)  # 重试前等待
                else:
                    return None
    
    def get_server_time(self):
        """获取服务器时间"""
        return self._make_request('GET', '/fapi/v1/time')
    
    def get_exchange_info(self):
        """获取交易规则和交易对信息"""
        return self._make_request('GET', '/fapi/v1/exchangeInfo')
    
    def get_account_info(self):
        """获取账户信息"""
        return self._make_request('GET', '/fapi/v2/account', signed=True)
    
    def get_balance(self):
        """获取账户余额V2"""
        return self._make_request('GET', '/fapi/v2/balance', signed=True)
    
    def place_order(self, symbol, side, order_type, quantity, price=None, 
                   time_in_force='GTC', reduce_only=False, position_side='BOTH'):
        """下单 - 修复精度和参数问题"""
        try:
            # 根据BTCUSDT交易规则调整参数
            if symbol == 'BTCUSDT':
                # 确保数量精度为3位小数
                quantity = round(float(quantity), 3)
                # 确保最小数量为0.001
                if quantity < 0.001:
                    quantity = 0.001
                
                # 只有限价单且提供了价格时才处理价格
                if order_type == 'LIMIT' and price is not None:
                    # 确保价格精度为1位小数，且是tickSize的倍数
                    adjusted_price = round(float(price), 1)
                    # 确保价格是0.1的倍数 - 使用整数除法避免浮点数精度问题
                    adjusted_price = (adjusted_price // 0.1) * 0.1
                    adjusted_price = round(adjusted_price, 1)  # 再次确保精度
                    
                    # 检查最小名义价值 (5 USDT)
                    notional_value = quantity * adjusted_price
                    if notional_value < 5.0:
                        # 调整数量以满足最小名义价值
                        quantity = max(0.001, round(5.1 / adjusted_price, 3))
                        logging.info(f"[下单] 调整数量以满足最小名义价值: {quantity}")
                    
                    price = adjusted_price
            
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': str(quantity),
                'positionSide': position_side
            }
            
            # 只有限价单且提供了价格时才添加价格参数
            if order_type == 'LIMIT' and price is not None:
                params['price'] = str(price)
                params['timeInForce'] = time_in_force
            
            if reduce_only:
                params['reduceOnly'] = 'true'
            
            # 记录详细的下单参数
            logging.debug(f"[下单] 参数: {params}")
            
            result = self._make_request('POST', '/fapi/v1/order', params, signed=True)
            
            if result is None:
                logging.error(f"[下单] API返回None，可能是网络错误或API限制")
            
            return result
            
        except Exception as e:
            logging.error(f"[下单] 构造订单参数失败: {e}")
            return None
    
    def place_market_order(self, symbol, side, quantity, reduce_only=False):
        """下市价单"""
        return self.place_order(symbol, side, 'MARKET', quantity, reduce_only=reduce_only)
    
    def place_limit_order(self, symbol, side, quantity, price, time_in_force='IOC', reduce_only=False):
        """下限价单"""
        return self.place_order(symbol, side, 'LIMIT', quantity, price, time_in_force, reduce_only)
    
    def cancel_all_orders(self, symbol):
        """撤销所有订单"""
        params = {'symbol': symbol}
        return self._make_request('DELETE', '/fapi/v1/allOpenOrders', params, signed=True)
    
    def get_position_risk(self, symbol=None):
        """获取持仓风险"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request('GET', '/fapi/v2/positionRisk', params, signed=True)
    
    def get_order_status(self, symbol, order_id):
        """查询订单状态"""
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('GET', '/fapi/v1/order', params, signed=True)
    
    def cancel_order(self, symbol, order_id):
        """取消订单"""
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('DELETE', '/fapi/v1/order', params, signed=True)

class EnhancedSpreadMonitor:
    """增强版价差监控器"""
    
    def __init__(self, symbols, spread_threshold):
        self.symbols = [symbol.lower() for symbol in symbols]
        self.spread_threshold = spread_threshold
        self.spreads = {}
        self.ws = None
        self.running = False
        self.callbacks = []
        self.reconnect_count = 0
        self.last_message_time = time.time()
        
        # WebSocket代理配置 - 修复代理配置
        self.ws_options = {}
        if WEBSOCKET_CONFIG.get("USE_PROXY", False):
            proxy_host = WEBSOCKET_CONFIG.get("PROXY_HOST", "127.0.0.1")
            proxy_port = WEBSOCKET_CONFIG.get("PROXY_PORT", 7890)
            proxy_type = WEBSOCKET_CONFIG.get("PROXY_TYPE", "http")
            
            logging.info(f"[WebSocket] 使用代理: {proxy_type}://{proxy_host}:{proxy_port}")
            
            # 修复WebSocket代理配置
            if proxy_type.lower() == "http":
                self.ws_options["http_proxy_host"] = proxy_host
                self.ws_options["http_proxy_port"] = proxy_port
                self.ws_options["proxy_type"] = "http"
            elif proxy_type.lower() == "socks5":
                self.ws_options["http_proxy_host"] = proxy_host
                self.ws_options["http_proxy_port"] = proxy_port
                self.ws_options["proxy_type"] = "socks5"
            elif proxy_type.lower() == "socks4":
                self.ws_options["http_proxy_host"] = proxy_host
                self.ws_options["http_proxy_port"] = proxy_port
                self.ws_options["proxy_type"] = "socks4"
    
    def add_callback(self, callback):
        """添加回调函数"""
        self.callbacks.append(callback)
    
    def on_message(self, ws, message):
        """处理WebSocket消息"""
        try:
            self.last_message_time = time.time()
            data = json.loads(message)
            
            # 处理组合流数据
            if 'stream' in data:
                stream = data['stream']
                ticker_data = data['data']
                symbol = stream.split('@')[0].upper()
            else:
                # 处理单一流数据
                ticker_data = data
                symbol = ticker_data['s']
            
            bid = float(ticker_data['b'])
            ask = float(ticker_data['a'])
            spread = (ask - bid) / bid
            
            # 更新价差数据
            self.spreads[symbol] = {
                'bid': bid,
                'ask': ask,
                'spread': spread,
                'timestamp': time.time(),
                'bid_qty': float(ticker_data['B']),
                'ask_qty': float(ticker_data['A'])
            }
            
            # 检查是否满足交易条件
            if spread < self.spread_threshold:
                logging.debug(f"[价差监控] {symbol} 价差合适: {spread:.4%} (买:{bid}, 卖:{ask})")
                
                # 调用回调函数
                for callback in self.callbacks:
                    try:
                        callback(symbol, self.spreads[symbol])
                    except Exception as e:
                        logging.error(f"[价差监控] 回调函数执行错误: {e}")
            
        except Exception as e:
            logging.error(f"[WebSocket] 处理消息错误: {e}")
    
    def on_error(self, ws, error):
        logging.error(f"[WebSocket] 连接错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        logging.warning(f"[WebSocket] 连接关闭: {close_status_code} - {close_msg}")
        if self.running:
            self.reconnect_count += 1
            logging.info(f"[WebSocket] 尝试第 {self.reconnect_count} 次重新连接...")
            time.sleep(WEBSOCKET_CONFIG["RECONNECT_DELAY"])
            self.start_monitoring()
    
    def on_open(self, ws):
        logging.info("[WebSocket] 连接已建立")
        self.reconnect_count = 0
    
    def start_monitoring(self):
        """开始监控"""
        self.running = True
        
        # 使用正确的AsterDex WebSocket端点
        if len(self.symbols) == 1:
            # 单个交易对使用直接连接
            ws_url = f"{WEBSOCKET_CONFIG['WS_URL']}/{self.symbols[0]}@bookTicker"
        else:
            # 多个交易对使用流式连接
            streams = [f"{symbol}@bookTicker" for symbol in self.symbols]
            ws_url = f"{WEBSOCKET_CONFIG['STREAM_URL']}?streams={'/'.join(streams)}"
        
        logging.info(f"[WebSocket] 连接地址: {ws_url}")
        
        # 设置WebSocket选项
        ws_options = {
            'ping_interval': WEBSOCKET_CONFIG["PING_INTERVAL"],
            'ping_timeout': 10,
            'sslopt': {"cert_reqs": ssl.CERT_NONE} if not WEBSOCKET_CONFIG.get("VERIFY_SSL", True) else {}
        }
        
        # 添加代理配置
        if WEBSOCKET_CONFIG.get("USE_PROXY", False):
            proxy_host = WEBSOCKET_CONFIG.get("PROXY_HOST", "127.0.0.1")
            proxy_port = WEBSOCKET_CONFIG.get("PROXY_PORT", 7890)
            proxy_type = WEBSOCKET_CONFIG.get("PROXY_TYPE", "http")
            
            logging.info(f"[WebSocket] 使用代理: {proxy_type}://{proxy_host}:{proxy_port}")
            
            if proxy_type.lower() == "http":
                ws_options["http_proxy_host"] = proxy_host
                ws_options["http_proxy_port"] = proxy_port
            elif proxy_type.lower() == "socks5":
                ws_options["proxy_type"] = "socks5"
                ws_options["http_proxy_host"] = proxy_host
                ws_options["http_proxy_port"] = proxy_port
            elif proxy_type.lower() == "socks4":
                ws_options["proxy_type"] = "socks4"
                ws_options["http_proxy_host"] = proxy_host
                ws_options["http_proxy_port"] = proxy_port
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # 启动WebSocket连接（使用代理配置）
        try:
            self.ws.run_forever(**ws_options)
        except Exception as e:
            logging.error(f"[WebSocket] 启动失败: {e}")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.ws:
            self.ws.close()
    
    def is_healthy(self):
        """检查连接健康状态"""
        return (time.time() - self.last_message_time) < 60  # 60秒内有消息则认为健康

class EnhancedVolumeTrader:
    """增强版交易量刷单器"""
    
    def __init__(self):
        # 初始化日志
        self.logger = EnhancedLogger.setup_logger()
        
        # 初始化组件
        self.api = EnhancedAsterDexAPI()
        self.stats = TradingStatistics()
        self.risk_manager = RiskManager(self.stats)
        
        # 新增：趋势分析组件
        self.trend_analyzer = TrendAnalyzer(
            window_size=30,
            short_ma=5,
            long_ma=20
        )
        self.trend_decision = TrendBasedTradeDecision(self.trend_analyzer)
        
        # 交易配置
        self.symbols = TRADING_CONFIG["SYMBOLS"]
        self.trade_quantity = TRADING_CONFIG.get("TRADE_QUANTITY", 0.001)
        self.spread_threshold = TRADING_CONFIG.get("MIN_SPREAD_THRESHOLD", 0.0001)
        self.min_trade_interval = TRADING_CONFIG.get("TRADE_INTERVAL", 1.0)
        
        # 趋势交易配置
        self.trend_trading_enabled = STRATEGY_CONFIG.get("TREND_TRADING", {}).get("ENABLED", True)
        self.trend_confidence_threshold = STRATEGY_CONFIG.get("TREND_TRADING", {}).get("MIN_CONFIDENCE", 0.2)
        self.directional_trade_ratio = STRATEGY_CONFIG.get("TREND_TRADING", {}).get("DIRECTIONAL_RATIO", 0.7)
        
        # 交易状态
        self.trading_enabled = True
        self.positions = {}
        self.last_trade_time = {}
        self.current_trend_direction = "NEUTRAL"
        self.trend_change_time = time.time()
        
        # 初始化价差监控器
        self.spread_monitor = EnhancedSpreadMonitor(self.symbols, self.spread_threshold)
        self.spread_monitor.add_callback(self.on_spread_opportunity)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logging.info(f"[系统] 收到信号 {signum}，准备停止交易...")
        self.trading_enabled = False
    
    def validate_config(self):
        """验证配置"""
        if API_CONFIG["API_KEY"] == "your_api_key_here":
            logging.error("[配置] 请在config.py中设置正确的API_KEY")
            return False
        
        if API_CONFIG["SECRET_KEY"] == "your_secret_key_here":
            logging.error("[配置] 请在config.py中设置正确的SECRET_KEY")
            return False
        
        # 测试API连接
        server_time = self.api.get_server_time()
        if not server_time:
            logging.error("[配置] 无法连接到API服务器")
            return False
        
        logging.info("[配置] 配置验证通过")
        return True
    
    def on_spread_opportunity(self, symbol, spread_data):
        """价差机会回调 - 增加趋势判断"""
        if not self.trading_enabled:
            return
        
        # 风险检查
        if not self.risk_manager.check_risk_limits():
            logging.error("[风险管理] 触发风险限制，停止交易")
            self.trading_enabled = False
            return
        
        # 检查仓位回撤 - 新增
        bid = spread_data['bid']
        ask = spread_data['ask']
        current_price = (bid + ask) / 2
        
        # 获取当前持仓并检查回撤
        try:
            position_info = self.api.get_position_risk(symbol)
            if position_info:
                for position in position_info:
                    if position['symbol'] == symbol:
                        position_amt = float(position['positionAmt'])
                        if abs(position_amt) > 0.001:
                            # 检查仓位回撤
                            if not self.risk_manager.update_position_value(symbol, current_price, position_amt):
                                logging.error(f"[风险管理] {symbol} 仓位回撤超限，执行强制平仓")
                                if self.risk_manager.force_close_position(symbol, self.api):
                                    logging.info(f"[风险管理] {symbol} 强制平仓完成")
                                else:
                                    logging.error(f"[风险管理] {symbol} 强制平仓失败，停止交易")
                                    self.trading_enabled = False
                                return
        except Exception as e:
            logging.error(f"[风险管理] 检查仓位回撤失败: {e}")
        
        # 检查交易间隔
        current_time = time.time()
        if symbol in self.last_trade_time:
            if current_time - self.last_trade_time[symbol] < self.min_trade_interval:
                return
        
        # 检查日交易次数限制
        if self.stats.daily_trades >= TRADING_CONFIG["MAX_DAILY_TRADES"]:
            logging.warning("[交易] 已达到日交易次数限制")
            return
        
        # 更新趋势数据
        self.update_trend_data(symbol, spread_data)
        
        # 执行趋势感知交易
        self.execute_trend_aware_trade(symbol, spread_data)
    
    def update_trend_data(self, symbol, spread_data):
        """更新趋势分析数据"""
        bid = spread_data['bid']
        ask = spread_data['ask']
        mid_price = (bid + ask) / 2
        volume = spread_data.get('bid_qty', 0) + spread_data.get('ask_qty', 0)
        
        # 添加价格数据到趋势分析器
        self.trend_analyzer.add_price_data(mid_price, volume)
        
        # 检查趋势变化
        new_direction = self.trend_analyzer.get_position_direction()
        if new_direction != self.current_trend_direction:
            logging.info(f"[趋势变化] {symbol} 趋势从 {self.current_trend_direction} 变为 {new_direction}")
            self.current_trend_direction = new_direction
            self.trend_change_time = time.time()
    
    def execute_trend_aware_trade(self, symbol, spread_data):
        """执行趋势感知交易"""
        try:
            bid = spread_data['bid']
            ask = spread_data['ask']
            spread = spread_data['spread']
            
            # 获取趋势决策
            trade_direction, reason = self.trend_decision.get_optimal_trade_direction(
                (bid + ask) / 2, spread_data
            )
            
            logging.info(f"[趋势交易] {symbol} 开始执行交易, 价差: {spread:.4%}")
            logging.info(f"[趋势交易] 趋势方向: {trade_direction}, 原因: {reason}")
            
            # 根据趋势方向选择交易策略
            if self.trend_trading_enabled and trade_direction in ["LONG", "SHORT"]:
                success, is_maker, estimated_fee = self.execute_directional_trade(
                    symbol, trade_direction, bid, ask, spread_data
                )
            else:
                # 传统双向刷单
                success, is_maker, estimated_fee = self.execute_traditional_volume_trade(
                    symbol, bid, ask, spread_data
                )
            
            # 更新统计
            self.stats.add_trade(success, self.trade_quantity, 0, is_maker, estimated_fee)
            
            if success:
                self.last_trade_time[symbol] = time.time()
                logging.info(f"[交易] {symbol} 交易完成, 总交易次数: {self.stats.total_trades}")
            else:
                logging.warning(f"[交易] {symbol} 交易失败")
            
            # 定期报告统计
            if self.stats.total_trades % 50 == 0:  # 每50次交易报告一次
                self.stats.print_stats()
                self.print_trend_analysis()
                # 新增：打印仓位回撤报告
                risk_report = self.risk_manager.get_position_risk_report()
                logging.info(risk_report)
            
        except Exception as e:
            logging.error(f"[交易] 执行趋势感知交易失败: {e}")
            self.stats.add_trade(False, 0)
    
    def execute_directional_trade(self, symbol, direction, bid, ask, spread_data):
        """执行方向性交易"""
        try:
            if direction == "LONG":
                return self.execute_long_strategy(symbol, bid, ask, spread_data)
            elif direction == "SHORT":
                return self.execute_short_strategy(symbol, bid, ask, spread_data)
            else:
                return self.execute_traditional_volume_trade(symbol, bid, ask, spread_data)
                
        except Exception as e:
            logging.error(f"[方向交易] 执行失败: {e}")
            return False, False, 0
    
    def execute_long_strategy(self, symbol, bid, ask, spread_data):
        """执行做多策略 - 优化限价单成为Maker"""
        try:
            # 获取配置参数
            buy_offset = STRATEGY_CONFIG["LIMIT_ORDER"]["BUY_PRICE_OFFSET"]
            sell_offset = STRATEGY_CONFIG["LIMIT_ORDER"]["SELL_PRICE_OFFSET"]
            time_in_force = STRATEGY_CONFIG["LIMIT_ORDER"]["TIME_IN_FORCE"]
            max_wait_time = STRATEGY_CONFIG["LIMIT_ORDER"].get("MAX_WAIT_TIME", 5)
            
            # 做多策略：更积极的买入，保守的卖出
            buy_price = round(bid * (1 + buy_offset * 0.3), 8)  # 更接近市价买入
            sell_price = round(ask * (1 + sell_offset * 2), 8)  # 更高价格卖出
            
            logging.debug(f"[做多策略] {symbol} 买价: {buy_price}, 卖价: {sell_price}")
            
            # 1. 限价买入订单 (更容易成交)
            buy_order = self.api.place_limit_order(
                symbol, 'BUY', self.trade_quantity, buy_price, time_in_force
            )
            
            if not buy_order or 'orderId' not in buy_order:
                logging.error(f"[做多] 买入订单下单失败: {buy_order}")
                return False, False, 0
            
            buy_order_id = buy_order['orderId']
            logging.debug(f"[做多] 买入订单已下单: {buy_order_id}")
            
            # 等待买入订单成交
            buy_filled = self.wait_for_order_fill(symbol, buy_order_id, max_wait_time)
            
            if not buy_filled:
                try:
                    self.api.cancel_order(symbol, buy_order_id)
                    logging.debug(f"[做多] 已取消买入订单: {buy_order_id}")
                except:
                    pass
                return False, False, 0
            
            logging.debug(f"[做多] 买入订单已成交: {buy_order_id}")
            
            # 2. 限价卖出订单 (设置更高价格，等待趋势获利)
            sell_order = self.api.place_limit_order(
                symbol, 'SELL', self.trade_quantity, sell_price, 'GTC', reduce_only=True
            )
            
            if not sell_order or 'orderId' not in sell_order:
                logging.error(f"[做多] 卖出订单下单失败: {sell_order}")
                self.positions[symbol] = self.positions.get(symbol, 0) + self.trade_quantity
                return False, False, 0
            
            sell_order_id = sell_order['orderId']
            logging.debug(f"[做多] 卖出订单已下单: {sell_order_id}")
            
            # 等待卖出订单成交 (可以等待更长时间)
            sell_filled = self.wait_for_order_fill(symbol, sell_order_id, max_wait_time * 2)
            
            if not sell_filled:
                # 如果高价卖出未成交，使用市价单快速平仓
                try:
                    self.api.cancel_order(symbol, sell_order_id)
                    market_sell = self.api.place_market_order(symbol, 'SELL', self.trade_quantity, reduce_only=True)
                    if market_sell:
                        logging.info(f"[做多] 使用市价单平仓: {symbol}")
                        estimated_fee = self.trade_quantity * buy_price * 0.0003  # 混合费率
                        return True, False, estimated_fee
                except:
                    pass
                self.positions[symbol] = self.positions.get(symbol, 0) + self.trade_quantity
                return False, False, 0
            
            logging.info(f"[做多策略] {symbol} 完成，享受趋势获利")
            
            # 估算手续费 - 做多策略通常能获得更好的Maker比例
            estimated_fee = self.trade_quantity * (buy_price + sell_price) * 0.0002 * 0.8  # 80% Maker概率
            
            return True, True, estimated_fee
            
        except Exception as e:
            logging.error(f"[做多策略] 失败: {e}")
            return False, False, 0
    
    def execute_short_strategy(self, symbol, bid, ask, spread_data):
        """执行做空策略 - 优化限价单成为Maker"""
        try:
            # 获取配置参数
            buy_offset = STRATEGY_CONFIG["LIMIT_ORDER"]["BUY_PRICE_OFFSET"]
            sell_offset = STRATEGY_CONFIG["LIMIT_ORDER"]["SELL_PRICE_OFFSET"]
            time_in_force = STRATEGY_CONFIG["LIMIT_ORDER"]["TIME_IN_FORCE"]
            max_wait_time = STRATEGY_CONFIG["LIMIT_ORDER"].get("MAX_WAIT_TIME", 5)
            
            # 做空策略：保守的买入，更积极的卖出
            buy_price = round(bid * (1 - buy_offset * 2), 8)  # 更低价格买入
            sell_price = round(ask * (1 - sell_offset * 0.3), 8)  # 更接近市价卖出
            
            logging.debug(f"[做空策略] {symbol} 买价: {buy_price}, 卖价: {sell_price}")
            
            # 1. 限价卖出订单 (开空仓)
            sell_order = self.api.place_limit_order(
                symbol, 'SELL', self.trade_quantity, sell_price, time_in_force
            )
            
            if not sell_order or 'orderId' not in sell_order:
                logging.error(f"[做空] 卖出订单下单失败: {sell_order}")
                return False, False, 0
            
            sell_order_id = sell_order['orderId']
            logging.debug(f"[做空] 卖出订单已下单: {sell_order_id}")
            
            # 等待卖出订单成交
            sell_filled = self.wait_for_order_fill(symbol, sell_order_id, max_wait_time)
            
            if not sell_filled:
                try:
                    self.api.cancel_order(symbol, sell_order_id)
                    logging.debug(f"[做空] 已取消卖出订单: {sell_order_id}")
                except:
                    pass
                return False, False, 0
            
            logging.debug(f"[做空] 卖出订单已成交: {sell_order_id}")
            
            # 2. 限价买入订单 (平空仓，设置更低价格等待下跌获利)
            buy_order = self.api.place_limit_order(
                symbol, 'BUY', self.trade_quantity, buy_price, 'GTC', reduce_only=True
            )
            
            if not buy_order or 'orderId' not in buy_order:
                logging.error(f"[做空] 买入订单下单失败: {buy_order}")
                self.positions[symbol] = self.positions.get(symbol, 0) - self.trade_quantity
                return False, False, 0
            
            buy_order_id = buy_order['orderId']
            logging.debug(f"[做空] 买入订单已下单: {buy_order_id}")
            
            # 等待买入订单成交
            buy_filled = self.wait_for_order_fill(symbol, buy_order_id, max_wait_time * 2)
            
            if not buy_filled:
                # 如果低价买入未成交，使用市价单快速平仓
                try:
                    self.api.cancel_order(symbol, buy_order_id)
                    market_buy = self.api.place_market_order(symbol, 'BUY', self.trade_quantity, reduce_only=True)
                    if market_buy:
                        logging.info(f"[做空] 使用市价单平仓: {symbol}")
                        estimated_fee = self.trade_quantity * sell_price * 0.0003  # 混合费率
                        return True, False, estimated_fee
                except:
                    pass
                self.positions[symbol] = self.positions.get(symbol, 0) - self.trade_quantity
                return False, False, 0
            
            logging.info(f"[做空策略] {symbol} 完成，享受趋势获利")
            
            # 估算手续费
            estimated_fee = self.trade_quantity * (buy_price + sell_price) * 0.0002 * 0.8  # 80% Maker概率
            
            return True, True, estimated_fee
            
        except Exception as e:
            logging.error(f"[做空策略] 失败: {e}")
            return False, False, 0
    
    def execute_traditional_volume_trade(self, symbol, bid, ask, spread_data):
        """执行传统双向刷单交易"""
        # 使用原有的优化限价单策略
        return self.use_optimized_limit_strategy(symbol, bid, ask, spread_data)
    
    def print_trend_analysis(self):
        """打印趋势分析报告"""
        try:
            signal, strength = self.trend_analyzer.get_trend_signal()
            direction = self.trend_analyzer.get_position_direction()
            
            logging.info("=" * 60)
            logging.info("[趋势分析] 市场趋势报告")
            logging.info("=" * 60)
            logging.info(f"当前趋势信号: {signal}")
            logging.info(f"趋势强度: {strength:.3f}")
            logging.info(f"建议方向: {direction}")
            logging.info(f"趋势持续时间: {(time.time() - self.trend_change_time):.0f} 秒")
            
            # 显示详细分析
            if len(self.trend_analyzer.price_history) >= 5:
                current_price = self.trend_analyzer.price_history[-1]
                momentum = self.trend_analyzer.calculate_price_momentum()
                rsi = self.trend_analyzer.calculate_rsi()
                volatility = self.trend_analyzer.calculate_volatility()
                
                logging.info(f"当前价格: {current_price:.2f}")
                logging.info(f"价格动量: {momentum:.4f} ({momentum*100:.2f}%)")
                logging.info(f"RSI指标: {rsi:.1f}")
                logging.info(f"波动率: {volatility:.4f} ({volatility*100:.2f}%)")
            
            logging.info("=" * 60)
            
        except Exception as e:
            logging.error(f"[趋势分析] 打印报告失败: {e}")
    
    def use_optimized_limit_strategy(self, symbol, bid, ask, spread_data):
        """优化的限价单策略 - 减少手续费"""
        try:
            # 获取配置参数
            buy_offset = STRATEGY_CONFIG["LIMIT_ORDER"]["BUY_PRICE_OFFSET"]
            sell_offset = STRATEGY_CONFIG["LIMIT_ORDER"]["SELL_PRICE_OFFSET"]
            time_in_force = STRATEGY_CONFIG["LIMIT_ORDER"]["TIME_IN_FORCE"]
            max_wait_time = STRATEGY_CONFIG["LIMIT_ORDER"].get("MAX_WAIT_TIME", 5)  # 最大等待时间
            
            # 计算更优的限价 - 尽量成为Maker获得返佣
            bid_qty = spread_data.get('bid_qty', 0)
            ask_qty = spread_data.get('ask_qty', 0)
            
            # 动态调整价格偏移，确保成为Maker
            if bid_qty > ask_qty:
                # 买方深度更大，优先做买方Maker
                buy_price = round(bid * (1 + buy_offset * 0.5), 8)  # 更接近当前买价
                sell_price = round(ask * (1 - sell_offset), 8)
            else:
                # 卖方深度更大，优先做卖方Maker
                buy_price = round(bid * (1 + buy_offset), 8)
                sell_price = round(ask * (1 - sell_offset * 0.5), 8)  # 更接近当前卖价
            
            logging.debug(f"[限价策略] {symbol} 买价: {buy_price}, 卖价: {sell_price}")
            
            # 1. 限价买入订单
            buy_order = self.api.place_limit_order(
                symbol, 'BUY', self.trade_quantity, buy_price, time_in_force
            )
            
            if not buy_order or 'orderId' not in buy_order:
                logging.error(f"[交易] 买入订单下单失败: {buy_order}")
                return False, False, 0
            
            buy_order_id = buy_order['orderId']
            logging.debug(f"[交易] 买入订单已下单: {buy_order_id}")
            
            # 等待买入订单成交
            buy_filled = self.wait_for_order_fill(symbol, buy_order_id, max_wait_time)
            
            if not buy_filled:
                # 取消未成交的买入订单
                try:
                    cancel_result = self.api.cancel_order(symbol, buy_order_id)
                    logging.debug(f"[交易] 已取消买入订单: {buy_order_id}")
                except:
                    pass
                return False, False, 0
            
            logging.debug(f"[交易] 买入订单已成交: {buy_order_id}")
            
            # 2. 限价卖出订单
            sell_order = self.api.place_limit_order(
                symbol, 'SELL', self.trade_quantity, sell_price, time_in_force, reduce_only=True
            )
            
            if not sell_order or 'orderId' not in sell_order:
                logging.error(f"[交易] 卖出订单下单失败: {sell_order}")
                # 记录持仓，稍后清理
                self.positions[symbol] = self.positions.get(symbol, 0) + self.trade_quantity
                return False, False, 0
            
            sell_order_id = sell_order['orderId']
            logging.debug(f"[交易] 卖出订单已下单: {sell_order_id}")
            
            # 等待卖出订单成交
            sell_filled = self.wait_for_order_fill(symbol, sell_order_id, max_wait_time)
            
            if not sell_filled:
                # 取消未成交的卖出订单
                try:
                    cancel_result = self.api.cancel_order(symbol, sell_order_id)
                    logging.debug(f"[交易] 已取消卖出订单: {sell_order_id}")
                except:
                    pass
                # 记录持仓，稍后清理
                self.positions[symbol] = self.positions.get(symbol, 0) + self.trade_quantity
                return False, False, 0
            
            logging.debug(f"[交易] 卖出订单已成交: {sell_order_id}")
            logging.info(f"[费用优化] {symbol} 限价单策略完成，享受Maker费率优惠")
            
            # 估算手续费 - Maker费率通常更低
            estimated_maker_fee_rate = 0.0002  # 0.02% (示例费率，实际应从API获取)
            estimated_fee = self.trade_quantity * (buy_price + sell_price) * estimated_maker_fee_rate
            
            return True, True, estimated_fee
            
        except Exception as e:
            logging.error(f"[交易] 优化限价单策略失败: {e}")
            return False, False, 0
    
    def wait_for_order_fill(self, symbol, order_id, max_wait_time):
        """等待订单成交"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                order_status = self.api.get_order_status(symbol, order_id)
                if order_status:
                    status = order_status.get('status', '')
                    if status in ['FILLED']:
                        return True
                    elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                        return False
                
                time.sleep(0.1)  # 100ms检查间隔
                
            except Exception as e:
                logging.error(f"[交易] 检查订单状态失败: {e}")
                break
        
        return False
    
    def cleanup_positions(self):
        """清理剩余持仓"""
        for symbol, position in list(self.positions.items()):
            if abs(position) > 0.0001:
                try:
                    side = 'SELL' if position > 0 else 'BUY'
                    quantity = abs(position)
                    
                    order = self.api.place_market_order(symbol, side, quantity, reduce_only=True)
                    if order and 'orderId' in order:
                        logging.info(f"[持仓] 清理持仓成功: {symbol} {side} {quantity}")
                        self.positions[symbol] = 0
                    
                except Exception as e:
                    logging.error(f"[持仓] 清理持仓失败 {symbol}: {e}")
    
    def get_account_status(self):
        """获取账户状态"""
        try:
            # 使用新的余额查询API
            balance_info = self.api.get_balance()
            if balance_info and isinstance(balance_info, list):
                total_balance = 0
                usdt_balance = 0
                
                for asset in balance_info:
                    if asset.get('asset') == 'USDT':
                        usdt_balance = float(asset.get('balance', 0))
                        available_balance = float(asset.get('availableBalance', 0))
                        cross_wallet_balance = float(asset.get('crossWalletBalance', 0))
                        cross_unpnl = float(asset.get('crossUnPnl', 0))
                        
                        logging.info(f"[账户] USDT余额: {usdt_balance:.4f}")
                        logging.info(f"[账户] 可用余额: {available_balance:.4f}")
                        logging.info(f"[账户] 全仓余额: {cross_wallet_balance:.4f}")
                        logging.info(f"[账户] 未实现盈亏: {cross_unpnl:.4f}")
                        break
                
                logging.info(f"[API] 调用次数: {self.api.api_calls}, 错误次数: {self.api.api_errors}")
                return balance_info
            else:
                # 如果余额API失败，尝试账户信息API
                account_info = self.api.get_account_info()
                if account_info:
                    balance = float(account_info.get('totalWalletBalance', 0))
                    pnl = float(account_info.get('totalUnrealizedProfit', 0))
                    
                    logging.info(f"[账户] 总余额: {balance:.4f} USDT, 未实现盈亏: {pnl:.4f} USDT")
                    logging.info(f"[API] 调用次数: {self.api.api_calls}, 错误次数: {self.api.api_errors}")
                    return account_info
                
        except Exception as e:
            logging.error(f"[账户] 获取账户状态失败: {e}")
        return None
    
    def start_trading(self):
        """开始交易"""
        logging.info("[系统] 启动增强版交易量刷单系统")
        
        # 验证配置
        if not self.validate_config():
            return
        
        # 检查账户状态
        account_status = self.get_account_status()
        if not account_status:
            logging.error("[系统] 无法获取账户状态，停止启动")
            return
        
        # 启动价差监控
        monitor_thread = threading.Thread(target=self.spread_monitor.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 主循环
        try:
            while self.trading_enabled and not self.risk_manager.should_stop_trading():
                # 定期清理持仓
                if self.stats.total_trades % 10 == 0:  # 每10次交易清理一次
                    self.cleanup_positions()
                
                # 定期检查账户状态
                if self.stats.total_trades % 50 == 0:  # 每50次交易检查一次
                    self.get_account_status()
                
                # 检查WebSocket健康状态
                if not self.spread_monitor.is_healthy():
                    logging.warning("[WebSocket] 连接不健康，尝试重连...")
                    self.spread_monitor.stop_monitoring()
                    time.sleep(5)
                    monitor_thread = threading.Thread(target=self.spread_monitor.start_monitoring)
                    monitor_thread.daemon = True
                    monitor_thread.start()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info("[系统] 收到停止信号")
        finally:
            self.stop_trading()
    
    def stop_trading(self):
        """停止交易"""
        logging.info("[系统] 停止交易系统")
        self.trading_enabled = False
        self.spread_monitor.stop_monitoring()
        
        # 清理剩余持仓
        self.cleanup_positions()
        
        # 撤销所有挂单
        for symbol in self.symbols:
            try:
                self.api.cancel_all_orders(symbol)
                logging.info(f"[系统] 已撤销 {symbol} 所有挂单")
            except Exception as e:
                logging.error(f"[系统] 撤销 {symbol} 挂单失败: {e}")
        
        # 最终统计报告
        self.stats.print_stats()
        logging.info("[系统] 交易系统已停止")

def main():
    """主函数"""
    trader = EnhancedVolumeTrader()
    trader.start_trading()

if __name__ == "__main__":
    main()