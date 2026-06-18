"""自定义异常：简化错误日志和终止信号。

  AppException — 带 logger.error 的基础异常
  AppTypeError — 类型错误（旧版遗留，可用内置 TypeError 替代）
  StopExecution — 全局停止信号：截图检测到此异常 → 不再执行后续操作
"""

from loguru import logger


class AppException(Exception):
    def __init__(self, message):
        super().__init__(message)
        logger.error(message)


class AppTypeError(AppException):
    def __init__(self, message):
        super().__init__(message)


class StopExecution(Exception):
    def __init__(self):
        super().__init__("停止执行程序")
