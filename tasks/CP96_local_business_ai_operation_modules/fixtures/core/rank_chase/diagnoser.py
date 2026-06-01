"""
榜单诊断器 - 自动识别当前排名、上榜门槛、对标商家分析
"""
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from config import settings
from core.douyin_lai_ke.client import DouyinLaiKeClient
from core.analyzer.competitor import CompetitorAnalyzer


@dataclass
class RankInfo:
    """榜单信息"""
    city: str
    industry: str
    category: str  # 热销榜/人气榜/种草榜/好评榜/服务榜
    current_rank: Optional[int]
    threshold: Dict  # 上榜门槛 {销量: x, 核销: x, 评价: x, 直播时长: x}
    target_rank: int  # 目标上榜名次


@dataclass
class CompetitorInfo:
    """对标商家信息"""
    business_id: str
    name: str
    rank: int
    sales_volume: int  # 近30天销量
    verification_volume: int  # 近30天核销
    live_hours: float  # 月直播时长
    video_count: int  # 月发布短视频
    review_count: int  # 总评价数
    average_rating: float  # 平均分
    group_packages: List[Dict]  # 团单结构 [{name, price, sales}]


@dataclass
class FeasibilityReport:
    """冲榜可行性报告"""
    business_name: str
    current_rank: Optional[int]
    target_rank: int
    current_data: Dict  # 当前商家数据
    gap_analysis: Dict  # 缺口分析
    estimated_days: int  # 预计上榜天数
    required_sales: int  # 需要新增销量
    required_videos: int  # 需要新增视频
    required_live_hours: float  # 需要新增直播时长
    feasibility_score: int  # 可行性分数 0-100
    conclusion: str  # 结论建议


class RankDiagnoser:
    """榜单诊断器"""

    def __init__(self):
        self.client = DouyinLaiKeClient()
        self.competitor_analyzer = CompetitorAnalyzer()

    def diagnose(
        self,
        business_id: str,
        city: str,
        industry: str,
        target_rank: int = 10,
        custom_category: Optional[str] = None
    ) -> FeasibilityReport:
        """
        完整榜单诊断
        - 识别当前排名
        - 获取上榜门槛
        - 分析对标商家
        - 生成可行性报告
        """
        # 1. 获取商家基础数据
        business_data = self._get_business_current_data(business_id)
        business_name = business_data.get('name', 'Unknown')

        # 2. 获取行业适配的榜单类型
        from .industry_adapter import get_industry_adapter
        adapter = get_industry_adapter(industry)
        available_categories = adapter.get_available_rank_categories()

        if custom_category and custom_category in available_categories:
            rank_category = custom_category
        else:
            rank_category = adapter.get_default_rank_category()

        # 3. 获取当前榜单信息
        rank_info = self._get_rank_info(city, industry, rank_category, business_id)
        rank_info.target_rank = target_rank

        # 4. 分析对标商家（上榜前N名）
        competitors = self._analyze_competitors(city, industry, rank_category, target_rank)

        # 5. 计算上榜门槛（取当前上榜第N名的数据）
        threshold = self._calculate_threshold(competitors, target_rank, adapter)
        rank_info.threshold = threshold

        # 6. 分析缺口
        gap_analysis = self._calculate_gap(business_data, threshold, competitors)

        # 7. 计算预计上榜时间
        estimated = self._estimate_time_to_rank(
            business_data, gap_analysis, adapter.daily_growth_factor()
        )

        # 8. 生成可行性报告
        report = FeasibilityReport(
            business_name=business_name,
            current_rank=rank_info.current_rank,
            target_rank=target_rank,
            current_data=business_data,
            gap_analysis=gap_analysis,
            estimated_days=estimated['days'],
            required_sales=estimated['required_sales'],
            required_videos=estimated['required_videos'],
            required_live_hours=estimated['required_live_hours'],
            feasibility_score=self._calculate_feasibility_score(
                gap_analysis, estimated['days'], business_data
            ),
            conclusion=self._generate_conclusion(
                estimated['days'], estimated['feasibility_score']
            )
        )

        # 保存诊断结果
        self._save_diagnosis_result(business_id, report, rank_info, competitors)

        return report

    def _get_business_current_data(self, business_id: str) -> Dict:
        """获取商家当前数据"""
        # 优先从抖音来客API拉取
        if self.client.access_token or self.client.login():
            try:
                data = self.client.get_business_data(business_id)
                # 补充计算所需字段
                data['monthly_sales'] = data.get('monthly_sales', 0)
                data['monthly_verification'] = data.get('monthly_verification', 0)
                data['monthly_live_hours'] = data.get('monthly_live_hours', 0)
                data['monthly_videos'] = data.get('monthly_videos', 0)
                data['total_reviews'] = data.get('total_reviews', 0)
                data['average_rating'] = data.get('average_rating', 0.0)
                data['operation_score'] = data.get('operation_score', 0.0)
                data['service_score'] = data.get('service_score', 0.0)
                return data
            except Exception as e:
                print(f"API拉取失败，使用模拟数据: {e}")

        # 演示/模拟数据
        return {
            'name': 'Unknown Business',
            'monthly_sales': 0,
            'monthly_verification': 0,
            'monthly_live_hours': 0,
            'monthly_videos': 0,
            'total_reviews': 0,
            'average_rating': 4.0,
            'operation_score': 60.0,
            'service_score': 60.0,
        }

    def _get_rank_info(
        self,
        city: str,
        industry: str,
        category: str,
        business_id: str
    ) -> RankInfo:
        """获取当前榜单信息"""
        # 调用API获取榜单列表，查找当前商家排名
        # 这里简化处理，实际对接抖音榜单API
        current_rank = self._find_business_rank_in_list(city, industry, category, business_id)

        return RankInfo(
            city=city,
            industry=industry,
            category=category,
            current_rank=current_rank,
            threshold={},  # 后面计算
            target_rank=10
        )

    def _find_business_rank_in_list(
        self,
        city: str,
        industry: str,
        category: str,
        business_id: str
    ) -> Optional[int]:
        """在榜单列表中查找商家当前排名"""
        # 实际实现：调用榜单API获取全榜单，遍历查找
        # 模拟返回None（表示未上榜）
        return None

    def _analyze_competitors(
        self,
        city: str,
        industry: str,
        category: str,
        target_rank: int
    ) -> List[CompetitorInfo]:
        """分析对标商家（上榜前target_rank名）"""
        # 抓取前target_rank名商家数据
        competitors = self.competitor_analyzer.get_top_rank_competitors(
            city, industry, category, target_rank
        )

        results = []
        for comp in competitors:
            info = CompetitorInfo(
                business_id=comp.get('business_id', ''),
                name=comp.get('name', ''),
                rank=comp.get('rank', 0),
                sales_volume=comp.get('sales_volume', 0),
                verification_volume=comp.get('verification_volume', 0),
                live_hours=comp.get('live_hours', 0.0),
                video_count=comp.get('video_count', 0),
                review_count=comp.get('review_count', 0),
                average_rating=comp.get('average_rating', 4.5),
                group_packages=comp.get('group_packages', [])
            )
            results.append(info)

        return sorted(results, key=lambda x: x.rank)

    def _calculate_threshold(
        self,
        competitors: List[CompetitorInfo],
        target_rank: int,
        adapter
    ) -> Dict:
        """计算上榜门槛 - 取第target_rank名的数据作为门槛"""
        if not competitors:
            return adapter.get_default_threshold()

        # 如果已有足够多上榜商家，取第N名作为门槛
        if len(competitors) >= target_rank:
            threshold_comp = competitors[target_rank - 1]
        else:
            threshold_comp = competitors[-1]

        return {
            'monthly_sales': threshold_comp.sales_volume,
            'monthly_verification': threshold_comp.verification_volume,
            'monthly_live_hours': threshold_comp.live_hours,
            'monthly_videos': threshold_comp.video_count,
            'total_reviews': threshold_comp.review_count,
            'min_rating': threshold_comp.average_rating - 0.2,
        }

    def _calculate_gap(self, current: Dict, threshold: Dict, competitors: List[CompetitorInfo]) -> Dict:
        """计算与上榜门槛的缺口"""
        gap = {}
        for key, value in threshold.items():
            current_val = current.get(key.replace('monthly_', '').replace('total_', ''), 0)
            if isinstance(current_val, (int, float)):
                gap[key] = max(0, value - current_val)
            else:
                gap[key] = 0

        # 计算综合缺口分数
        total_gap = sum(v for k, v in gap.items() if isinstance(v, (int, float)))
        gap['total_gap_score'] = total_gap

        return gap

    def _estimate_time_to_rank(self, current: Dict, gap: Dict, daily_growth: Dict) -> Dict:
        """预计需要多少天才能上榜"""
        days_needed = 1

        # 按最大缺口维度计算时间
        if gap.get('required_sales', 0) > 0 and daily_growth.get('sales', 0) > 0:
            sales_days = int(gap['required_sales'] / daily_growth['sales']) + 1
            days_needed = max(days_needed, sales_days)

        if gap.get('required_videos', 0) > 0 and daily_growth.get('videos', 0) > 0:
            video_days = int(gap['required_videos'] / daily_growth['videos']) + 1
            days_needed = max(days_needed, video_days)

        if gap.get('required_live_hours', 0) > 0 and daily_growth.get('live_hours', 0) > 0:
            live_days = int(gap['required_live_hours'] / daily_growth['live_hours']) + 1
            days_needed = max(days_needed, live_days)

        return {
            'days': min(days_needed, 90),  # 最多90天
            'required_sales': int(gap.get('monthly_sales', 0)),
            'required_videos': int(gap.get('monthly_videos', 0)),
            'required_live_hours': round(gap.get('monthly_live_hours', 0), 1),
        }

    def _calculate_feasibility_score(
        self,
        gap: Dict,
        estimated_days: int,
        current_data: Dict
    ) -> int:
        """计算可行性分数"""
        score = 100

        # 时间越长分数越低
        if estimated_days > 60:
            score -= 30
        elif estimated_days > 30:
            score -= 15
        elif estimated_days > 14:
            score -= 5

        # 经营分服务分过低降低分数
        op_score = current_data.get('operation_score', 0)
        sv_score = current_data.get('service_score', 0)
        if op_score < 60:
            score -= 20
        if sv_score < 60:
            score -= 20

        # 已有较高评分加分
        rating = current_data.get('average_rating', 0)
        if rating >= 4.5:
            score += 5
        elif rating < 4.0:
            score -= 15

        return max(0, min(100, score))

    def _generate_conclusion(self, days: int, score: int) -> str:
        """生成结论"""
        if score >= 80:
            return f"冲榜可行性很高，预计 {days} 天可达成目标，建议立即启动冲榜计划。"
        elif score >= 60:
            return f"冲榜可行性较好，预计 {days} 天可达成目标，需要坚持执行计划。"
        elif score >= 40:
            return f"冲榜有一定难度，预计 {days} 天，建议先提升经营分服务分后再冲榜。"
        else:
            return f"冲榜难度较大，建议先做基础运营积累，数据达标后再冲击榜单。"

    def _save_diagnosis_result(
        self,
        business_id: str,
        report: FeasibilityReport,
        rank_info: RankInfo,
        competitors: List[CompetitorInfo]
    ):
        """保存诊断结果"""
        output = {
            'generated_at': datetime.now().isoformat(),
            'business_id': business_id,
            'report': asdict(report),
            'rank_info': asdict(rank_info),
            'competitors': [asdict(c) for c in competitors],
        }

        path = settings.data_dir / f"{business_id}_rank_diagnosis.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def generate_markdown_report(self, report: FeasibilityReport) -> str:
        """生成Markdown格式的可行性报告"""
        md = f"""# 同城榜单冲榜可行性报告

## 基本信息
- 商家名称：**{report.business_name}**
- 当前排名：{report.current_rank if report.current_rank else "未上榜"}
- 目标排名：前 {report.target_rank} 名

## 当前数据
"""
        for key, value in report.current_data.items():
            if isinstance(value, (int, float)):
                md += f"- {key}: {value}\n"

        md += f"""
## 缺口分析
"""
        for key, value in report.gap_analysis.items():
            if isinstance(value, (int, float)) and value > 0:
                md += f"- {key}: 还差 {value}\n"

        md += f"""
## 冲榜预测
- 预计上榜时间：**{report.estimated_days} 天**
- 需要新增销量：{report.required_sales}
- 需要新增短视频：{report.required_videos}
- 需要新增直播时长：{report.required_live_hours} 小时

## 可行性评估
- 可行性分数：**{report.feasibility_score}/100**

## 结论
{report.conclusion}

---
*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return md
