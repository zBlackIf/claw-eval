"""
本地生活商家自助投流 - 投流策略模块
负责生成不同场景下的投流策略方案
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json
from datetime import datetime, timedelta


class FlowStrategyType(Enum):
    """投流策略类型"""
    CITY_WIDE = "同城门店定向"
    HOT_PRIORITY = "爆款优先投流"
    COLD_START = "冷启动投流"


class CrowdLabel(Enum):
    """八大人群标签"""
    FOOD_LOVER = "美食爱好者"
    BEAUTY_CONSUMER = "美妆消费者"
    FITNESS_FAN = "健身爱好者"
    LIFESTYLE = "品质生活人群"
    FAMILY = "家庭主妇/宝爸宝妈"
    YOUTH = "年轻潮流人群"
    BUSINESS = "商务人士"
    SENIOR = "银发健康人群"


@dataclass
class CrowdTarget:
    """人群定向配置"""
    radius_km: int = 5  # 半径范围 3-5公里
    city_only: bool = True  # 仅限本地生活人群
    selected_labels: List[str] = field(default_factory=list)  # 选中的人群标签
    gender: Optional[str] = None  # 性别定向
    age_range: Optional[str] = None  # 年龄范围

    def to_dict(self) -> Dict:
        return {
            "radius_km": self.radius_km,
            "city_only": self.city_only,
            "selected_labels": self.selected_labels,
            "gender": self.gender,
            "age_range": self.age_range
        }


@dataclass
class BudgetConfig:
    """预算配置"""
    daily_budget: float = 0.0  # 日预算，0表示不限制
    per_plan_budget: float = 0.0  # 单条计划预算
    max_cost_per_click: float = 0.0  # 单次点击最高出价
    max_cost_per_entry: float = 0.0  # 单次进店最高出价
    stop_when_exceed: bool = True  # 超支立即停止

    def to_dict(self) -> Dict:
        return {
            "daily_budget": self.daily_budget,
            "per_plan_budget": self.per_plan_budget,
            "max_cost_per_click": self.max_cost_per_click,
            "max_cost_per_entry": self.max_cost_per_entry,
            "stop_when_exceed": self.stop_when_exceed
        }


@dataclass
class VideoInfo:
    """视频信息用于投流分析"""
    video_id: str
    title: str
    publish_days: int  # 发布天数
    trend_percent: float  # 涨幅百分比
    complete_rate: float  # 完播率
    play_count: int  # 播放量
    click_to_store: int  # 进店量
    conversion: float  # 转化率


@dataclass
class FlowPlan:
    """投流计划"""
    plan_name: str
    strategy_type: str
    video_id: str
    video_title: str
    crowd_target: CrowdTarget
    budget: BudgetConfig
    suggested_bid: float
    reason: str  # 推荐理由
    estimated_effect: str  # 预期效果
    need_audit: bool = True  # 需要审核（强制审核机制）
    status: str = "pending_audit"  # pending_audit -> approved -> running -> stopped
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "plan_name": self.plan_name,
            "strategy_type": self.strategy_type,
            "video_id": self.video_id,
            "video_title": self.video_title,
            "crowd_target": self.crowd_target.to_dict(),
            "budget": self.budget.to_dict(),
            "suggested_bid": self.suggested_bid,
            "reason": self.reason,
            "estimated_effect": self.estimated_effect,
            "need_audit": self.need_audit,
            "status": self.status,
            "created_at": self.created_at
        }


class FlowStrategyGenerator:
    """投流策略生成器"""

    def __init__(self):
        self.industry_crowd_map = {
            "catering": [CrowdLabel.FOOD_LOVER, CrowdLabel.LIFESTYLE, CrowdLabel.YOUTH],
            "beauty": [CrowdLabel.BEAUTY_CONSUMER, CrowdLabel.LIFESTYLE, CrowdLabel.YOUTH],
            "fitness": [CrowdLabel.FITNESS_FAN, CrowdLabel.YOUTH, CrowdLabel.LIFESTYLE],
            "retail": [CrowdLabel.FAMILY, CrowdLabel.LIFESTYLE, CrowdLabel.YOUTH],
            "hotel": [CrowdLabel.LIFESTYLE, CrowdLabel.BUSINESS, CrowdLabel.YOUTH],
            "entertainment": [CrowdLabel.YOUTH, CrowdLabel.LIFESTYLE, CrowdLabel.FAMILY],
            "education": [CrowdLabel.FAMILY, CrowdLabel.BUSINESS, CrowdLabel.YOUTH],
            "health": [CrowdLabel.SENIOR, CrowdLabel.HEALTH, CrowdLabel.FAMILY],
        }

    def generate_city_target_strategy(
        self,
        store_lat: float,
        store_lng: float,
        industry: str,
        daily_budget: float,
        radius: int = 5
    ) -> FlowPlan:
        """
        同城门店定向策略
        - 半径3-5公里
        - 本地生活人群
        - 八大人群标签精准投放
        """
        if radius not in [3, 5]:
            radius = 5

        # 获取行业推荐人群标签
        recommended_crowds = self.industry_crowd_map.get(
            industry,
            [CrowdLabel.LIFESTYLE, CrowdLabel.YOUTH, CrowdLabel.FAMILY]
        )
        crowd_labels = [c.value for c in recommended_crowds]

        crowd = CrowdTarget(
            radius_km=radius,
            city_only=True,
            selected_labels=crowd_labels
        )

        budget = BudgetConfig(
            daily_budget=daily_budget,
            per_plan_budget=daily_budget,
            stop_when_exceed=True
        )

        # 建议出价：本地生活一般 0.5-2元之间
        suggested_bid = round(daily_budget / 100, 2)
        if suggested_bid < 0.5:
            suggested_bid = 0.5
        if suggested_bid > 2.0:
            suggested_bid = 2.0

        return FlowPlan(
            plan_name=f"同城{radius}公里门店定向-{industry}",
            strategy_type=FlowStrategyType.CITY_WIDE.value,
            video_id="",
            video_title="",
            crowd_target=crowd,
            budget=budget,
            suggested_bid=suggested_bid,
            reason=f"针对{industry}行业，半径{radius}公里内精准触达{', '.join(crowd_labels)}",
            estimated_effect=f"预计日曝光 {(int(daily_budget / suggested_bid) * 3) if suggested_bid > 0 else 0} 次，进店率 3-8%",
            need_audit=True
        )

    def generate_hot_priority_strategy(
        self,
        videos: List[VideoInfo],
        daily_budget: float,
        industry: str
    ) -> List[FlowPlan]:
        """
        爆款优先投流策略
        - 只给7天内上升爆款
        - 高完播视频自动生成投流建议
        """
        plans = []
        # 筛选：7天内发布、趋势上涨、完播率高于行业均值
        hot_videos = [
            v for v in videos
            if v.publish_days <= 7 and v.trend_percent > 10 and v.complete_rate > 0.2
        ]

        # 按热度排序，分配预算
        total_budget_allocated = 0.0
        for i, video in enumerate(hot_videos[:5]):  # 最多选5个爆款
            # 爆款分配更多预算
            if i == 0:
                # top1 分配 40% 预算
                plan_budget = daily_budget * 0.4
            elif i == 1:
                plan_budget = daily_budget * 0.3
            elif i == 2:
                plan_budget = daily_budget * 0.2
            else:
                plan_budget = daily_budget * 0.1

            # 检查总预算不超
            if total_budget_allocated + plan_budget > daily_budget:
                plan_budget = daily_budget - total_budget_allocated

            if plan_budget <= 0:
                continue

            total_budget_allocated += plan_budget

            # 获取推荐人群标签
            recommended_crowds = self.industry_crowd_map.get(
                industry,
                [CrowdLabel.LIFESTYLE, CrowdLabel.YOUTH, CrowdLabel.FAMILY]
            )
            crowd_labels = [c.value for c in recommended_crowds]

            crowd = CrowdTarget(
                radius_km=5,
                city_only=True,
                selected_labels=crowd_labels
            )

            budget = BudgetConfig(
                daily_budget=0,  # 由总日预算控制
                per_plan_budget=plan_budget,
                stop_when_exceed=True
            )

            # 爆款可以出价略高，获取更多流量
            suggested_bid = 0.8 if video.complete_rate > 0.3 else 0.5

            reason = (
                f"近{video.publish_days}天发布，涨幅{video.trend_percent:.1f}%，"
                f"完播率{video.complete_rate*100:.1f}%，自然表现优秀，放大投流放大效果"
            )

            estimated_effect = (
                f"基于自然流量表现，投流后预计播放提升 {(video.trend_percent * 2):.0f}%，"
                f"预估进店 {int(plan_budget / 2)} 人"
            )

            plan = FlowPlan(
                plan_name=f"爆款放大-{video.title[:20]}",
                strategy_type=FlowStrategyType.HOT_PRIORITY.value,
                video_id=video.video_id,
                video_title=video.title,
                crowd_target=crowd,
                budget=budget,
                suggested_bid=suggested_bid,
                reason=reason,
                estimated_effect=estimated_effect,
                need_audit=True
            )
            plans.append(plan)

        return plans

    def generate_cold_start_strategy(
        self,
        industry: str,
        store_address: str,
        daily_budget: float = 50.0
    ) -> FlowPlan:
        """
        冷启动投流策略
        - 新号0粉起号小额测试策略
        - 冲同城榜单
        """
        # 冷启动人群：同城全量覆盖+行业标签
        recommended_crowds = self.industry_crowd_map.get(
            industry,
            [CrowdLabel.LIFESTYLE, CrowdLabel.YOUTH, CrowdLabel.FAMILY]
        )
        crowd_labels = [c.value for c in recommended_crowds]

        crowd = CrowdTarget(
            radius_km=5,
            city_only=True,
            selected_labels=crowd_labels
        )

        # 小额测试预算
        budget = BudgetConfig(
            daily_budget=daily_budget,
            per_plan_budget=daily_budget,
            max_cost_per_entry=3.0,  # 单次进店不超过3元
            stop_when_exceed=True
        )

        # 冷启动低价测试
        suggested_bid = 0.3

        plan = FlowPlan(
            plan_name="新号冷启动-同城榜单冲量",
            strategy_type=FlowStrategyType.COLD_START.value,
            video_id="",
            video_title="新账号多条视频轮测",
            crowd_target=crowd,
            budget=budget,
            suggested_bid=suggested_bid,
            reason=f"新号0粉起号，小额测试快速打标签，冲击同城榜单，获取自然流量加权",
            estimated_effect=f"日预算{daily_budget}元，预计测试出1-2条潜力视频，为后续放大做准备",
            need_audit=True
        )

        return plan

    def export_plans_json(self, plans: List[FlowPlan], output_path: str) -> str:
        """导出投流计划为JSON文件"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_plans": len(plans),
            "plans": [p.to_dict() for p in plans],
            "notice": "所有投流计划需人工审核确认后才可执行，系统不自动扣费，仅提供方案和跳转指引"
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path


class BudgetController:
    """预算控制器 - 防超支"""

    def __init__(self):
        self.daily_consumed: Dict[str, float] = {}  # date -> consumed
        self.plan_consumed: Dict[str, float] = {}  # plan_id -> consumed

    def check_budget_available(
        self,
        plan_id: str,
        daily_budget: float,
        per_plan_budget: float
    ) -> bool:
        """检查预算是否可用"""
        today = datetime.now().strftime("%Y-%m-%d")

        # 检查日预算
        daily_used = self.daily_consumed.get(today, 0.0)
        if daily_budget > 0 and daily_used >= daily_budget:
            return False

        # 检查单计划预算
        plan_used = self.plan_consumed.get(plan_id, 0.0)
        if per_plan_budget > 0 and plan_used >= per_plan_budget:
            return False

        return True

    def record_consumption(self, plan_id: str, amount: float):
        """记录消耗"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_consumed[today] = self.daily_consumed.get(today, 0.0) + amount
        self.plan_consumed[plan_id] = self.plan_consumed.get(plan_id, 0.0) + amount

    def get_daily_consumed(self) -> float:
        """获取今日已消耗"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.daily_consumed.get(today, 0.0)
