"""
同花顺新闻爬虫数据源

从同花顺财经网站爬取新闻数据，返回统一格式
"""
import asyncio
import requests
import json
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import random
from loguru import logger

from .data_source_base import DataSourceBase


class ThxNewsCrawl(DataSourceBase):
    """
    同花顺新闻爬虫
    
    从同花顺财经网站获取新闻数据，返回统一格式的 DataFrame
    """
    
    def __init__(self, max_pages: int = 5, enable_frontend_crawl: bool = False,
                 max_size_kb: Optional[float] = 512.0,
                 max_time_range_days: Optional[int] = 7,
                 max_records: Optional[int] = 500,
                 use_cache: bool = True):
        """
        Args:
            max_pages: 最大爬取页数
            enable_frontend_crawl: 是否启用前端爬取（需要 crawl4ai，默认关闭）
            max_size_kb: 最大数据大小（KB）
            max_time_range_days: 最大时间范围（天数）
            max_records: 最大记录数
            use_cache: 是否使用缓存，False 表示每次都获取最新数据（适合LLM调用），默认 True
        """
        super().__init__("thx_news_crawl", max_size_kb=max_size_kb,
                        max_time_range_days=max_time_range_days,
                        max_records=max_records, use_cache=use_cache)
        self.max_pages = max_pages
        self.enable_frontend_crawl = enable_frontend_crawl

    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def parse_pub_time_from_frontend(self, line: str, url: str) -> str:
        """从前端页面解析发布时间"""
        try:
            date_part = None
            m_url_date = re.search(r"/(\d{8})/", url or "")
            if m_url_date:
                ymd = m_url_date.group(1)
                date_part = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
            time_part = None
            m_time = re.search(r"\b(\d{1,2}):(\d{2})\b", line or "")
            if m_time:
                h = int(m_time.group(1))
                m = int(m_time.group(2))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    time_part = f"{h:02d}:{m:02d}:00"
            if not date_part:
                m_cn = re.search(r"(\d{4})[年/\\-](\d{1,2})[月/\\-](\d{1,2})", line or "")
                if m_cn:
                    y = int(m_cn.group(1))
                    mo = int(m_cn.group(2))
                    d = int(m_cn.group(3))
                    date_part = f"{y:04d}-{mo:02d}-{d:02d}"
            if date_part and time_part:
                return f"{date_part} {time_part}"
            if date_part:
                return f"{date_part} 00:00:00"
            return ""
        except Exception:
            return ""

    def extract_company_news_from_markdown(self, md: str) -> List[Dict[str, Any]]:
        """从 Markdown 格式提取公司新闻"""
        records = []
        for raw_line in (md or "").splitlines():
            line = raw_line.strip()
            if not (line.startswith('* ') or line.startswith('- ')):
                continue
            m_link = re.search(r"\[([^\]]+)\]\((https?://[^)\s]+)[^)]*\)", line)
            if not m_link:
                continue
            title = (m_link.group(1) or "").strip()
            url = (m_link.group(2) or "").strip()
            if not re.search(r"/(\d{8})/", url):
                continue
            tail = line[m_link.end():]
            m_intro = re.search(r"\[([^\]]+)\]", tail)
            intro = (m_intro.group(1) or "").strip() if m_intro else ""
            content = self.clean_text(intro)
            pub_time = self.parse_pub_time_from_frontend(line, url)
            records.append({
                "title": title or "",
                "content": content or "",
                "pub_time": pub_time or "",
                "url": url or "",
            })
        return records

    def clean_html_content(self, html_content: str) -> str:
        """清理HTML内容"""
        if not html_content:
            return ""
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return clean_text

    def parse_pub_time(self, timestamp: int) -> str:
        """解析时间戳为字符串"""
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ""

    def get_news_data(self, page: int = 1, pagesize: int = 400) -> List[Dict[str, Any]]:
        """获取新闻数据（API方式）"""
        url = "https://news.10jqka.com.cn/tapp/news/push/stock/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://news.10jqka.com.cn/realtimenews.html',
            'Origin': 'https://news.10jqka.com.cn',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        params = {
            'page': page,
            'tag': '',
            'track': 'website',
            'pagesize': pagesize
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            news_list = data.get('data', {}).get('list', [])
            processed_news = []
            for news in news_list:
                title = news.get('title', '')
                content = self.clean_html_content(news.get('digest', '')) 
                pub_time = self.parse_pub_time(int(news.get('ctime', 0))) 
                news_url = news.get('url', '')
                
                if not news_url and news.get('id'):
                    news_url = f"https://news.10jqka.com.cn/tapp/news/push/stock/{news.get('id')}/"
                
                processed_news.append({
                    'title': title,
                    'content': content,
                    'pub_time': pub_time,
                    'url': news_url
                })
            
            return processed_news
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return []

    def crawl_multiple_pages(self) -> List[Dict[str, Any]]:
        """爬取多页数据"""
        all_news = []
        
        for page in range(1, self.max_pages + 1):
            page_news = self.get_news_data(page=page, pagesize=400)
            
            if not page_news:
                break
                
            all_news.extend(page_news)
            # 优化：移除人为延迟以提升性能
            # 如果需要限流，可以考虑使用异步sleep: await asyncio.sleep(0.1)
            # if page < self.max_pages:
            #     delay = random.uniform(1, 3)
            #     time.sleep(delay)
        
        return all_news

    async def crawl_frontend_pages(self) -> List[Dict[str, Any]]:
        """前端爬取（需要 crawl4ai）"""
        if not self.enable_frontend_crawl:
            logger.info("前端爬取已禁用")
            return []
        
        try:
            # 尝试导入 crawl4ai
            try:
                from crawl4ai import AsyncWebCrawler
            except ImportError:
                logger.warning("crawl4ai 未安装，跳过前端爬取")
                return []
            
            async with AsyncWebCrawler() as crawler:
                company_news_urls = [
                    "https://stock.10jqka.com.cn/companynews_list/index.shtml",
                    *[f"https://stock.10jqka.com.cn/companynews_list/index_{i}.shtml" for i in range(2, 21)],
                ]
                
                hsdp_urls = [
                    "https://stock.10jqka.com.cn/hsdp_list/index.shtml",
                    *[f"https://stock.10jqka.com.cn/hsdp_list/index_{i}.shtml" for i in range(2, 21)],
                ]
                
                page_urls = company_news_urls + hsdp_urls
                logger.info(f"开始前端爬取，共 {len(page_urls)} 页")
                
                results = await crawler.arun_many(urls=page_urls)
                logger.info(f"前端爬取完成，处理 {len(results or [])} 个响应")
                
                all_records = []
                for res in (results or []):
                    page_markdown = getattr(res, "markdown", "")
                    all_records.extend(self.extract_company_news_from_markdown(page_markdown))
                
                logger.info(f"前端爬取完成，获取 {len(all_records)} 条记录")
                return all_records
                
        except Exception as e:
            logger.error(f"前端爬取失败: {e}")
            return []

    async def get_data(self, trigger_time: str, **query_params) -> pd.DataFrame:
        """
        实现基类的抽象方法，获取数据
        
        Args:
            trigger_time: 触发时间字符串
            
        Returns:
            DataFrame with columns ['title', 'content', 'pub_time', 'url']
        """
        tasks = [
            asyncio.to_thread(self.crawl_multiple_pages),  # API爬取
            self.crawl_frontend_pages()  # 前端爬取
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理API爬取结果
        api_news_data = []
        if isinstance(results[0], list):
            api_news_data = results[0]
            logger.info(f"✅ API爬取成功: {len(api_news_data)} 条记录")
        elif isinstance(results[0], Exception):
            logger.error(f"❌ API爬取失败: {results[0]}")
        else:
            logger.warning(f"⚠️ API爬取返回意外类型: {type(results[0])}")
        
        # 处理前端爬取结果
        frontend_news_data = []
        if isinstance(results[1], list):
            frontend_news_data = results[1]
            logger.info(f"✅ 前端爬取成功: {len(frontend_news_data)} 条记录")
        elif isinstance(results[1], Exception):
            logger.error(f"❌ 前端爬取失败: {results[1]}")
        else:
            logger.warning(f"⚠️ 前端爬取返回意外类型: {type(results[1])}")
        
        # 合并所有数据
        all_news_data = api_news_data + frontend_news_data
        
        logger.info(f"📈 数据收集汇总: API {len(api_news_data)} 条, 前端 {len(frontend_news_data)} 条, 合计 {len(all_news_data)} 条")
        
        # 检查是否至少有一个数据源成功
        if not api_news_data and not frontend_news_data:
            logger.error("❌ API和前端爬取都失败，无可用数据")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        elif not all_news_data:
            logger.warning("⚠️ 未收集到任何数据")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        # 去重
        seen_urls = set()
        deduped_news = []
        for news in all_news_data:
            url = news.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped_news.append(news)
        
        df = pd.DataFrame(deduped_news)
        
        # 确保所有必需列都存在
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        
        # 只返回必需列，时间筛选由 normalize_dataframe 统一处理
        df = df[self.REQUIRED_COLUMNS].copy()
        
        logger.info(f"成功获取同花顺新闻原始数据，共 {len(df)} 条记录（去重后，时间筛选由 normalize_dataframe 统一处理）")
        return df


if __name__ == "__main__":
    # 测试代码
    crawler = ThxNewsCrawl(max_pages=2, enable_frontend_crawl=False)
    df = asyncio.run(crawler.fetch_data_async("2025-01-20 15:00:00"))
    print(f"获取到 {len(df)} 条记录")
    if not df.empty:
        print(df.head())

