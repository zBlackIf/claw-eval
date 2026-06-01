"""
行业适配层 - 全行业自适应评分规则、套餐结构、亮标要求
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class IndustryRules:
    """行业特定规则"""
    industry_name: str
    industry_code: str
    # 评分重点
    score_focus: List[str] = field(default_factory=list)
    # 必须亮标项
    required_badges: List[str] = field(default_factory=list)
    # 推荐商品结构（不同SKU数量占比）
    recommended_product_structure: Dict[str, int] = field(default_factory=dict)
    # 佣金推荐范围
    commission_range: tuple[float, float] = (5, 20)
    # 内容发布频率要求
    content_frequency: int = 3  # 每周几条
    # 服务重点优化项
    service_focus: List[str] = field(default_factory=list)
    # 经营分目标（满分前不同行业要求不同）
    target_business_score: float = 95.0
    target_service_score: float = 95.0
    # 自定义装修要求
    decoration_requirements: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "industry_name": self.industry_name,
            "industry_code": self.industry_code,
            "score_focus": self.score_focus,
            "required_badges": self.required_badges,
            "recommended_product_structure": self.recommended_product_structure,
            "commission_range": self.commission_range,
            "content_frequency": self.content_frequency,
            "service_focus": self.service_focus,
            "target_business_score": self.target_business_score,
            "target_service_score": self.target_service_score,
            "decoration_requirements": self.decoration_requirements,
        }


# 预定义行业规则
PREDEFINED_RULES = {
    "catering": IndustryRules(
        industry_name="餐饮",
        industry_code="catering",
        score_focus=["商品信息完整度", "团购覆盖率", "用户评价质量"],
        required_badges=["免费WiFi", "停车位", "卫生间", "预约"],
        recommended_product_structure={
            "引流爆款": 1,
            "爆款套餐": 2,
            "单人餐": 2,
            "双人餐": 2,
            "多人餐": 1,
            "特色菜单品": 3,
            "代金券": 2
        },
        commission_range=(8, 15),
        content_frequency=4,
        service_focus=["消息响应速度", "退款处理", "差评回复"],
        target_business_score=98.0,
        target_service_score=95.0,
        decoration_requirements={
            "门店门头": 1,
            "环境照片": 5,
            "菜品展示": 10,
            "后厨环境": 1,
            "服务员/团队": 1
        }
    ),
    "beauty": IndustryRules(
        industry_name="美业",
        industry_code="beauty",
        score_focus=["门店信息完整度", "预约及时处理率", "用户评价质量"],
        required_badges=["免费停车", "免费WiFi", "预约免费", "到店礼"],
        recommended_product_structure={
            "体验引流": 1,
            "爆款项目": 2,
            "单人套餐": 2,
            "多人同行": 1,
            "会员卡": 1,
            "单品项目": 3
        },
        commission_range=(10, 20),
        content_frequency=3,
        service_focus=["预约处理", "消息响应速度", "差评处理"],
        target_business_score=95.0,
        target_service_score=98.0,
        decoration_requirements={
            "门店门头": 1,
            "环境照片": 6,
            "技师展示": 4,
            "项目效果对比": 5,
            "等候区": 1
        }
    ),
    "hotel": IndustryRules(
        industry_name="酒店住宿",
        industry_code="hotel",
        score_focus=["门店信息完整度", "核销履约率", "退款处理"],
        required_badges=["免费停车", "免费WiFi", "早餐", "电梯", "行李寄存"],
        recommended_product_structure={
            "特惠房型": 1,
            "标准房型": 2,
            "高级房型": 2,
            "套房": 1,
            "套餐": 2,
            "连住优惠": 1
        },
        commission_range=(5, 12),
        content_frequency=2,
        service_focus=["退款处理", "投诉处理", "预约响应"],
        target_business_score=95.0,
        target_service_score=98.0,
        decoration_requirements={
            "门店门头": 1,
            "大堂": 2,
            "客房": 6,
            "设施": 3,
            "周边环境": 2
        }
    ),
    "fitness": IndustryRules(
        industry_name="健身",
        industry_code="fitness",
        score_focus=["核销履约率", "用户评价质量", "内容活跃度"],
        required_badges=["免费停车", " locker", "淋浴", "WiFi"],
        recommended_product_structure={
            "体验课": 1,
            "私教课": 3,
            "月卡": 1,
            "季卡": 1,
            "年卡": 1,
            "团课": 2
        },
        commission_range=(8, 18),
        content_frequency=3,
        service_focus=["预约处理", "消息响应"],
        target_business_score=95.0,
        target_service_score=95.0,
        decoration_requirements={
            "门头": 1,
            "前台": 1,
            "器械区": 4,
            "操房": 2,
            "淋浴区": 1,
            "教练展示": 4
        }
    ),
    "retail": IndustryRules(
        industry_name="零售",
        industry_code="retail",
        score_focus=["商品信息完整度", "团购覆盖率", "核销履约率"],
        required_badges=["免费WiFi", "退换货"],
        recommended_product_structure={
            "引流款": 2,
            "利润款": 5,
            "组合套餐": 2,
            "代金券": 2
        },
        commission_range=(5, 15),
        content_frequency=3,
        service_focus=["退款处理", "消息响应"],
        target_business_score=95.0,
        target_service_score=95.0,
        decoration_requirements={
            "门头": 1,
            "店内环境": 4,
            "商品展示": 8,
            "收银台": 1
        }
    ),
    "entertainment": IndustryRules(
        industry_name="休闲娱乐",
        industry_code="entertainment",
        score_focus=["门店信息完整度", "内容活跃度", "评价质量"],
        required_badges=["免费WiFi", "停车位", "包间"],
        recommended_product_structure={
            "引流体验": 1,
            "小时套餐": 2,
            "全天套餐": 1,
            "多人包场": 1,
            "饮品小吃": 3,
            "会员套餐": 1
        },
        commission_range=(8, 16),
        content_frequency=3,
        service_focus=["预约处理", "差评回复"],
        target_business_score=95.0,
        target_service_score=95.0,
        decoration_requirements={
            "门头": 1,
            "大厅": 2,
            "包间": 3,
            "设施设备": 4,
            "环境": 3
        }
    ),
    "education": IndustryRules(
        industry_name="教育培训",
        industry_code="education",
        score_focus=["门店信息完整度", "预约处理", "评价质量"],
        required_badges=["免费试听", "停车位", "WiFi"],
        recommended_product_structure={
            "体验课": 1,
            "短期班": 2,
            "长期班": 1,
            "一对一": 2,
            "小班课": 2,
            "集训营": 1
        },
        commission_range=(10, 20),
        content_frequency=2,
        service_focus=["预约处理", "消息响应", "退款处理"],
        target_business_score=95.0,
        target_service_score=98.0,
        decoration_requirements={
            "门头": 1,
            "前台": 1,
            "教室": 4,
            "师资展示": 4,
            "环境": 2
        }
    ),
    "health": IndustryRules(
        industry_name="健康养生",
        industry_code="health",
        score_focus=["门店信息完整度", "预约处理", "评价质量"],
        required_badges=["停车位", "WiFi", "独立包间"],
        recommended_product_structure={
            "体验项目": 1,
            "经典项目": 3,
            "套餐": 2,
            "疗程卡": 1,
            "次卡": 2,
            "会员卡": 1
        },
        commission_range=(10, 18),
        content_frequency=3,
        service_focus=["预约处理", "消息响应", "差评处理"],
        target_business_score=95.0,
        target_service_score=98.0,
        decoration_requirements={
            "门头": 1,
            "大厅": 1,
            "包间": 4,
            "技师展示": 3,
            "环境": 3
        }
    )
}


class IndustryAdapter:
    """行业适配器 - 根据商家行业自动加载对应规则"""

    def __init__(self):
        self.rules = PREDEFINED_RULES

    def get_rules(self, industry_code: str) -> IndustryRules:
        """获取行业规则"""
        if industry_code in self.rules:
            return self.rules[industry_code]
        # 返回默认规则
        return IndustryRules(
            industry_name="通用",
            industry_code=industry_code,
            score_focus=["门店信息完整度", "商品信息完整度"],
            required_badges=[],
            recommended_product_structure={
                "引流款": 1,
                "标准款": 3,
                "套餐": 2
            },
            commission_range=(5, 15),
            content_frequency=3,
            service_focus=["消息响应", "退款处理"],
            target_business_score=95.0,
            target_service_score=95.0,
            decoration_requirements={
                "门头": 1,
                "环境": 3,
                "产品展示": 5
            }
        )

    def detect_industry_from_data(self, business_data: Dict) -> str:
        """从商家数据自动识别行业"""
        # 如果数据中已有行业分类
        if "base" in business_data:
            category = business_data["base"].get("industry_category", "")
            code = self._map_category_to_code(category)
            if code in self.rules:
                return code

        # 通过商品结构推测
        product_categories = business_data.get("product_categories", [])
        category_keywords = {
            "catering": ["餐", "饭", "菜", "火锅", "烧烤", "甜品", "饮品"],
            "beauty": ["美容", "美发", "美甲", "美睫", "护肤", "SPA", "按摩"],
            "hotel": ["酒店", "住宿", "宾馆", "民宿"],
            "fitness": ["健身", "游泳", "瑜伽", "舞蹈"],
            "education": ["培训", "教育", "学习", "课程"],
            "health": ["养生", "足疗", "推拿", "中医"],
            "entertainment": ["KTV", "电影", "剧本杀", "密室", "桌游"],
            "retail": ["零售", "超市", "便利店", "百货"],
        }

        for code, keywords in category_keywords.items():
            for cat in product_categories:
                cat_lower = cat.lower()
                for kw in keywords:
                    if kw in cat_lower:
                        return code

        return "general"

    def _map_category_to_code(self, category: str) -> str:
        """映射分类名称到代码"""
        mapping = {
            "餐饮": "catering",
            "美食": "catering",
            "火锅": "catering",
            "美业": "beauty",
            "美容": "beauty",
            "美发": "beauty",
            "酒店": "hotel",
            "住宿": "hotel",
            "民宿": "hotel",
            "健身": "fitness",
            "瑜伽": "fitness",
            "零售": "retail",
            "超市": "retail",
            "休闲": "entertainment",
            "娱乐": "entertainment",
            "教育培训": "education",
            "培训": "education",
            "健康": "health",
            "养生": "health",
        }
        for key, code in mapping.items():
            if key in category:
                return code
        return "general"

    def get_required_photos_count(self, industry_code: str) -> Dict[str, int]:
        """获取行业要求的相册照片数量要求"""
        rules = self.get_rules(industry_code)
        return rules.decoration_requirements

    def get_target_score(self, industry_code: str) -> tuple[float, float]:
        """获取目标分数"""
        rules = self.get_rules(industry_code)
        return rules.target_business_score, rules.target_service_score

    def get_recommended_product_count(self, industry_code: str) -> int:
        """推荐最少商品数量"""
        rules = self.get_rules(industry_code)
        return sum(rules.recommended_product_structure.values())

    def get_expected_commission(self, industry_code: str) -> float:
        """获取推荐佣金比例"""
        rules = self.get_rules(industry_code)
        return (rules.commission_range[0] + rules.commission_range[1]) / 2
