#!/usr/bin/env python3
"""
本地生活实体商家 AI 运营 - 主入口
"""
import click
import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from config import settings

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """本地生活实体商家 AI 运营 - 全流程自动化运营工具"""
    pass


@cli.command()
def init():
    """初始化项目，检查配置"""
    console.print(Panel.fit(
        "[bold blue]本地生活商家 AI 运营[/]\n正在初始化...",
        border_style="gold"
    ))

    # 创建必要目录
    settings.output_dir.mkdir(exist_ok=True)
    settings.data_dir.mkdir(exist_ok=True)

    console.print("[green]✓ 初始化完成[/]")
    console.print(f"输出目录: {settings.output_dir}")
    console.print(f"数据目录: {settings.data_dir}")


@cli.command()
@click.option("--city", required=True, help="同城城市名称，使用 \"all\" 代表全城市")
@click.option("--industry", required=True, help="行业 (catering/beauty/fitness/retail/hotel/entertainment/education/health)，使用 \"all\" 代表全行业")
@click.option("--limit", default=20, help="返回数量")
@click.option("--days", default=None, type=int, help="只取最近 N 天 (默认使用配置文件)")
@click.option("--rising-only", is_flag=True, default=False, help="只保留热度上升的视频")
def find_hot(city, industry, limit, days, rising_only):
    """查找近N天热度上升的同城同行业爆款视频"""
    from core.analyzer.hot_finder import HotFinder

    finder = HotFinder()
    results = asyncio.run(finder.find_rising_hot(city, industry, limit, days, rising_only))

    console.print(f"[green]找到 {len(results)} 个热度上升视频[/]")
    for i, item in enumerate(results, 1):
        console.print(f"{i}. [{item['platform']}] {item['title']} ↑{item['trend']:.1f}% 热度={item['hot_value']:.0f}")


# ========== 自助投流模块 ==========

@cli.command()
@click.option("--title", required=True, help="视频标题")
@click.option("--description", default="", help="视频描述")
@click.option("--has-watermark", is_flag=True, default=False, help="是否有水印")
@click.option("--width", type=int, default=None, help="视频宽度")
@click.option("--height", type=int, default=None, help="视频高度")
@click.option("--duration", type=float, default=None, help="视频时长（秒）")
def check_material(title, description, has_watermark, width, height, duration):
    """投流素材合规检测 - 检查素材是否符合投放要求"""
    from core.promotion.material_optimizer import MaterialComplianceChecker
    
    checker = MaterialComplianceChecker()
    result = checker.check_video_compliance(
        title=title,
        description=description,
        has_watermark=has_watermark,
        width=width,
        height=height,
        duration_sec=duration
    )
    
    console.print(f"[blue]检测结果:[/]")
    console.print(f"  合规分数: [bold]{result.score}/100[/]")
    console.print(f"  是否合规: {'[green]✓ 通过' if result.is_compliant else '[red]✗ 不通过'}[/]")
    
    if result.issues:
        console.print(f"[yellow]发现问题:[/]")
        for issue in result.issues:
            console.print(f"  - {issue}")
    
    if result.suggestions:
        console.print(f"[blue]优化建议:[/]")
        for sugg in result.suggestions:
            console.print(f"  - {sugg}")

@cli.command()
@click.option("--title", required=True, help="原视频标题")
@click.option("--industry", required=True, help="行业 (catering/beauty/fitness/retail/hotel/entertainment/education/health)")
@click.option("--city", required=True, help="城市名称")
@click.option("--business-name", required=True, help="商家名称")
@click.option("--area", default="", help="区域（商圈）")
@click.option("--special", default="", help="特色卖点")
@click.option("--radius", type=int, default=5, help="投放半径（公里）")
@click.option("--offer", default="", help="优惠活动描述")
@click.option("--product-name", default="", help="投放商品名称")
@click.option("--price", type=float, default=None, help="商品价格")
@click.option("--output", default=None, help="输出JSON文件路径")
def optimize_material(title, industry, city, business_name, area, special, radius, offer, product_name, price, output):
    """优化投流素材 - 生成优化标题、标签、投放话术"""
    from core.promotion.material_optimizer import MaterialOptimizer, MaterialComplianceChecker
    from config import settings
    
    optimizer = MaterialOptimizer()
    checker = MaterialComplianceChecker()
    
    # 先做合规检查
    check_result = checker.check_video_compliance(title=title)
    
    # 优化素材
    optimized = optimizer.optimize_material(
        original_title=title,
        industry=industry,
        city=city,
        business_name=business_name,
        area=area,
        special=special,
        radius_km=radius,
        offer=offer,
        product_name=product_name,
        product_price=price
    )
    
    # 输出结果
    console.print(Panel.fit(
        f"[bold green]投流素材优化完成[/]\n"
        f"合规分数: {check_result.score}/100\n"
        f"是否合规: {'✓ 通过' if check_result.is_compliant else '✗ 需要修改'}",
        border_style="green"
    ))
    
    console.print("\n[bold blue]优化后标题:[/]")
    for i, t in enumerate(optimized.optimized_titles, 1):
        console.print(f"  {i}. {t}")
    
    console.print(f"\n[bold blue]标签:[/] {' '.join(optimized.tags)}")
    
    console.print(f"\n[bold blue]人群定向描述:[/]\n  {optimized.crowd_description}")
    
    console.print("\n[bold blue]DOU+ 投放话术:[/]")
    console.print(optimized.douplus_copy)
    
    console.print("\n[bold blue]随心推 投放话术:[/]")
    console.print(optimized.suixintui_copy)
    
    if output:
        output_path = settings.output_dir / output
        optimizer.export_optimization_result(check_result, optimized, str(output_path))
        console.print(f"[green]✓ 完整结果已保存: {output_path}[/]")
    else:
        default_path = settings.output_dir / f"optimized_{industry}_{title[:20]}.json"
        optimizer.export_optimization_result(check_result, optimized, str(default_path))
        console.print(f"[dim]完整结果已自动保存: {default_path}[/dim]")

@cli.command()
@click.option("--industry", required=True, help="行业")
@click.option("--lat", type=float, required=True, help="门店纬度")
@click.option("--lng", type=float, required=True, help="门店经度")
@click.option("--daily-budget", type=float, required=True, help="日预算（元）")
@click.option("--radius", type=int, default=5, help="投放半径（公里）")
@click.option("--output", default=None, help="输出JSON文件路径")
def strategy_city(industry, lat, lng, daily_budget, radius, output):
    """生成同城门店定向投流策略 - 固定半径精准投放"""
    from core.promotion.flow_strategy import FlowStrategyGenerator
    from config import settings
    
    generator = FlowStrategyGenerator()
    plan = generator.generate_city_target_strategy(
        store_lat=lat,
        store_lng=lng,
        industry=industry,
        daily_budget=daily_budget,
        radius=radius
    )
    
    # 打印计划
    console.print(Panel.fit(
        f"[bold blue]{plan.plan_name}[/]\n"
        f"策略类型: {plan.strategy_type}\n"
        f"投放半径: {plan.crowd_target.radius_km} 公里\n"
        f"日预算: {plan.budget.daily_budget} 元\n"
        f"建议出价: {plan.suggested_bid} 元/点击\n"
        f"\n推荐理由: {plan.reason}\n"
        f"预期效果: {plan.estimated_effect}",
        title="[green]同城定向投流计划[/]",
        border_style="blue"
    ))
    
    if output:
        output_path = settings.output_dir / output
        generator.export_plans_json([plan], str(output_path))
        console.print(f"[green]✓ 计划已保存: {output_path}[/]")

@cli.command()
@click.option("--industry", required=True, help="行业")
@click.option("--address", required=True, help="门店地址")
@click.option("--daily-budget", type=float, default=50.0, help="日预算（元），默认50元小额测试")
@click.option("--output", default=None, help="输出JSON文件路径")
def strategy_cold(industry, address, daily_budget, output):
    """生成冷启动投流策略 - 新号0粉起号冲同城榜单"""
    from core.promotion.flow_strategy import FlowStrategyGenerator
    from config import settings
    
    generator = FlowStrategyGenerator()
    plan = generator.generate_cold_start_strategy(
        industry=industry,
        store_address=address,
        daily_budget=daily_budget
    )
    
    console.print(Panel.fit(
        f"[bold blue]{plan.plan_name}[/]\n"
        f"策略类型: {plan.strategy_type}\n"
        f"日预算: {plan.budget.daily_budget} 元\n"
        f"建议出价: {plan.suggested_bid} 元/点击\n"
        f"单次进店上限: {plan.budget.max_cost_per_entry} 元\n"
        f"\n推荐理由: {plan.reason}\n"
        f"预期效果: {plan.estimated_effect}",
        title="[green]冷启动投流计划[/]",
        border_style="blue"
    ))
    
    if output:
        output_path = settings.output_dir / output
        generator.export_plans_json([plan], str(output_path))
        console.print(f"[green]✓ 计划已保存: {output_path}[/]")

@cli.command()
@click.option("--industry", required=True, help="行业")
@click.option("--daily-budget", type=float, required=True, help="总日预算（元）")
@click.option("--input-file", required=True, help="视频数据JSON文件路径")
@click.option("--output", default=None, help="输出JSON文件路径")
def strategy_hot(industry, daily_budget, input_file, output):
    """生成爆款优先投流策略 - 自然流量好的视频放大投放"""
    from core.promotion.flow_strategy import FlowStrategyGenerator, VideoInfo
    from config import settings
    import json
    
    generator = FlowStrategyGenerator()
    
    # 读取视频数据
    with open(input_file, 'r', encoding='utf-8') as f:
        video_data_list = json.load(f)
    
    videos = []
    for item in video_data_list:
        videos.append(VideoInfo(
            video_id=item.get('video_id', ''),
            title=item.get('title', ''),
            publish_days=item.get('publish_days', 0),
            trend_percent=item.get('trend_percent', 0),
            complete_rate=item.get('complete_rate', 0),
            play_count=item.get('play_count', 0),
            click_to_store=item.get('click_to_store', 0),
            conversion=item.get('conversion', 0)
        ))
    
    plans = generator.generate_hot_priority_strategy(videos, daily_budget, industry)
    
    if not plans:
        console.print("[yellow]没有符合条件的爆款视频，需要满足: 7天内发布，涨幅>10%，完播率>20%[/]")
        return
    
    console.print(f"[green]找到 {len(plans)} 个可投放爆款视频[/]\n")
    
    table = Table(title="爆款投流计划")
    table.add_column("计划名称", style="cyan")
    table.add_column("视频标题", style="white")
    table.add_column("计划预算", style="green")
    table.add_column("建议出价", style="yellow")
    
    for plan in plans:
        table.add_row(
            plan.plan_name[:20],
            plan.video_title[:25] + ("..." if len(plan.video_title) > 25 else ""),
            f"{plan.budget.per_plan_budget:.1f}元",
            f"{plan.suggested_bid:.2f}元"
        )
    
    console.print(table)
    
    for plan in plans:
        console.print(f"\n[bold blue]{plan.plan_name}:[/]")
        console.print(f"  {plan.reason}")
        console.print(f"  {plan.estimated_effect}")
    
    if output:
        output_path = settings.output_dir / output
    else:
        output_path = settings.output_dir / f"hot_strategy_{industry}.json"
    
    generator.export_plans_json(plans, str(output_path))
    console.print(f"\n[green]✓ 完整计划已保存: {output_path}[/]")

@cli.command()
def list_flow_plans():
    """列出所有已生成的投流计划"""
    from config import settings
    from pathlib import Path
    import json
    
    # 查找所有JSON计划文件
    plan_files = list(settings.output_dir.glob("*strategy*.json")) + list(settings.output_dir.glob("*optimized*.json"))
    
    if not plan_files:
        console.print("[yellow]暂无投流计划文件[/]")
        return
    
    table = Table(title="已生成投流计划")
    table.add_column("文件名", style="cyan")
    table.add_column("生成时间", style="white")
    table.add_column("计划数量", style="green")
    
    for f in sorted(plan_files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
            generated_at = data.get('generated_at', '').split('T')[0]
            total = data.get('total_plans', 1)
            table.add_row(f.name, generated_at, str(total))
        except:
            table.add_row(f.name, "unknown", "?")
    
    console.print(table)

if __name__ == "__main__":
    cli()
# ========== 商家全生命周期服务模块 ==========

@cli.command()
@click.option("--name", required=True, help="商家名称")
@click.option("--industry", required=True, help="行业 (catering/beauty/fitness/retail/hotel/entertainment/education/health)")
@click.option("--type", required=True, default="个体工商户", help="主体类型 (个体工商户/企业)")
@click.option("--legal-person", required=True, help="法人姓名")
@click.option("--address", required=True, help="门店地址")
@click.option("--phone", required=True, help="联系电话")
@click.option("--output", default=None, help="输出文件路径")
def onboarding(name, industry, type, legal_person, address, phone, output):
    """新商家入驻指导 - 生成个性化入驻分步教程"""
    from core.business.onboarding import OnboardingGuide, BusinessInfo

    info = BusinessInfo(
        business_name=name,
        industry=industry,
        business_type=type,
        legal_person_name=legal_person,
        id_card="",  # 不需要实际填写，只用于检查
        business_license="",
        store_address=address,
        phone=phone,
        has_offline_store=True
    )

    # 检查资料完整性
    guide = OnboardingGuide()
    check_result = guide.check_documents(info)

    if not check_result["complete"]:
        console.print("[yellow]⚠ 资料不完整，缺失:[/]")
        for item in check_result["missing"]:
            console.print(f"  - {item}")
        console.print(f"[yellow]行业提示: {check_result['tips']}[/]")

    # 生成入驻指南
    console.print("[blue]正在生成个性化入驻指导...[/]")
    content = guide.generate_guide(info)

    if output:
        output_path = settings.output_dir / output
        output_path.write_text(content, encoding='utf-8')
        console.print(f"[green]✓ 入驻指导已保存: {output_path}[/]")
    else:
        console.print(Panel.fit(content, title="[bold green]入驻指导[/]", border_style="yellow"))
        # 自动保存
        default_path = settings.output_dir / f"{name}_onboarding_guide.md"
        default_path.write_text(content, encoding='utf-8')
        console.print(f"[dim]已自动保存到: {default_path}[/dim]")


@cli.command()
@click.option("--industry", required=True, help="行业")
@click.option("--output", default=None, help="输出文件")
def onboarding_qa(industry, output):
    """生成该行业入驻常见问题QA"""
    from core.business.onboarding import OnboardingGuide

    guide = OnboardingGuide()
    console.print("[blue]正在生成常见问答...[/]")
    content = guide.generate_qa(industry)

    if output:
        output_path = settings.output_dir / output
        output_path.write_text(content, encoding='utf-8')
        console.print(f"[green]✓ QA已保存: {output_path}[/]")
    else:
        console.print(Panel.fit(content, title="[green]入驻常见问答[/]", border_style="yellow"))


@cli.command()
@click.option("--business-id", required=True, help="商家ID")
@click.option("--output", default=None, help="输出文件")
def diagnose(business_id, output):
    """生成商家数据诊断报告"""
    from core.business.diagnostics import DiagnosticsReporter

    reporter = DiagnosticsReporter()
    report = reporter.generate_report(business_id)

    if output:
        output_path = settings.output_dir / output
    else:
        output_path = settings.output_dir / f"{business_id}_diagnosis.md"

    output_path.write_text(report, encoding='utf-8')
    console.print(f"[green]✓ 诊断报告已保存: {output_path}[/]")

    # 打印摘要
    lines = report.split('\n')[:20]
    console.print(Panel.fit('\n'.join(lines) + '\n...', title="[blue]报告摘要[/]", border_style="blue"))


@cli.command()
@click.option("--city", required=True, help="城市")
@click.option("--name", required=True, help="商家名称")
@click.option("--industry", required=True, help="行业")
@click.option("--days", type=int, default=7, help="计划天数 (7或14)")
@click.option("--output", default=None, help="输出文件")
def cold_start(city, name, industry, days, output):
    """生成同城冷启动冲刺计划（7天/14天破播放冲热榜）"""
    from core.business.cold_start import ColdStartPlanner

    planner = ColdStartPlanner()
    console.print(f"[blue]正在生成{days}天冷启动计划...[/]")

    if days == 7:
        plan = planner.generate_7day_plan(city, industry, name)
    elif days == 14:
        plan = planner.generate_14day_plan(city, industry, name)
    else:
        console.print("[red]天数只能是 7 或 14[/]")
        return

    md = planner.export_markdown(plan)

    if output:
        output_path = settings.output_dir / output
    else:
        output_path = settings.output_dir / f"{name}_cold_start_{days}d.md"

    output_path.write_text(md, encoding='utf-8')
    console.print(f"[green]✓ 冷启动计划已保存: {output_path}[/]")

    # 打印概览
    table = Table(title="计划概览")
    table.add_column("项目", style="cyan")
    table.add_column("内容", style="white")
    table.add_row("计划天数", f"{plan.days} 天")
    table.add_row("预期播放", f"{plan.estimated_plays:,}")
    table.add_row("目标排名", plan.ranking_goal)
    table.add_row("核心标签", ", ".join(plan.hashtags[:5]))
    console.print(table)

    # 打印权重技巧
    console.print("[blue]💡 权重提升技巧:[/]")
    for i, tactic in enumerate(planner.get_weight_boost_tactics(), 1):
        console.print(f"  {i}. {tactic}")


@cli.command()
@click.option("--input-dir", required=True, help="输入素材目录")
@click.option("--industry", required=True, help="行业 (catering/beauty/fitness/retail/hotel/entertainment)")
@click.option("--platform", default="douyin", help="平台 (douyin/kuaishou/xhs/video)，all 代表全平台")
def auto_decorate(input_dir, industry, platform):
    """全行业自动装修 - 自动图片裁剪合规"""
    from core.business.decorator import AutoDecorator
    
    decorator = AutoDecorator()
    input_path = Path(input_dir)
    
    if platform == "all":
        results = decorator.batch_process_all_platforms(input_path, industry)
        total = sum(len(r) for r in results.values())
        console.print(f"[green]✓ 全平台自动装修完成，共处理 {total} 张图片[/]")
        for p, r in results.items():
            console.print(f"  {p}: {len(r)} 张")
    else:
        results = decorator.auto_decorate_industry(input_path, industry, platform)
        console.print(f"[green]✓ 自动装修完成[/]")
        for usage, path in results.items():
            console.print(f"  {usage}: {path}")


