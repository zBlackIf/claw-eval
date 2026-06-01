# 短视频内容分析任务

## 分析维度
请从以下维度分析视频存在的问题并给出改进建议：

1. **标题与封面** - 标题吸引力、关键词密度、搜索友好度
2. **内容结构** - 开头钩子、节奏把控、信息密度、结尾引导
3. **标签策略** - 标签数量、精准度、热度与竞争度平衡
4. **受众定位** - 目标用户画像、内容与受众匹配度
5. **数据诊断** - 基于互动数据判断问题环节（完播率、互动率等）

## 输出要求
1. 生成 video_analysis_report.md - 详细分析报告
2. 生成 improvement_plan.json - 结构化改进方案
   格式：
   {
     "video_id": "...",
     "overall_score": 0-100,
     "issues": [{"dimension": "...", "severity": "high/medium/low", "description": "...", "suggestion": "..."}],
     "optimized_title_options": ["..."],
     "recommended_hashtags": ["..."],
     "content_structure_suggestion": "..."
   }
