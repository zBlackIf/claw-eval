# -*- coding: utf-8 -*-
"""期货消息面汇总系统 - 消息解析器"""
import re
from datetime import date, datetime
from typing import Optional, Tuple

from config import CATEGORY_MAPPING, VARIETIES


class MessageParser:
    def __init__(self):
        self.varieties = VARIETIES
        self.category_mapping = CATEGORY_MAPPING

    def clean_content(self, content: str) -> str:
        """清理消息内容，去除多余空白和特殊字符"""
        content = re.sub(r'\s+', ' ', content).strip()
        content = re.sub(r'[​‌‍﻿]', '', content)
        return content

    def extract_variety(self, content: str) -> Optional[str]:
        """从消息中提取品种"""
        for variety in self.varieties:
            if variety in content:
                return variety
        return None

    def extract_category(self, content: str) -> str:
        """提取分类信息"""
        for category, keywords in self.category_mapping.items():
            for keyword in keywords:
                if keyword in content:
                    return category
        return "其他"

    def extract_date(self, content: str) -> date:
        """从内容中提取日期，默认返回今天"""
        patterns = [
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})',
            r'(\d{1,2})[-/月](\d{1,2})[日号]',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        return date(int(groups[0]), int(groups[1]), int(groups[2]))
                    elif len(groups) == 2:
                        today = date.today()
                        return date(today.year, int(groups[0]), int(groups[1]))
                except ValueError:
                    pass
        return date.today()

    def parse_message(self, content: str, raw_content: Optional[str] = None) -> Tuple[Optional[str], str, date, str]:
        """
        解析消息
        返回: (品种, 分类, 日期, 清理后的内容)
        """
        cleaned_content = self.clean_content(content)
        variety = self.extract_variety(cleaned_content)
        category = self.extract_category(cleaned_content)
        msg_date = self.extract_date(cleaned_content)

        return variety, category, msg_date, cleaned_content

    def parse_and_store(self, content: str, raw_content: Optional[str] = None,
                        variety: Optional[str] = None,
                        category: Optional[str] = None) -> dict:
        """解析消息并返回结构化结果"""
        cleaned_content = self.clean_content(content)

        if not variety:
            variety = self.extract_variety(cleaned_content) or "未分类"

        if not category:
            category = self.extract_category(cleaned_content)

        msg_date = self.extract_date(cleaned_content)

        return {
            "variety": variety,
            "category": category,
            "date": msg_date.isoformat(),
            "content": cleaned_content,
            "raw_content": raw_content or content
        }


# 全局解析器实例
parser = MessageParser()
