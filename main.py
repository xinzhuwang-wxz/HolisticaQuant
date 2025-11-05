"""
HolisticaQuant 主入口

使用示例：
    python main.py "分析用友网络（sh600588）的投资价值"
    
或使用异步：
    python -m asyncio main.py "分析用友网络（sh600588）的投资价值"
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from holisticaquant.graph import HolisticaGraph
from holisticaquant.utils.llm_factory import create_llm
from holisticaquant.config.config import get_config
from loguru import logger


def setup_logging(debug: bool = False):
    """设置日志"""
    logger.remove()
    if debug:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")


async def main_async(query: str, provider: str = None):
    """
    异步主函数
    
    Args:
        query: 用户查询
        provider: LLM提供商（可选，默认按优先级自动选择）
    """
    # 加载配置
    config = get_config().config
    debug = config.get("debug", False)
    
    setup_logging(debug)
    
    logger.info("=" * 60)
    logger.info("HolisticaQuant - 金融分析智能体系统")
    logger.info("=" * 60)
    
    try:
        # 创建LLM
        logger.info("初始化LLM...")
        llm = create_llm(provider=provider, config=config)
        logger.info(f"LLM初始化成功")
        
        # 创建图
        logger.info("构建工作流图...")
        graph = HolisticaGraph(llm=llm, config=config)
        logger.info("工作流图构建完成")
        
        # 创建上下文
        # trigger_time格式说明：
        # - '%Y-%m-%d %H:00:00': 按小时聚合（分钟和秒设为00），适合金融数据按小时统计
        # - '%Y-%m-%d %H:%M:%S': 精确到秒，适合需要精确时间的场景
        # 当前使用按小时聚合格式，因为金融数据通常按小时或交易日统计
        context = {
            "trigger_time": datetime.now().strftime('%Y-%m-%d %H:00:00'),
        }
        
        logger.info(f"触发时间: {context['trigger_time']} (按小时聚合格式)")
        
        # 执行工作流
        logger.info("=" * 60)
        logger.info(f"开始处理查询: {query}")
        logger.info("=" * 60)
        
        state = await graph.run_async(query=query, context=context)
        
        # 输出结果
        logger.info("=" * 60)
        logger.info("执行完成")
        logger.info("=" * 60)
        
        # 获取报告
        report = graph.get_report(state)
        print("\n" + "=" * 60)
        print("投资策略报告")
        print("=" * 60)
        print(report)
        print("=" * 60)
        
        # 输出追踪信息
        if debug and state.get("trace"):
            print("\n追踪信息：")
            for trace in state["trace"]:
                print(f"  [{trace['step']}] {trace['agent']}: {trace['action']}")
                if trace.get("output"):
                    print(f"    输出: {trace['output'][:100]}...")
        
        return state
        
    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback
        if debug:
            traceback.print_exc()
        raise


def main():
    """同步主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <查询> [--provider=<provider>]")
        print("\n示例:")
        print('  python main.py "分析用友网络（sh600588）的投资价值"')
        print('  python main.py "分析比亚迪（sz002594）的投资价值" --provider=doubao')
        print("\n支持的LLM提供商: doubao, chatgpt, claude, deepseek")
        sys.exit(1)
    
    query = sys.argv[1]
    
    # 解析参数
    provider = None
    for arg in sys.argv[2:]:
        if arg.startswith("--provider="):
            provider = arg.split("=")[1]
    
    # 运行异步主函数
    asyncio.run(main_async(query, provider))


if __name__ == "__main__":
    main()

