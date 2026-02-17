"""
统一日志配置模块
提供带颜色的、分级别的日志输出
全局只使用一个 logger 实例
"""
import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',       # 青色
        'INFO': '\033[32m',        # 绿色
        'WARNING': '\033[33m',     # 黄色
        'ERROR': '\033[31m',       # 红色
        'CRITICAL': '\033[35m',    # 紫色
        'RESET': '\033[0m',        # 重置
        'BOLD': '\033[1m',         # 粗体
    }

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        bold = self.COLORS['BOLD']

        record.levelname_colored = f"{color}{bold}{levelname:8}{reset}"
        record.name_colored = f"{self.COLORS['DEBUG']}{record.name}{reset}"

        return super().format(record)


def setup_logger(
    name: str = "scholar_agent",
    level: int = logging.DEBUG,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    设置并获取全局 logger

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        console: 是否输出到控制台

    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = ColoredFormatter(
        '%(asctime)s | %(levelname_colored)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file:
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()
