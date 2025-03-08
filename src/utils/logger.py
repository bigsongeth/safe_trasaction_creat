import logging
import os
import sys
from typing import Optional

# 创建日志格式
VERBOSE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
SIMPLE_FORMAT = '%(message)s'

# 日志级别，可以通过环境变量配置
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
}

class SafeLogger:
    """
    Safe应用的日志工具，用于优化终端输出，减少重复信息
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SafeLogger, cls).__new__(cls)
            # 初始化日志配置
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # 获取环境变量中配置的日志级别，默认为INFO
        log_level_name = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_level = LOG_LEVELS.get(log_level_name, logging.INFO)
        
        # 设置是否显示详细日志
        self.verbose = os.getenv('VERBOSE_LOGGING', 'False').lower() == 'true'
        
        # 配置日志记录器
        self.logger = logging.getLogger('safe_app')
        self.logger.setLevel(self.log_level)
        
        # 清除任何已存在的处理器
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        
        # 设置日志格式
        if self.verbose:
            formatter = logging.Formatter(VERBOSE_FORMAT)
        else:
            formatter = logging.Formatter(SIMPLE_FORMAT)
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 记录已输出的消息，用于避免重复
        self.logged_messages = set()
    
    def debug(self, message: str, repeat_ok: bool = False):
        """输出调试级别日志"""
        if not repeat_ok and message in self.logged_messages:
            return
        self.logger.debug(message)
        self.logged_messages.add(message)
    
    def info(self, message: str, repeat_ok: bool = False):
        """输出信息级别日志"""
        if not repeat_ok and message in self.logged_messages:
            return
        self.logger.info(message)
        self.logged_messages.add(message)
    
    def warning(self, message: str, repeat_ok: bool = False):
        """输出警告级别日志"""
        if not repeat_ok and message in self.logged_messages:
            return
        self.logger.warning(message)
        self.logged_messages.add(message)
    
    def error(self, message: str, repeat_ok: bool = False):
        """输出错误级别日志"""
        if not repeat_ok and message in self.logged_messages:
            return
        self.logger.error(message)
        self.logged_messages.add(message)
    
    def section(self, title: str):
        """输出分节标题，便于阅读"""
        divider = "-" * 40
        self.info(f"\n{divider}")
        self.info(f" {title} ")
        self.info(f"{divider}")
    
    def progress(self, step: int, total: int, message: str):
        """输出进度信息"""
        progress_bar = f"[{'#' * step}{' ' * (total - step)}]"
        self.info(f"{progress_bar} {step}/{total} {message}", repeat_ok=True)
    
    def transaction_info(self, address: str, amount: float, token: str = "USDT"):
        """输出交易信息，以标准格式显示"""
        formatted_address = self._format_address(address)
        self.info(f"转账: {formatted_address} ← {amount} {token}")
    
    def _format_address(self, address: str) -> str:
        """格式化地址，只显示开头和结尾几位，方便阅读"""
        if not address or len(address) < 10:
            return address
        return f"{address[:6]}...{address[-4:]}"


# 创建单例实例
logger = SafeLogger() 