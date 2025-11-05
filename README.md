<div align="center">

![Holistica Quant Header](./docs/holistica-header.svg)

**基于LangGraph构建的金融分析智能体系统**

</div>

## 系统架构

```
query -> plan -> data -> strategy
```

### 核心组件

1. **计划团队（PlanTeam）**
   - `plan_analyst`: 分析用户查询，提取股票代码（6位数字），制定数据收集计划
   - 使用结构化输出（Pydantic Schema）确保输出格式一致
   - 从用户查询或知识库中推断股票代码，不依赖外部工具

2. **数据团队（DataTeam）**
   - `data_analyst`: 调用工具收集数据（股票基本面、市场数据、新闻等），生成详细分析报告
   - 支持迭代收集（最多3次），自动评估数据充分性
   - 使用工具结果摘要优化token使用，确保LLM能正常生成内容

3. **策略团队（StrategyTeam）**
   - `strategy_analyst`: 基于数据分析报告和Agentic RAG历史洞见生成投资策略和建议
   - 集成Agentic RAG：读取相关历史洞见，生成策略后保存新洞见（暂未实现）
   - 生成最终投资报告（包含宏观、微观、风险、建议等完整分析）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写API密钥：

```bash
cp .env.example .env
```

至少配置一个LLM提供商的API key（优先级：豆包 > chatgpt > claude > deepseek）

### 3. 运行

```bash
python main.py "分析海陆重工的投资价值"
```


**注意**：当前系统仅支持A股市场数据，请使用A股名称或股票代码（如 sh600588、sz002594 等）。

## 配置说明

### LLM提供商

支持多个LLM提供商，按优先级自动选择：

1. **豆包（Doubao）** - 字节跳动
2. **ChatGPT** - OpenAI
3. **Claude** - Anthropic
4. **DeepSeek**

### 数据源

- **市场数据**: akshare（指数、板块资金流）
- **股票基本面数据**: akshare（财务指标、公司信息）
- **股票市场数据**: akshare（实时行情、K线数据）
- **新闻数据**: sina（默认启用），thx（可选，默认禁用）
- **通用工具**: calculator（数学计算）、web_search（网络搜索）、db_query（数据库查询）

## 项目结构

```
holisticaquant/
├── agents/              # 智能体模块
│   ├── planTeam/       # 计划团队（plan_analyst）
│   ├── dataTeam/       # 数据团队（data_analyst）
│   ├── strategyTeam/   # 策略团队（strategy_analyst）
│   └── utils/          # 工具函数（BaseAgent、schemas、agent_tools等）
├── config/             # 配置管理
├── dataflows/          # 数据流模块
│   ├── datasource/     # 数据源（akshare等）
│   └── general/        # 通用工具（calculator、web_search、db_query）
├── graph/              # 图构建和执行（LangGraph）
├── memory/             # Agentic RAG推理引擎（FinancialReasoningEngine）
└── utils/              # 工具函数（LLM工厂等）

main.py                 # 主入口
.env.example            # 环境变量示例
requirements.txt        # 依赖包
```

## 环境变量

详见 `.env.example` 文件

主要配置项：
- **LLM配置**：`DOUBAO_API_KEY`、`OPENAI_API_KEY`等
- **Agentic RAG**：`AGENTIC_RAG_ENABLED`、`AGENTIC_RAG_MAX_INSIGHTS`等
- **Agent配置**：`MAX_ITERATIONS`（工具调用最大迭代次数）、`MAX_COLLECTION_ITERATIONS`（数据收集最大迭代次数）
- **工具配置**：`TOOL_MAX_RESULT_LENGTH`（工具结果最大长度）、`TOOL_MAX_RECORDS`（最大记录数）
- **新闻工具**：`TOOL_SINA_NEWS_ENABLED`、`TOOL_SINA_NEWS_END_PAGE`、`TOOL_THX_NEWS_ENABLED`、`TOOL_THX_NEWS_MAX_PAGES`

## 核心特性

### 结构化输出

所有Agent使用Pydantic Schema进行结构化输出，确保数据格式一致：
- `PlanSchema`: plan_analyst的输出（tickers、time_range等）
- `DataSufficiencySchema`: data_analyst的数据充分性评估
- `StrategySchema`: strategy_analyst的投资建议

### Agentic RAG（金融洞见记忆）

集成Agentic RAG系统，智能管理金融洞见：
- **洞见提取**：从策略报告中自动提取关键金融洞见
- **智能检索**：基于关键词搜索相关历史洞见
- **记忆管理**：自动遗忘机制，控制内存大小
- **同步执行**：所有Agentic RAG操作都是同步的，简化错误处理

### 工具管理

- **自动截断**：工具结果自动截断，避免token过多
- **重复检测**：防止重复调用相同工具
- **失败追踪**：记录工具调用成功率，支持降级建议
- **并行执行**：支持并行执行多个工具调用

### 错误处理

- **严格验证**：空内容时直接报错，不掩盖问题
- **详细日志**：记录LLM返回的完整信息，便于调试
- **Token优化**：使用工具结果摘要，避免token过多导致生成失败

## 开发

### 添加新的数据源

继承 `DataSourceBase` 并实现 `get_data` 方法：

```python
from holisticaquant.dataflows.datasource import DataSourceBase

class MyDataSource(DataSourceBase):
    async def get_data(self, trigger_time: str, **query_params) -> pd.DataFrame:
        # 实现数据获取逻辑
        # 注意：所有数据源都是异步的
        pass
```

### 添加新的智能体

继承 `BaseAgent` 并实现抽象方法：

```python
from holisticaquant.agents.utils.base_agent import BaseAgent
from holisticaquant.agents.utils.schemas import YourSchema  # Pydantic Schema
from pydantic import BaseModel
from typing import Optional, Type, Dict, Any

class MyAgent(BaseAgent):
    def _get_structured_output_schema(self) -> Optional[Type[BaseModel]]:
        # 返回结构化输出Schema（如果需要）
        return YourSchema  # 或 None
    
    def _needs_text_report(self) -> bool:
        # 是否需要生成文本报告
        return True
    
    def _get_system_message(self) -> str:
        # 返回系统消息
        return "你的系统提示词"
    
    def _get_user_input(self, state) -> str:
        # 返回用户输入
        return "基于state构建的用户输入"
    
    def _get_continue_prompt(self) -> str:
        # 返回继续处理的提示词（可选）
        return "请继续处理。"
    
    def _validate_state(self, state):
        # 验证状态（可选）
        pass
    
    def _process_result(
        self, 
        state, 
        structured_data: Optional[BaseModel],  # 结构化输出数据
        text_content: Optional[str],  # 文本报告内容
        tool_results: Dict[str, str]  # 工具调用结果
    ) -> Dict[str, Any]:
        # 处理结果并返回state更新
        return {
            "field1": value1,
            "field2": value2,
            "output_summary": "处理摘要"  # 必需字段
        }
```

**关键特性**：
- **结构化输出**：使用Pydantic Schema确保输出格式一致
- **工具调用**：自动处理工具调用、结果截断、重复检测
- **错误处理**：空内容时直接报错，不掩盖问题
- **Token优化**：使用工具结果摘要，避免token过多


