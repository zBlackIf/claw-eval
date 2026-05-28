"""
行业榜单规则适配器
- 餐饮：热销榜、人气榜、种草榜
- 美业：热销榜、服务榜、好评榜
- 休闲/酒店/健身/汽修/生活服务：自动匹配对应榜单规则
"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class IndustryRankConfig:
    """行业榜单配置"""
    industry_name: str
    available_categories: List[str]
    default_category: str
    weight_sales: float  # 销量权重
    weight_verification: float  # 核销权重
    weight_review: float  # 评价权重
    weight_content: float  # 内容权重
    weight_live: float  # 直播权重
    weight_score: float  # 评分权重

    def get_default_threshold(self) -> Dict:
        """获取默认上榜门槛（按行业经验）"""
        base = {
            'monthly_sales': int(500 * self.weight_sales * 2),
            'monthly_verification': int(300 * self.weight_verification * 2),
            'monthly_live_hours': 30 * self.weight_live,
            'monthly_videos': 30 * self.weight_content,
            'total_reviews': int(100 * self.weight_review * 2),
            'min_rating': 4.2,
        }
        return base

    def daily_growth_factor(self) -> Dict:
        """每日合理增长目标"""
        return {
            'sales': 10 if self.weight_sales > 0.3 else 5,
            'videos': 1 if self.weight_content > 0.2 else 0.5,
            'live_hours': 2 if self.weight_live > 0.2 else 1,
        }


# 各行业配置
INDUSTRY_CONFIGS = {
    # 餐饮
    'catering': IndustryRankConfig(
        industry_name='餐饮',
        available_categories=['热销榜', '人气榜', '种草榜', '好评榜'],
        default_category='热销榜',
        weight_sales=0.35,
        weight_verification=0.25,
        weight_review=0.10,
        weight_content=0.10,
        weight_live=0.10,
        weight_score=0.10,
    ),
    # 美业
    'beauty': IndustryRankConfig(
        industry_name='美业',
        available_categories=['热销榜', '服务榜', '好评榜', '种草榜'],
        default_category='好评榜',
        weight_sales=0.20,
        weight_verification=0.20,
        weight_review=0.25,
        weight_content=0.10,
        weight_live=0.05,
        weight_score=0.20,
    ),
    # 健身
    'fitness': IndustryRankConfig(
        industry_name='健身',
        available_categories=['热销榜', '人气榜', '好评榜'],
        default_category='人气榜',
        weight_sales=0.25,
        weight_verification=0.25,
        weight_review=0.15,
        weight_content=0.10,
        weight_live=0.10,
        weight_score=0.15,
    ),
    # 酒店
    'hotel': IndustryRankConfig(
        industry_name='酒店',
        available_categories=['热销榜', '人气榜', '好评榜'],
        default_category='热销榜',
        weight_sales=0.30,
        weight_verification=0.30,
        weight_review=0.15,
        weight_content=0.05,
        weight_live=0.05,
        weight_score=0.15,
    ),
    # 休闲娱乐
    'entertainment': IndustryRankConfig(
        industry_name='休闲娱乐',
        available_categories=['热销榜', '人气榜', '种草榜'],
        default_category='人气榜',
        weight_sales=0.25,
        weight_verification=0.20,
        weight_review=0.10,
        weight_content=0.15,
        weight_live=0.15,
        weight_score=0.15,
    ),
    # 零售
    'retail': IndustryRankConfig(
        industry_name='零售',
        available_categories=['热销榜', '人气榜'],
        default_category='热销榜',
        weight_sales=0.40,
        weight_verification=0.25,
        weight_review=0.10,
        weight_content=0.10,
        weight_live=0.05,
        weight_score=0.10,
    ),
    # 教育培训
    'education': IndustryRankConfig(
        industry_name='教育培训',
        available_categories=['人气榜', '好评榜', '服务榜'],
        default_category='好评榜',
        weight_sales=0.15,
        weight_verification=0.15,
        weight_review=0.25,
        weight_content=0.15,
        weight_live=0.10,
        weight_score=0.20,
    ),
    # 生活服务（汽修/美容等）
    'life_service': IndustryRankConfig(
        industry_name='生活服务',
        available_categories=['服务榜', '好评榜', '人气榜'],
        default_category='服务榜',
        weight_sales=0.15,
        weight_verification=0.20,
        weight_review=0.25,
        weight_content=0.10,
        weight_live=0.05,
        weight_score=0.25,
    ),
    # 健康养生
    'health': IndustryRankConfig(
        industry_name='健康养生',
        available_categories=['热销榜', '好评榜', '服务榜'],
        default_category='好评榜',
        weight_sales=0.20,
        weight_verification=0.20,
        weight_review=0.20,
        weight_content=0.10,
        weight_live=0.10,
        weight_score=0.20,
    ),
}


def get_industry_adapter(industry_code: str) -> IndustryRankConfig:
    """获取行业适配器"""
    # 直接匹配
    if industry_code in INDUSTRY_CONFIGS:
        return INDUSTRY_CONFIGS[industry_code]

    # 模糊匹配
    if '餐饮' in industry_code or 'cater' in industry_code.lower():
        return INDUSTRY_CONFIGS['catering']
    if '美' in industry_code or 'beauty' in industry_code.lower():
        return INDUSTRY_CONFIGS['beauty']
    if '健身' in industry_code or 'fit' in industry_code.lower():
        return INDUSTRY_CONFIGS['fitness']
    if '酒店' in industry_code or 'hotel' in industry_code.lower():
        return INDUSTRY_CONFIGS['hotel']
    if '休闲' in industry_code or '娱乐' in industry_code or 'entertain' in industry_code.lower():
        return INDUSTRY_CONFIGS['entertainment']
    if '教育' in industry_code:
        return INDUSTRY_CONFIGS['education']
    if '健康' in industry_code or '养生' in industry_code:
        return INDUSTRY_CONFIGS['health']

    # 默认返回生活服务配置
    return INDUSTRY_CONFIGS['life_service']
