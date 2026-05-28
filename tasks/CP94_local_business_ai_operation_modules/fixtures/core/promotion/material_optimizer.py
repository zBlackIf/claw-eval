"""
本地生活商家自助投流 - 投流素材自动优化模块
负责检测素材合规性、生成投流标题标签和投放话术
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MaterialCheckResult:
    """素材检测结果"""
    is_compliant: bool
    issues: List[str]
    score: int  # 0-100分
    suggestions: List[str]

    def to_dict(self) -> Dict:
        return {
            "is_compliant": self.is_compliant,
            "issues": self.issues,
            "score": self.score,
            "suggestions": self.suggestions
        }


@dataclass
class OptimizedMaterial:
    """优化后的投流素材"""
    original_title: str
    optimized_titles: List[str]
    tags: List[str]
    crowd_description: str
    douplus_copy: str
    suixintui_copy: str

    def to_dict(self) -> Dict:
        return {
            "original_title": self.original_title,
            "optimized_titles": self.optimized_titles,
            "tags": self.tags,
            "crowd_description": self.crowd_description,
            "douplus_copy": self.douplus_copy,
            "suixintui_copy": self.suixintui_copy
        }


class MaterialComplianceChecker:
    """投流素材合规检测器"""

    def __init__(self):
        # 违规关键词列表
        self.forbidden_words = [
            "最", "第一", "顶级", "国家级", "世界级", "最高", "最佳", "绝对",
            "根治", "根治", "100%", "包好", "痊愈", "特效",
            "国家级", "官方推荐", "免检", "国家领导人",
            "赌博", "色情", "毒品", "枪支", "军火",
            "投资返利", "稳赚不赔", "保本", "暴富",
        ]

        # 水印检测特征
        self.watermark_patterns = [
            r"抖音", r"快手", r"小红书", r"视频号",
            r"剪映", r"醒图", r"水印", r"截图",
            r"www\.", r".com", r"http",
        ]

        # 最低画质要求
        self.min_resolution_width = 720
        self.min_resolution_height = 1280

    def check_forbidden_words(self, text: str) -> Tuple[bool, List[str]]:
        """检测违规关键词"""
        found = []
        for word in self.forbidden_words:
            if word in text:
                found.append(word)
        return len(found) == 0, found

    def check_watermark(self, image_path: Optional[str] = None, has_watermark: bool = False) -> Tuple[bool, str]:
        """检测水印 - 如果通过AI或人工识别有水印返回False"""
        if has_watermark:
            return False, "素材存在明显水印/Logo，不符合投流规范"
        return True, ""

    def check_resolution(self, width: int, height: int) -> Tuple[bool, str]:
        """检测分辨率"""
        if width < self.min_resolution_width or height < self.min_resolution_height:
            return False, f"画质不达标，最低要求 {self.min_resolution_width}x{self.min_resolution_height}，当前 {width}x{height}"
        return True, ""

    def check_duration(self, duration_sec: float) -> Tuple[bool, str]:
        """检测视频时长 - 投流适合15-60秒"""
        if duration_sec < 10:
            return False, f"视频时长过短({duration_sec:.0f}秒)，投流建议15-60秒"
        if duration_sec > 120:
            return False, f"视频时长过长({duration_sec:.0f}秒)，投流建议15-60秒"
        return True, ""

    def check_video_compliance(
        self,
        title: str,
        description: str = "",
        has_watermark: bool = False,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration_sec: Optional[float] = None
    ) -> MaterialCheckResult:
        """综合检测视频合规性"""
        issues = []
        suggestions = []
        score = 100

        # 检测违规词
        text_to_check = title + " " + description
        ok_words, bad_words = self.check_forbidden_words(text_to_check)
        if not ok_words:
            issues.append(f"包含违规关键词: {', '.join(bad_words)}")
            score -= 20 * len(bad_words)
            suggestions.append(f"删除违规关键词: {', '.join(bad_words)}")

        # 检测水印
        ok_watermark, msg_watermark = self.check_watermark(has_watermark=has_watermark)
        if not ok_watermark:
            issues.append(msg_watermark)
            score -= 25
            suggestions.append("去除水印、第三方Logo和文字遮盖")

        # 检测分辨率
        if width and height:
            ok_res, msg_res = self.check_resolution(width, height)
            if not ok_res:
                issues.append(msg_res)
                score -= 15
                suggestions.append("重新导出更高分辨率视频，建议1080*1920")

        # 检测时长
        if duration_sec:
            ok_dur, msg_dur = self.check_duration(duration_sec)
            if not ok_dur:
                issues.append(msg_dur)
                score -= 10
                suggestions.append("裁剪到15-60秒，突出核心卖点")

        # 标题长度检查
        if len(title) < 5:
            issues.append("标题过短，信息不足")
            score -= 10
            suggestions.append("优化标题长度，增加核心卖点信息")
        elif len(title) > 50:
            issues.append("标题过长，建议精简")
            score -= 5
            suggestions.append("精简标题到50字以内，平台推荐5-30字最佳")

        # 计算合规性
        is_compliant = score >= 70 and len(issues) == 0

        if is_compliant:
            suggestions.append("素材符合投流规范，可以正常投放")

        # 确保分数不低于0
        score = max(0, score)

        return MaterialCheckResult(
            is_compliant=is_compliant,
            issues=issues,
            score=score,
            suggestions=suggestions
        )


class MaterialOptimizer:
    """投流素材优化器 - 生成标题、标签、投放话术"""

    def __init__(self):
        self.industry_hot_tags = {
            "catering": [
                "#本地美食", "#同城美食", "#美食推荐", "#吃喝玩乐",
                "#探店", "#火锅", "#烤肉", "#奶茶", "#甜品",
                "#美食探店", "#好吃不贵", "#本地人推荐"
            ],
            "beauty": [
                "#本地美容", "#同城美发", "#美甲美睫", "#皮肤管理",
                "#变美", "#美容探店", "#同城变美", "#精致女孩",
                "#护肤", "#美妆", "#美发", "#SPA"
            ],
            "fitness": [
                "#健身", "#减肥", "#同城健身", "#本地健身房",
                "#减脂", "#塑形", "#健身教练", "#运动打卡",
                "#撸铁", "#瑜伽", "#普拉提"
            ],
            "retail": [
                "#本地购物", "#同城好店", "#女装", "#男装", "#鞋包",
                "#好物推荐", "#性价比", "#本地人都爱", "#宝藏店铺",
                "#周末逛街", "#实体店"
            ],
            "hotel": [
                "#本地酒店", "#同城住宿", "#民宿推荐", "#周末度假",
                "#酒店探店", "#休闲度假", "#性价比酒店", "#亲子游",
                "#周边游", "#城市度假"
            ],
            "entertainment": [
                "#本地玩乐", "#同城休闲", "#KTV", "#密室逃脱", "#剧本杀",
                "#周末去哪玩", "#朋友聚会", "#玩乐指南", "#网红打卡",
                "#拍照好看", "#城市探店"
            ],
            "education": [
                "#本地教育", "#同城培训", "#亲子教育", "#兴趣班", "#技能培训",
                "#少儿", "#成人培训", "#考证", "#学习打卡", "#教育培训"
            ],
            "health": [
                "#本地养生", "#同城健康", "#中医养生", "#推拿按摩", "#足疗",
                "#健康生活", "#调理身体", "#放松身心", "#养生会馆"
            ],
        }

        # 标题模板
        self.title_templates = {
            "catering": [
                "{city}人都在吃的{name}，性价比超高！",
                "在{city}找到超好吃的{name}，就在{location}",
                "这家{name}我能吃100次！{special}",
                "同城探店 | 藏在{area}的宝藏{name}",
            ],
            "beauty": [
                "{city}女生都爱来的{project}，太舒服了",
                "在{city}做{project}，这家真的绝",
                "同城变美好去处 | {name}，性价比拉满",
                "这家{project}我愿意N刷，体验感满分",
            ],
            "default": [
                "{city}同城推荐 | {name}",
                "本地宝藏好店 | {name}，值得一来",
                "{area}这家{industry}，真的太香了",
                "同城探店 | 发现一家超棒的{name}",
            ]
        }

    def generate_optimized_titles(
        self,
        original_title: str,
        industry: str,
        city: str,
        business_name: str,
        area: str = "",
        special: str = ""
    ) -> List[str]:
        """生成优化后的投流标题"""
        templates = self.title_templates.get(industry, self.title_templates["default"])
        titles = []

        for tpl in templates:
            title = tpl.format(
                city=city,
                name=business_name,
                location=area or city,
                area=area or "本地",
                project=original_title,
                special=special or "特色美食" if industry == "catering" else "特色项目",
                industry=industry
            )
            titles.append(title)

        # 加入带福利引导的标题
        titles.append(f"点击定位抢福利！{business_name} - {city}同城专属优惠")
        titles.append(f"{city}本地人都在抢，{business_name}优惠套餐，手慢无！")

        return titles[:5]  # 返回最多5个标题

    def generate_tags(self, industry: str, custom_tags: List[str] = None) -> List[str]:
        """生成投流标签"""
        base_tags = [
            "#本地生活", "#同城", "#同城探店", "#本地商家", "#探店"
        ]

        industry_tags = self.industry_hot_tags.get(industry, [])

        all_tags = base_tags + industry_tags
        if custom_tags:
            all_tags.extend([f"#{tag}" if not tag.startswith('#') else tag for tag in custom_tags])

        # 去重，返回最多15个标签
        seen = set()
        result = []
        for tag in all_tags:
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
                if len(result) >= 15:
                    break

        return result

    def generate_crowd_description(self, industry: str, radius_km: int) -> str:
        """生成人群定向文案"""
        descriptions = {
            "catering": f"辐射{radius_km}公里范围内美食爱好者、周边上班族、周边居民，精准触达有即时到店需求的用户",
            "beauty": f"面向{radius_km}公里范围内18-45岁女性用户，精准覆盖爱美人士、品质生活人群",
            "fitness": f"覆盖{radius_km}公里范围内健身爱好者、减脂塑形需求人群、年轻上班族",
            "retail": f"{radius_km}公里范围内周边居民、逛街人群，覆盖全年龄段购物需求用户",
            "hotel": f"面向全市范围内差旅用户、本地休闲度假人群、周边游用户",
            "entertainment": f"{radius_km}公里范围内年轻人群、朋友聚会、周末休闲娱乐用户",
            "education": f"{radius_km}公里范围内有相关培训需求的家长/成人用户",
            "health": f"{radius_km}公里范围内注重养生健康的人群，全年龄段覆盖",
        }
        return descriptions.get(
            industry,
            f"辐射{radius_km}公里范围内本地生活人群，精准触达有需求的目标客户"
        )

    def generate_douplus_copy(self, business_name: str, industry: str, offer: str = "") -> str:
        """生成DOU+投放话术"""
        if not offer:
            offer = "到店享受专属优惠"

        template = f"""【DOU+ 投放建议】

投放目标：门店引流
定向范围：同城5公里
人群方向：{industry}行业精准人群

投放文案：
{business_name} 本地实体门店，品质保障！
{offer}
点击下方定位立即抢购/预约！

投放技巧：
1. 选择门店引流目标，更容易获得平台推流
2. 投放2小时后看数据，进店成本低于5元可加投
3. 同一素材持续投放，系统会持续优化人群
"""
        return template

    def generate_suixintui_copy(self, business_name: str, product_name: str, price: float = None) -> str:
        """生成随心投放放话术"""
        price_text = f"{price}元" if price else "优惠价"
        template = f"""【随心推 投放建议】

投放类型：小店随心推 / 商品随心推
投放目标：成交转化

商品信息：
商家：{business_name}
商品：{product_name}
价格：{price_text}

定向设置：
- 地域：同城5公里
- 兴趣标签：对应行业类目
- 智能放量：开启（帮助探索更多潜在客户）

出价建议：
- 根据商品利润出价，出价=商品利润*30%
- 投放时长：6小时/12小时测试
- 跑不动再提价，每次提价0.1-0.3元

优化技巧：
1. 选择最近7天自然流量好的视频投放
2. 同一个商品测试2-3个素材，保留ROI最高的
3. ROI达标可以持续加投，ROI低于1:2及时关停
"""
        return template

    def optimize_material(
        self,
        original_title: str,
        industry: str,
        city: str,
        business_name: str,
        area: str = "",
        special: str = "",
        radius_km: int = 5,
        custom_tags: List[str] = None,
        offer: str = "",
        product_name: str = "",
        product_price: float = None
    ) -> OptimizedMaterial:
        """完整优化投流素材"""
        optimized_titles = self.generate_optimized_titles(
            original_title, industry, city, business_name, area, special
        )
        tags = self.generate_tags(industry, custom_tags)
        crowd_desc = self.generate_crowd_description(industry, radius_km)
        douplus = self.generate_douplus_copy(business_name, industry, offer)
        suixintui = self.generate_suixintui_copy(business_name, product_name or original_title, product_price)

        return OptimizedMaterial(
            original_title=original_title,
            optimized_titles=optimized_titles,
            tags=tags,
            crowd_description=crowd_desc,
            douplus_copy=douplus,
            suixintui_copy=suixintui
        )

    def export_optimization_result(
        self,
        check_result: MaterialCheckResult,
        optimized: OptimizedMaterial,
        output_path: str
    ) -> str:
        """导出优化结果"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "compliance_check": check_result.to_dict(),
            "optimized_material": optimized.to_dict(),
            "notice": "投流素材优化仅供参考，请人工审核后再投放"
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return output_path
