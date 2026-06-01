"""
分数诊断器 - 自动扫描丢分点，计算预计提分幅度
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from config import settings
from core.douyin_lai_ke.client import DouyinLaiKeClient
from core.douyin_lai_ke.data import DataFetcher


@dataclass
class LossPoint:
    """丢分点"""
    category: str          # 分类：经营分/服务分
    factor: str            # 影响因素
    current_value: float   # 当前值
    target_value: float    # 目标值
    lost_score: float      # 丢分多少
    priority: int          # 优先级 1-5，1最高
    industry_specific: bool = False  # 是否行业特定

    def get_potential_gain(self) -> float:
        """可挽回分数"""
        return self.lost_score

    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "factor": self.factor,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "lost_score": self.lost_score,
            "priority": self.priority,
            "industry_specific": self.industry_specific
        }


@dataclass
class DiagnosticReport:
    """诊断报告"""
    business_id: str
    industry: str
    business_score: float
    service_score: float
    max_possible_business: float = 100.0
    max_possible_service: float = 100.0
    loss_points: List[LossPoint] = field(default_factory=list)
    industry_rank: Optional[int] = None
    industry_total: Optional[int] = None
    generated_at: datetime = field(default_factory=datetime.now)

    def get_total_lost_business(self) -> float:
        """经营分总丢分"""
        return sum(lp.lost_score for lp in self.loss_points if lp.category == "business")

    def get_total_lost_service(self) -> float:
        """服务分总丢分"""
        return sum(lp.lost_score for lp in self.loss_points if lp.category == "service")

    def get_expected_business_after(self) -> float:
        """优化后预期经营分"""
        return min(self.business_score + self.get_total_lost_business(), 100.0)

    def get_expected_service_after(self) -> float:
        """优化后预期服务分"""
        return min(self.service_score + self.get_total_lost_service(), 100.0)

    def get_sorted_loss_points(self) -> List[LossPoint]:
        """按优先级排序"""
        return sorted(self.loss_points, key=lambda x: x.priority)

    def to_markdown(self) -> str:
        """生成Markdown诊断报告"""
        lines = []
        lines.append(f"# 经营分/服务分诊断报告\n")
        lines.append(f"商家ID: `{self.business_id}`\n")
        lines.append(f"行业: `{self.industry}`\n")
        lines.append(f"生成时间: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 当前得分
        lines.append("## 当前得分\n")
        lines.append(f"- 经营分: **{self.business_score:.1f}** / 100")
        if self.industry_rank and self.industry_total:
            lines.append(f"  行业排名: {self.industry_rank} / {self.industry_total} (前 {self.industry_rank * 100 // self.industry_total}%)")
        lines.append(f"- 服务分: **{self.service_score:.1f}** / 100\n")

        # 预期提升
        lines.append("## 预期提升空间\n")
        lines.append(f"- 经营分可提升: **+{self.get_total_lost_business():.1f}** 分 → 预期 {self.get_expected_business_after():.1f} 分")
        lines.append(f"- 服务分可提升: **+{self.get_total_lost_service():.1f}** 分 → 预期 {self.get_expected_service_after():.1f} 分\n")

        # 丢分明细
        if self.loss_points:
            lines.append("## 丢分明细（按优先级）\n")
            lines.append("| 优先级 | 分类 | 影响因素 | 当前值 | 目标值 | 可提分 |")
            lines.append("|--------|------|----------|--------|--------|--------|")
            for lp in self.get_sorted_loss_points():
                cat_cn = "经营分" if lp.category == "business" else "服务分"
                lines.append(f"| {lp.priority} | {cat_cn} | {lp.factor} | {lp.current_value:.1f} | {lp.target_value:.1f} | +{lp.lost_score:.1f} |")
            lines.append("")

        lines.append("\n## 优化建议\n")
        lines.append("按照优先级依次完成优化，建议每周检查一次分数变化。")

        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps({
            "business_id": self.business_id,
            "industry": self.industry,
            "business_score": self.business_score,
            "service_score": self.service_score,
            "total_lost_business": self.get_total_lost_business(),
            "total_lost_service": self.get_total_lost_service(),
            "expected_business_after": self.get_expected_business_after(),
            "expected_service_after": self.get_expected_service_after(),
            "industry_rank": self.industry_rank,
            "industry_total": self.industry_total,
            "loss_points": [lp.to_dict() for lp in self.loss_points],
            "generated_at": self.generated_at.isoformat()
        }, ensure_ascii=False, indent=2)


class ScoreDiagnoser:
    """分数诊断器 - 扫描抖音来客后台，诊断丢分点"""

    # 标准评分项配置
    # 经营分各项权重（抖音来客标准）
    BUSINESS_WEIGHTS = {
        "门店信息完整度": 15,
        "商品信息完整度": 20,
        "团购覆盖率": 15,
        "内容发布活跃度": 10,
        "核销履约率": 15,
        "用户评价质量": 15,
        "活动参与度": 10,
    }

    # 服务分各项权重
    SERVICE_WEIGHTS = {
        "消息平均响应时长": 25,
        "平均退款处理时长": 25,
        "差评率": 20,
        "投诉率": 15,
        "预约及时处理率": 15,
    }

    # 及格线标准
    PASSING_THRESHOLD = {
        "门店信息完整度": 90,
        "商品信息完整度": 85,
        "团购覆盖率": 80,
        "内容发布活跃度": 70,
        "核销履约率": 80,
        "用户评价质量": 75,
        "活动参与度": 60,
        "消息平均响应时长": 80,  # 低于80需要优化（响应越快分越高）
        "平均退款处理时长": 80,
        "差评率": 75,
        "投诉率": 80,
        "预约及时处理率": 85,
    }

    def __init__(self):
        self.client = DouyinLaiKeClient()
        self.fetcher = DataFetcher()

    def diagnose(
        self,
        business_id: str,
        industry: str,
        raw_data: Optional[Dict] = None
    ) -> DiagnosticReport:
        """
        执行诊断
        :param business_id: 商家ID
        :param industry: 行业
        :param raw_data: 如果已有数据可以传入，否则从API拉取
        """
        # 获取数据
        if raw_data is None:
            raw_data = self.fetcher.fetch_business_full_data(business_id)

        # 提取当前得分
        current_business = self._extract_business_score(raw_data)
        current_service = self._extract_service_score(raw_data)

        # 创建报告
        report = DiagnosticReport(
            business_id=business_id,
            industry=industry,
            business_score=current_business,
            service_score=current_service
        )

        # 获取行业排名
        rank_info = self._extract_rank_info(raw_data)
        if rank_info:
            report.industry_rank = rank_info.get("rank")
            report.industry_total = rank_info.get("total")

        # 诊断经营分丢分点
        business_factors = self._extract_business_factors(raw_data)
        for factor, current in business_factors.items():
            threshold = self._get_industry_threshold(industry, factor, "business")
            if current < threshold:
                weight = self.BUSINESS_WEIGHTS[factor]
                # 计算丢分 = (threshold - current) / 100 * weight
                lost = ((threshold - current) / 100) * weight
                priority = self._calculate_priority(factor, lost, industry)
                report.loss_points.append(LossPoint(
                    category="business",
                    factor=factor,
                    current_value=current,
                    target_value=threshold,
                    lost_score=lost,
                    priority=priority,
                    industry_specific=self._is_industry_specific(factor, industry)
                ))

        # 诊断服务分丢分点
        service_factors = self._extract_service_factors(raw_data)
        for factor, current in service_factors.items():
            threshold = self._get_industry_threshold(industry, factor, "service")
            if current < threshold:
                weight = self.SERVICE_WEIGHTS[factor]
                lost = ((threshold - current) / 100) * weight
                priority = self._calculate_priority(factor, lost, industry)
                report.loss_points.append(LossPoint(
                    category="service",
                    factor=factor,
                    current_value=current,
                    target_value=threshold,
                    lost_score=lost,
                    priority=priority,
                    industry_specific=self._is_industry_specific(factor, industry)
                ))

        return report

    def _extract_business_score(self, data: Dict) -> float:
        """从原始数据提取经营分"""
        # 实际从API返回提取
        # 这里兼容模拟数据结构
        if "base" in data:
            return data["base"].get("business_score", 65.0)
        return data.get("business_score", 65.0)

    def _extract_service_score(self, data: Dict) -> float:
        """从原始数据提取服务分"""
        if "base" in data:
            return data["base"].get("service_score", 60.0)
        return data.get("service_score", 60.0)

    def _extract_rank_info(self, data: Dict) -> Optional[Dict]:
        """提取行业排名信息"""
        if "base" in data:
            return data["base"].get("rank_info")
        return data.get("rank_info")

    def _extract_business_factors(self, data: Dict) -> Dict[str, float]:
        """提取经营分各因子得分"""
        result = {}
        details = None
        if "base" in data:
            details = data["base"].get("factor_details", {})
        elif "factor_details" in data:
            details = data["factor_details"]

        for factor in self.BUSINESS_WEIGHTS:
            result[factor] = details.get(factor, 50.0)
        return result

    def _extract_service_factors(self, data: Dict) -> Dict[str, float]:
        """提取服务分各因子得分"""
        result = {}
        details = None
        if "base" in data:
            details = data["base"].get("service_factor_details", {})
        elif "service_factor_details" in data:
            details = data["service_factor_details"]

        for factor in self.SERVICE_WEIGHTS:
            result[factor] = details.get(factor, 50.0)
        return result

    def _get_industry_threshold(
        self,
        industry: str,
        factor: str,
        category: str
    ) -> float:
        """获取行业特定及格线"""
        # 行业特定调整
        # 餐饮对商品丰富度要求更高
        if industry == "catering" and factor == "商品信息完整度":
            return 90
        # 美业对预约处理要求更高
        if industry == "beauty" and factor == "预约及时处理率":
            return 90
        # 酒店对退款要求更高
        if industry == "hotel" and factor == "平均退款处理时长":
            return 85

        # 默认标准
        return self.PASSING_THRESHOLD.get(factor, 70)

    def _calculate_priority(self, factor: str, lost_score: float, industry: str) -> int:
        """计算优先级，1最高，5最低"""
        # 丢分越多优先级越高
        if lost_score >= 8:
            base_priority = 1
        elif lost_score >= 5:
            base_priority = 2
        elif lost_score >= 3:
            base_priority = 3
        elif lost_score >= 1:
            base_priority = 4
        else:
            base_priority = 5

        # 行业特定优先级调整
        # 服务分相关永远优先
        if factor in ["消息平均响应时长", "平均退款处理时长", "差评率", "投诉率"]:
            base_priority = max(1, base_priority - 1)

        # 美业 - 预约处理优先
        if industry == "beauty" and factor == "预约及时处理率":
            base_priority = max(1, base_priority - 1)

        # 酒店 - 退款优先
        if industry == "hotel" and factor == "平均退款处理时长":
            base_priority = max(1, base_priority - 1)

        return base_priority

    def _is_industry_specific(self, factor: str, industry: str) -> bool:
        """是否行业特定要求"""
        industry_specific_factors = {
            "catering": ["商品信息完整度", "团购覆盖率"],
            "beauty": ["预约及时处理率"],
            "hotel": ["平均退款处理时长", "投诉率"],
            "fitness": ["核销履约率"],
        }
        return factor in industry_specific_factors.get(industry, [])
