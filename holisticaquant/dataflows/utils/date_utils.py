"""
日期工具函数

提供交易日相关的日期计算功能
"""
from datetime import datetime, timedelta
from typing import Optional


def get_current_datetime(trigger_time: Optional[str] = None) -> str:
    """
    获取当前时间
    
    Args:
        trigger_time: 如果提供，直接返回；否则返回当前时间
        
    Returns:
        时间字符串，格式：YYYY-MM-DD HH:MM:SS
    """
    if trigger_time:
        return trigger_time
    else:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_previous_trading_date(trigger_time: str, output_format: str = "%Y%m%d") -> str:
    """
    获取 trigger_time 的上一个交易日
    
    注意：这是一个简化实现，实际应该使用交易日历。
    这个实现会：
    - 如果是周一，返回上周五
    - 如果是周末，返回上一个周五
    - 其他情况返回前一天
    
    Args:
        trigger_time: 触发时间，格式：YYYY-MM-DD HH:MM:SS
        output_format: 输出格式，默认：%Y%m%d
        
    Returns:
        上一个交易日，格式：YYYYMMDD
    """
    try:
        # 解析 trigger_time
        trigger_datetime = datetime.strptime(trigger_time, '%Y-%m-%d %H:%M:%S')
        trigger_date = trigger_datetime.date()
        
        # 计算上一个交易日（简化版：跳过周末）
        previous_date = trigger_date - timedelta(days=1)
        
        # 如果前一天是周六，往前推2天（到周五）
        if previous_date.weekday() == 5:  # 周六
            previous_date = previous_date - timedelta(days=1)
        # 如果前一天是周日，往前推2天（到周五）
        elif previous_date.weekday() == 6:  # 周日
            previous_date = previous_date - timedelta(days=2)
        
        # 格式化输出
        return previous_date.strftime(output_format)
        
    except Exception as e:
        # 如果解析失败，返回当前日期前一天
        today = datetime.now()
        previous_date = today - timedelta(days=1)
        return previous_date.strftime(output_format)


def is_trading_day(date_str: Optional[str] = None) -> bool:
    """
    判断是否为交易日
    
    注意：简化实现，只排除周末，不排除节假日
    
    Args:
        date_str: 日期字符串，格式：YYYY-MM-DD 或 YYYYMMDD。如果为 None，使用今天
        
    Returns:
        True 表示是交易日，False 表示不是
    """
    if date_str:
        try:
            if len(date_str) == 8:  # YYYYMMDD
                dt = datetime.strptime(date_str, '%Y%m%d')
            else:  # YYYY-MM-DD
                dt = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()
    
    # 排除周末
    return dt.weekday() < 5  # 0-4 是周一到周五


if __name__ == "__main__":
    # 测试代码
    print("当前时间:", get_current_datetime())
    print("上一个交易日:", get_previous_trading_date("2025-11-03 10:00:00"))
    print("是否为交易日:", is_trading_day("2025-11-03"))

