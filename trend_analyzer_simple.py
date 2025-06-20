#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版趋势分析模块
不依赖numpy，提供基本的市场趋势分析功能
"""

import time
import math
from collections import deque
from typing import Tuple, List, Optional

class TrendAnalyzer:
    """简化版趋势分析器"""
    
    def __init__(self, window_size: int = 30, short_ma: int = 5, long_ma: int = 20):
        """
        初始化趋势分析器
        
        Args:
            window_size: 价格历史窗口大小
            short_ma: 短期移动平均周期
            long_ma: 长期移动平均周期
        """
        self.window_size = window_size
        self.short_ma = short_ma
        self.long_ma = long_ma
        
        # 价格和成交量历史
        self.price_history = deque(maxlen=window_size)
        self.volume_history = deque(maxlen=window_size)
        self.timestamp_history = deque(maxlen=window_size)
        
        # 技术指标缓存
        self._short_ma_cache = None
        self._long_ma_cache = None
        self._rsi_cache = None
        self._last_update = 0
        
    def add_price_data(self, price: float, volume: float = 1.0):
        """添加价格数据"""
        current_time = time.time()
        
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(current_time)
        
        # 清除缓存
        self._clear_cache()
        self._last_update = current_time
    
    def _clear_cache(self):
        """清除技术指标缓存"""
        self._short_ma_cache = None
        self._long_ma_cache = None
        self._rsi_cache = None
    
    def calculate_moving_average(self, period: int) -> Optional[float]:
        """计算移动平均"""
        if len(self.price_history) < period:
            return None
        
        recent_prices = list(self.price_history)[-period:]
        return sum(recent_prices) / len(recent_prices)
    
    def get_short_ma(self) -> Optional[float]:
        """获取短期移动平均"""
        if self._short_ma_cache is None:
            self._short_ma_cache = self.calculate_moving_average(self.short_ma)
        return self._short_ma_cache
    
    def get_long_ma(self) -> Optional[float]:
        """获取长期移动平均"""
        if self._long_ma_cache is None:
            self._long_ma_cache = self.calculate_moving_average(self.long_ma)
        return self._long_ma_cache
    
    def calculate_price_momentum(self) -> float:
        """计算价格动量"""
        if len(self.price_history) < 2:
            return 0.0
        
        current_price = self.price_history[-1]
        previous_price = self.price_history[-2]
        
        return (current_price - previous_price) / previous_price
    
    def calculate_volatility(self) -> float:
        """计算价格波动率（不使用numpy）"""
        if len(self.price_history) < 5:
            return 0.0
        
        prices = list(self.price_history)[-10:]  # 使用最近10个价格
        returns = []
        
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # 手动计算标准差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)
    
    def calculate_rsi(self, period: int = 14) -> float:
        """计算RSI指标"""
        if len(self.price_history) < period + 1:
            return 50.0  # 中性值
        
        prices = list(self.price_history)[-(period + 1):]
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)
        
        if not gains or not losses:
            return 50.0
        
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def detect_support_resistance(self) -> Tuple[Optional[float], Optional[float]]:
        """检测支撑和阻力位"""
        if len(self.price_history) < 10:
            return None, None
        
        prices = list(self.price_history)
        
        # 简单的支撑阻力检测
        recent_high = max(prices[-10:])
        recent_low = min(prices[-10:])
        
        return recent_low, recent_high
    
    def get_trend_signal(self) -> Tuple[str, float]:
        """
        获取趋势信号
        
        Returns:
            (signal, strength): 信号类型和强度
        """
        if len(self.price_history) < self.long_ma:
            return "NEUTRAL", 0.0
        
        short_ma = self.get_short_ma()
        long_ma = self.get_long_ma()
        
        if short_ma is None or long_ma is None:
            return "NEUTRAL", 0.0
        
        # 计算趋势强度
        ma_diff = (short_ma - long_ma) / long_ma
        momentum = self.calculate_price_momentum()
        volatility = self.calculate_volatility()
        
        # 综合信号强度
        strength = abs(ma_diff) + abs(momentum) * 0.5
        
        # 调整波动率影响
        if volatility > 0.02:  # 高波动率降低信号强度
            strength *= 0.7
        
        # 确定信号方向
        if ma_diff > 0.001 and momentum > 0:
            return "BULLISH", min(strength, 1.0)
        elif ma_diff < -0.001 and momentum < 0:
            return "BEARISH", min(strength, 1.0)
        else:
            return "NEUTRAL", min(strength, 1.0)
    
    def get_position_direction(self) -> str:
        """获取建议的持仓方向"""
        signal, strength = self.get_trend_signal()
        
        # 需要足够的信号强度才建议方向性交易
        if strength < 0.2:
            return "NEUTRAL"
        
        if signal == "BULLISH":
            return "LONG"
        elif signal == "BEARISH":
            return "SHORT"
        else:
            return "NEUTRAL"


class TrendBasedTradeDecision:
    """基于趋势的交易决策器"""
    
    def __init__(self, trend_analyzer: TrendAnalyzer):
        """初始化交易决策器"""
        self.trend_analyzer = trend_analyzer
        self.last_decision_time = 0
        self.decision_cooldown = 5  # 决策冷却时间(秒)
    
    def get_optimal_trade_direction(self, current_price: float, market_data: dict) -> Tuple[str, str]:
        """
        获取最优交易方向
        
        Args:
            current_price: 当前价格
            market_data: 市场数据
            
        Returns:
            (direction, reason): 交易方向和原因
        """
        current_time = time.time()
        
        # 检查决策冷却时间
        if current_time - self.last_decision_time < self.decision_cooldown:
            return "NEUTRAL", "决策冷却中"
        
        # 获取趋势信号
        signal, strength = self.trend_analyzer.get_trend_signal()
        position_direction = self.trend_analyzer.get_position_direction()
        
        # 获取技术指标
        rsi = self.trend_analyzer.calculate_rsi()
        momentum = self.trend_analyzer.calculate_price_momentum()
        volatility = self.trend_analyzer.calculate_volatility()
        
        # 决策逻辑
        if strength < 0.1:
            return "NEUTRAL", "趋势信号太弱"
        
        if volatility > 0.05:
            return "NEUTRAL", "市场波动过大"
        
        # RSI过买过卖检查
        if rsi > 80:
            if position_direction == "LONG":
                return "NEUTRAL", "RSI过买，避免做多"
            else:
                return "SHORT", "RSI过买，建议做空"
        
        if rsi < 20:
            if position_direction == "SHORT":
                return "NEUTRAL", "RSI过卖，避免做空"
            else:
                return "LONG", "RSI过卖，建议做多"
        
        # 趋势跟随策略
        if signal == "BULLISH" and momentum > 0.001:
            self.last_decision_time = current_time
            return "LONG", f"看涨趋势，强度:{strength:.3f}"
        
        if signal == "BEARISH" and momentum < -0.001:
            self.last_decision_time = current_time
            return "SHORT", f"看跌趋势，强度:{strength:.3f}"
        
        return "NEUTRAL", "无明确趋势信号"
    
    def should_exit_position(self, entry_price: float, current_price: float, 
                           position_type: str, hold_time: float) -> Tuple[bool, str]:
        """
        判断是否应该退出仓位
        
        Args:
            entry_price: 入场价格
            current_price: 当前价格
            position_type: 仓位类型 ("LONG" 或 "SHORT")
            hold_time: 持仓时间(秒)
            
        Returns:
            (should_exit, reason): 是否退出和原因
        """
        # 计算盈亏比例
        if position_type == "LONG":
            pnl_ratio = (current_price - entry_price) / entry_price
        else:  # SHORT
            pnl_ratio = (entry_price - current_price) / entry_price
        
        # 止损检查 (2%止损)
        if pnl_ratio < -0.02:
            return True, f"触发止损: {pnl_ratio*100:.2f}%"
        
        # 止盈检查 (5%止盈)
        if pnl_ratio > 0.05:
            return True, f"触发止盈: {pnl_ratio*100:.2f}%"
        
        # 持仓时间检查 (5分钟超时)
        if hold_time > 300:
            return True, f"持仓超时: {hold_time:.0f}秒"
        
        # 趋势反转检查
        signal, strength = self.trend_analyzer.get_trend_signal()
        if position_type == "LONG" and signal == "BEARISH" and strength > 0.3:
            return True, "趋势反转，做多仓位退出"
        
        if position_type == "SHORT" and signal == "BULLISH" and strength > 0.3:
            return True, "趋势反转，做空仓位退出"
        
        return False, "继续持有"
    
    def calculate_position_size(self, account_balance: float, risk_ratio: float = 0.02) -> float:
        """
        计算仓位大小
        
        Args:
            account_balance: 账户余额
            risk_ratio: 风险比例 (默认2%)
            
        Returns:
            建议的仓位大小
        """
        # 基于账户余额和风险比例计算
        risk_amount = account_balance * risk_ratio
        
        # 假设止损为2%，计算最大仓位
        stop_loss_ratio = 0.02
        max_position = risk_amount / stop_loss_ratio
        
        # 限制最大仓位不超过账户余额的10%
        max_position = min(max_position, account_balance * 0.1)
        
        return max_position 