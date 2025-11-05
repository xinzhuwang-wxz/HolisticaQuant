"""
新浪财经新闻爬虫数据源示例

这是一个示例实现，展示如何从网站爬取数据并返回统一格式
"""
import asyncio
import aiohttp
import re
import json
import html
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from .data_source_base import DataSourceBase


class SinaNewsCrawl(DataSourceBase):
    """
    新浪财经新闻爬虫
    
    从新浪财经 API 获取新闻数据，返回统一格式的 DataFrame
    """
    
    def __init__(self, start_page: int = 1, end_page: int = 10,
                 max_size_kb: Optional[float] = 1024.0,
                 max_time_range_days: Optional[int] = 7,
                 max_records: Optional[int] = 1000,
                 use_cache: bool = True):
        """
        Args:
            start_page: 起始页码
            end_page: 结束页码
            max_size_kb: 最大数据大小（KB），None 表示无限制
            max_time_range_days: 最大时间范围（天数），None 表示无限制
            max_records: 最大记录数，None 表示无限制
            use_cache: 是否使用缓存，False 表示每次都获取最新数据（适合LLM调用），默认 True
        """
        super().__init__("sina_news_crawl", max_size_kb=max_size_kb,
                        max_time_range_days=max_time_range_days,
                        max_records=max_records, use_cache=use_cache)
        self.start_page = start_page
        self.end_page = end_page
        self.base_url = "http://feed.mix.sina.com.cn/api/roll/get"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Referer": "https://finance.sina.com.cn/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.fetch_full_content = True  # 是否抓取文章页以补全内容
        self.article_concurrency = 2  # 控制抓取文章页的并发数
        
    async def fetch_page(self, session: aiohttp.ClientSession, page: int) -> List[Dict[str, Any]]:
        """异步获取单个页面的数据"""
        params = {
            "pageid": 384,
            "lid": 2519,
            "k": "",
            "num": 50,
            "page": page
        }
        
        try:
            async with session.get(self.base_url, params=params, headers=self.headers, timeout=15) as response:
                text = await response.text()
                
                # 兼容 JSONP 与纯 JSON
                m = re.search(r'^\s*[\w$]+\((.*)\)\s*;?\s*$', text.strip(), re.S)
                json_text = m.group(1) if m else text.strip()
                data = json.loads(json_text)
                
                # 提取items
                items = self.extract_items(data, page)
                
                # 尝试补全内容
                if self.fetch_full_content and items:
                    await self.enrich_items_with_full_content(session, items)
                
                return items
                
        except Exception as e:
            logger.error(f"获取第 {page} 页数据失败: {e}")
            return []
    
    def extract_items(self, data: dict, page: int) -> List[Dict[str, Any]]:
        """从API响应中提取新闻items"""
        try:
            if isinstance(data, dict):
                result = data.get("result", {})
                if isinstance(result, dict):
                    data_field = result.get("data", [])
                    if isinstance(data_field, list):
                        processed_items = []
                        for raw in data_field:
                            if not isinstance(raw, dict):
                                continue
                            
                            # 提取发布时间
                            publish_time = self.normalize_publish_time(raw)
                            
                            # 本地可用的简介
                            intro_local = self.choose_best_intro_local(raw)
                            
                            # 目标URL
                            url = self.choose_best_url(raw)
                            
                            processed_items.append({
                                "title": raw.get("title") or raw.get("stitle") or "",
                                "content": intro_local or "",
                                "pub_time": publish_time or "",
                                "url": url or "",
                            })
                        return processed_items
            return []
        except Exception as e:
            logger.error(f"解析第 {page} 页数据失败: {e}")
            return []
    
    def normalize_publish_time(self, raw_item: dict) -> str:
        """将多种时间格式标准化为 'YYYY-MM-DD HH:MM:SS' 字符串"""
        try:
            # 候选时间字段
            candidate_keys = [
                "ctime", "intime", "mtime", "create_time", "createtime",
                "pub_time", "pubTime", "pubdate", "pubDate", "time", "update_time"
            ]
            raw_time_value = None
            for key in candidate_keys:
                if key in raw_item and raw_item.get(key) not in (None, ""):
                    raw_time_value = raw_item.get(key)
                    break
            
            if raw_time_value is None:
                return ""
            
            # 数字时间戳（秒或毫秒）
            if isinstance(raw_time_value, (int, float)):
                timestamp = int(raw_time_value)
            elif isinstance(raw_time_value, str) and re.fullmatch(r"\d{10,13}", raw_time_value):
                timestamp = int(raw_time_value)
            else:
                # 尝试解析常见的时间字符串
                if isinstance(raw_time_value, str):
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d",
                        "%Y/%m/%d %H:%M:%S",
                        "%Y/%m/%d %H:%M",
                        "%Y/%m/%d",
                    ]:
                        try:
                            dt = datetime.strptime(raw_time_value.strip(), fmt)
                            return dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pass
                return str(raw_time_value)

            # 毫秒与秒的区分
            if timestamp > 1_000_000_000_000:
                timestamp //= 1000
            elif 0 < timestamp < 10_000_000_000:
                pass
            else:
                timestamp = int(str(timestamp)[:10])

            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""
    
    def choose_best_url(self, raw_item: dict) -> str:
        """选择最合适的文章URL"""
        url = raw_item.get("url")
        if url:
            return url
        # 有些返回的 urls 是 JSON 字符串
        urls_field = raw_item.get("urls")
        if isinstance(urls_field, list) and urls_field:
            return urls_field[0]
        if isinstance(urls_field, str) and urls_field.strip().startswith("["):
            try:
                parsed = json.loads(urls_field)
                if isinstance(parsed, list) and parsed:
                    return parsed[0]
            except Exception:
                pass
        wapurl = raw_item.get("wapurl")
        if wapurl:
            return wapurl
        return ""
    
    def choose_best_intro_local(self, raw_item: dict) -> str:
        """在不请求文章页的情况下，选取最合适的简介字段"""
        candidates = [
            raw_item.get("intro"),
            raw_item.get("summary"),
            raw_item.get("wapsummary")
        ]
        candidates = [c for c in candidates if isinstance(c, str) and c.strip()]
        if not candidates:
            return ""
        # 选择最长的一条
        best = max(candidates, key=lambda x: len(x))
        return self._strip_html_tags(best)
    
    def should_fetch_full_content(self, content_text: str) -> bool:
        """判断是否需要抓取文章页补全内容"""
        if not content_text:
            return True
        text = content_text.strip()
        if len(text) < 60:
            return True
        if text.endswith("…") or text.endswith("..."):
            return True
        return False
    
    async def enrich_items_with_full_content(self, session: aiohttp.ClientSession, items: List[Dict[str, Any]]):
        """并发抓取文章页，补全内容"""
        semaphore = asyncio.Semaphore(self.article_concurrency)
        
        async def process_one(item: Dict[str, Any]):
            if not self.should_fetch_full_content(item.get("content", "")):
                return
            url = item.get("url")
            if not url:
                return
            try:
                async with semaphore:
                    content_full = await self.fetch_article_content(session, url)
                if content_full and len(content_full) > len(item.get("content") or ""):
                    item["content"] = content_full
            except Exception:
                pass
        
        await asyncio.gather(*[process_one(it) for it in items])
    
    async def fetch_article_content(self, session: aiohttp.ClientSession, url: str) -> str:
        """抓取文章页内容：优先 meta description，其次正文首段"""
        try:
            async with session.get(url, headers=self.headers, timeout=15) as resp:
                html_text = await resp.text(errors="ignore")
            if not html_text:
                return ""
            
            # 先尝试 meta description
            meta_desc = self._extract_meta_description(html_text)
            if meta_desc:
                return meta_desc
            
            # 退化到正文首段
            first_paragraph = self._extract_first_paragraph(html_text)
            if first_paragraph:
                return first_paragraph
            return ""
        except Exception:
            return ""
    
    def _extract_meta_description(self, html_text: str) -> str:
        """从HTML中提取<meta name="description">或<meta property="og:description">"""
        try:
            # name=description
            m1 = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html_text, re.I | re.S)
            if m1:
                return html.unescape(self._clean_whitespace(m1.group(1)))
            # property=og:description
            m2 = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html_text, re.I | re.S)
            if m2:
                return html.unescape(self._clean_whitespace(m2.group(1)))
            return ""
        except Exception:
            return ""
    
    def _extract_first_paragraph(self, html_text: str) -> str:
        """从常见容器中提取首段文本"""
        try:
            container_patterns = [
                r'<div[^>]+id=["\']artibody["\'][^>]*>(.*?)</div>',
                r'<article[^>]*>(.*?)</article>',
                r'<div[^>]+class=["\'][^"\']*(?:article|content)[^"\']*["\'][^>]*>(.*?)</div>',
            ]
            for pat in container_patterns:
                m = re.search(pat, html_text, re.I | re.S)
                if m:
                    inner = m.group(1)
                    # 找第一个<p>
                    p = re.search(r'<p[^>]*>(.*?)</p>', inner, re.I | re.S)
                    if p:
                        text = self._strip_html_tags(p.group(1))
                        return self._clean_whitespace(text)
            # 兜底：全局第一个<p>
            p = re.search(r'<p[^>]*>(.*?)</p>', html_text, re.I | re.S)
            if p:
                text = self._strip_html_tags(p.group(1))
                return self._clean_whitespace(text)
            return ""
        except Exception:
            return ""
    
    def _strip_html_tags(self, text: str) -> str:
        """去除HTML标签"""
        text = re.sub(r'<script[\s\S]*?</script>', ' ', text, flags=re.I)
        text = re.sub(r'<style[\s\S]*?</style>', ' ', text, flags=re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        return html.unescape(text)
    
    def _clean_whitespace(self, text: str) -> str:
        """清理空白字符"""
        return re.sub(r'\s+', ' ', (text or '')).strip()
    
    async def crawl_all_pages(self) -> List[Dict[str, Any]]:
        """爬取所有页面"""
        all_items = []
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = []
            for page in range(self.start_page, self.end_page + 1):
                task = self.fetch_page(session, page)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for page, result in enumerate(results, start=self.start_page):
                if isinstance(result, Exception):
                    logger.error(f"第 {page} 页发生异常: {result}")
                elif isinstance(result, list):
                    all_items.extend(result)
        
        return all_items
    
    async def get_data(self, trigger_time: str, **query_params) -> pd.DataFrame:
        """
        实现基类的抽象方法，获取数据
        
        Args:
            trigger_time: 触发时间字符串
            
        Returns:
            DataFrame with columns ['title', 'content', 'pub_time', 'url']
        """
        try:
            items = await self.crawl_all_pages()
        except Exception as e:
            logger.error(f"爬取数据失败: {e}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        if not items:
            logger.warning("未收集到任何数据")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        logger.info(f"处理 {len(items)} 条收集到的数据...")
        
        df = pd.DataFrame(items)
        
        # 处理时间字段并筛选
        if not df.empty and 'pub_time' in df.columns:
            df['pub_time'] = pd.to_datetime(df['pub_time'], errors='coerce')
            end_dt = pd.to_datetime(trigger_time, errors='coerce')
            mask = pd.Series(True, index=df.index)
            if not pd.isna(end_dt):
                # 筛选最近一天的数据
                start_dt = end_dt - pd.Timedelta(days=1)
                mask &= (df['pub_time'] >= start_dt) & (df['pub_time'] < end_dt)
            df = df.loc[mask].reset_index(drop=True)
            if 'pub_time' in df.columns:
                df['pub_time'] = df['pub_time'].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # 确保所有必需列都存在
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        
        logger.info(f"成功获取新浪财经新闻直到 {trigger_time}，共 {len(df)} 条记录")
        return df


if __name__ == "__main__":
    # 测试代码
    crawler = SinaNewsCrawl(start_page=1, end_page=2)
    df = asyncio.run(crawler.fetch_data_async("2025-01-20 15:00:00"))
    print(f"获取到 {len(df)} 条记录")
    if not df.empty:
        print(df.head())
        print(f"\n列名: {df.columns.tolist()}")
        print(f"\n示例数据:")
        print(df.iloc[0].to_dict())

