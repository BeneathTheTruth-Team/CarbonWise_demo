"""
碳智评 - Python数据可视化模块
功能：桑基图、雷达图、柱状图、热力图生成
技术栈：Plotly + Pandas + NumPy
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

class CarbonVisualizer:
    """碳数据可视化引擎"""

    def __init__(self, color_scheme: Dict[str, str] = None):
        """
        初始化可视化引擎

        Args:
            color_scheme: 配色方案，默认使用碳智评品牌色
        """
        self.colors = color_scheme or {
            'primary': '#2D6A4F',      # 深森绿
            'secondary': '#D4AF37',     # 金色
            'accent': '#E63946',       # 草莓红
            'background': '#f8f9fa',
            'text': '#333333',
            'grid': '#e9ecef'
        }

        self.process_names = [
            '原棉种植', '化纤生产', '纺纱', '织造', 
            '印染整理', '后整理', '运输销售', '消费使用', '废弃处理'
        ]

    def generate_sankey(self, carbon_flows: List[float], 
                       title: str = "纺织全生命周期碳流向") -> go.Figure:
        """
        生成桑基图展示碳流向

        Args:
            carbon_flows: 各环节碳排放量(kgCO2e/吨布)
            title: 图表标题

        Returns:
            Plotly Figure对象
        """
        # 桑基图节点定义
        labels = self.process_names + ['总排放']

        # 源节点索引(0-8) -> 目标节点索引(9)
        source = list(range(9))
        target = [9] * 9
        value = carbon_flows

        # 颜色映射
        colors_nodes = [self.colors['primary']] * 9 + [self.colors['accent']]
        colors_links = [
            f'rgba(45, 106, 79, {0.3 + v/max(carbon_flows)*0.7})' 
            for v in carbon_flows
        ]

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=colors_nodes,
                hovertemplate='%{label}<br>碳排放: %{value:.1f} kgCO₂e<extra></extra>'
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color=colors_links,
                hovertemplate='%{source.label} → %{target.label}<br>' +
                             '碳排放: %{value:.1f} kgCO₂e<br>' +
                             '占比: %{percent:.1%}<extra></extra>'
            )
        )])

        fig.update_layout(
            title_text=title,
            font_size=12,
            paper_bgcolor=self.colors['background'],
            plot_bgcolor=self.colors['background'],
            width=900,
            height=500,
            title_font=dict(size=16, color=self.colors['text'])
        )

        return fig

    def generate_radar(self, scores: Dict[str, float],
                      title: str = "碳效六维评分") -> go.Figure:
        """
        生成雷达图展示碳效六维评分

        Args:
            scores: 六维评分字典
                - energy_efficiency: 能源效率
                - carbon_intensity: 碳排放强度
                - waste_recycling: 废弃物回收率
                - water_usage: 水资源利用
                - chemical_mgmt: 化学品管理
                - renewable_ratio: 可再生能源占比
            title: 图表标题

        Returns:
            Plotly Figure对象
        """
        categories = ['能源效率', '碳排放强度', '废弃物回收率', 
                     '水资源利用', '化学品管理', '可再生能源占比']

        values = [
            scores.get('energy_efficiency', 0),
            scores.get('carbon_intensity', 0),
            scores.get('waste_recycling', 0),
            scores.get('water_usage', 0),
            scores.get('chemical_mgmt', 0),
            scores.get('renewable_ratio', 0)
        ]

        # 闭合雷达图
        values += values[:1]
        categories += categories[:1]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            fillcolor='rgba(45, 106, 79, 0.3)',
            line=dict(color=self.colors['primary'], width=2),
            name='当前企业',
            hovertemplate='%{theta}: %{r:.1f}分<extra></extra>'
        ))

        # 行业平均线
        industry_avg = [60, 60, 60, 60, 60, 60, 60]
        fig.add_trace(go.Scatterpolar(
            r=industry_avg,
            theta=categories,
            fill='toself',
            fillcolor='rgba(212, 175, 55, 0.1)',
            line=dict(color=self.colors['secondary'], width=1.5, dash='dash'),
            name='行业平均'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor=self.colors['grid'],
                    tickfont=dict(size=10)
                ),
                angularaxis=dict(
                    tickfont=dict(size=11)
                ),
                bgcolor=self.colors['background']
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            ),
            title_text=title,
            title_font=dict(size=16, color=self.colors['text']),
            paper_bgcolor='white',
            width=600,
            height=550
        )

        return fig

    def generate_monthly_trend(self, monthly_data: pd.DataFrame,
                               title: str = "月度碳效对标趋势") -> go.Figure:
        """
        生成柱状图展示月度对标趋势

        Args:
            monthly_data: DataFrame包含columns=['月份', '本企业', '行业平均', '行业先进']
            title: 图表标题

        Returns:
            Plotly Figure对象
        """
        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='本企业',
            x=monthly_data['月份'],
            y=monthly_data['本企业'],
            marker_color=self.colors['primary'],
            hovertemplate='%{x}<br>本企业: %{y:.2f} tCO₂e/t<extra></extra>'
        ))

        fig.add_trace(go.Bar(
            name='行业平均',
            x=monthly_data['月份'],
            y=monthly_data['行业平均'],
            marker_color=self.colors['secondary'],
            hovertemplate='%{x}<br>行业平均: %{y:.2f} tCO₂e/t<extra></extra>'
        ))

        fig.add_trace(go.Bar(
            name='行业先进',
            x=monthly_data['月份'],
            y=monthly_data['行业先进'],
            marker_color=self.colors['grid'],
            marker_line_color=self.colors['secondary'],
            marker_line_width=1.5,
            hovertemplate='%{x}<br>行业先进: %{y:.2f} tCO₂e/t<extra></extra>'
        ))

        fig.update_layout(
            barmode='group',
            title_text=title,
            xaxis_title="月份",
            yaxis_title="碳排放强度 (tCO₂e/吨)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            paper_bgcolor='white',
            plot_bgcolor=self.colors['background'],
            width=900,
            height=450,
            title_font=dict(size=16, color=self.colors['text']),
            font=dict(size=11)
        )

        fig.update_xaxes(gridcolor=self.colors['grid'])
        fig.update_yaxes(gridcolor=self.colors['grid'])

        return fig

    def generate_heatmap(self, equipment_matrix: pd.DataFrame,
                        title: str = "设备级碳排放热力分布") -> go.Figure:
        """
        生成热力图展示设备级碳排放分布

        Args:
            equipment_matrix: DataFrame(index=设备, columns=月份, values=碳排放)
            title: 图表标题

        Returns:
            Plotly Figure对象
        """
        fig = px.imshow(
            equipment_matrix,
            labels=dict(x="月份", y="设备", color="碳排放(kgCO₂e)"),
            x=equipment_matrix.columns,
            y=equipment_matrix.index,
            color_continuous_scale=[
                [0, '#f8f9fa'],
                [0.3, '#a8d5ba'],
                [0.6, '#2D6A4F'],
                [1, '#05140f']
            ],
            aspect="auto"
        )

        fig.update_traces(
            hovertemplate='%{y}<br>%{x}<br>碳排放: %{z:.1f} kgCO₂e<extra></extra>'
        )

        fig.update_layout(
            title_text=title,
            title_font=dict(size=16, color=self.colors['text']),
            paper_bgcolor='white',
            width=900,
            height=400,
            coloraxis_colorbar=dict(
                title="碳排放<br>(kgCO₂e)",
                titleside="right"
            )
        )

        return fig


# ==================== 报告生成模块 ====================

class ReportGenerator:
    """多标准报告自动生成器"""

    SUPPORTED_STANDARDS = ['ISO14067', 'PAS2050', 'CBAM', 'BANK_RATING', 'INTERNAL']

    def __init__(self, template_dir: str = "./templates"):
        self.template_dir = template_dir

    def generate_iso14067_report(self, company_data: Dict, 
                                  result: Dict) -> str:
        """
        生成ISO 14067产品碳足迹报告(中英文双语)

        Args:
            company_data: 企业基本信息
            result: 核算结果

        Returns:
            HTML格式报告字符串
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>ISO 14067 Product Carbon Footprint Report</title>
            <style>
                body {{ font-family: 'SimSun', serif; margin: 40px; color: #333; }}
                .header {{ text-align: center; border-bottom: 3px solid #2D6A4F; padding-bottom: 20px; }}
                .title {{ font-size: 24px; font-weight: bold; color: #2D6A4F; }}
                .subtitle {{ font-size: 14px; color: #666; margin-top: 10px; }}
                .section {{ margin: 30px 0; }}
                .section-title {{ font-size: 16px; font-weight: bold; color: #2D6A4F; 
                                border-left: 4px solid #D4AF37; padding-left: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #2D6A4F; color: white; }}
                .highlight {{ background-color: #fff3cd; }}
                .footer {{ margin-top: 50px; text-align: center; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">产品碳足迹报告 Product Carbon Footprint Report</div>
                <div class="subtitle">依据 ISO 14067:2018 标准 | Based on ISO 14067:2018</div>
            </div>

            <div class="section">
                <div class="section-title">1. 企业信息 Company Information</div>
                <table>
                    <tr><th>项目 Item</th><th>内容 Content</th></tr>
                    <tr><td>企业名称</td><td>{company_data.get('name', 'N/A')}</td></tr>
                    <tr><td>产品类型</td><td>{company_data.get('product', 'N/A')}</td></tr>
                    <tr><td>年产量</td><td>{company_data.get('output', 'N/A')} 吨</td></tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">2. 碳足迹核算结果 Carbon Footprint Results</div>
                <table>
                    <tr><th>指标 Indicator</th><th>数值 Value</th><th>单位 Unit</th></tr>
                    <tr class="highlight"><td>年碳排放总量</td>
                        <td>{result.get('annual_emission', 0):.2f}</td><td>tCO₂e</td></tr>
                    <tr><td>产品碳排放强度</td>
                        <td>{result.get('intensity', 0):.2f}</td><td>tCO₂e/t</td></tr>
                    <tr><td>不确定性区间(90%)</td>
                        <td>±{result.get('uncertainty', 0):.2f}</td><td>tCO₂e/t</td></tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">3. 核算边界 Accounting Boundary</div>
                <p>摇篮到大门 (Cradle-to-Gate): 从原材料获取到产品出厂</p>
                <p>系统边界包括: 原棉种植/化纤生产 → 纺纱 → 织造 → 印染整理 → 后整理</p>
            </div>

            <div class="footer">
                报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d')} | 
                碳智评 CarbonWise SaaS Platform
            </div>
        </body>
        </html>
        """
        return html

    def generate_cbam_template(self, company_data: Dict, 
                              result: Dict) -> str:
        """
        生成CBAM申报模板

        Args:
            company_data: 企业信息
            result: 核算结果

        Returns:
            XML/JSON格式CBAM数据
        """
        import json

        cbam_data = {
            "reporting_entity": company_data.get('name'),
            "reporting_period": "2026-Q1",
            "product_category": "CN-TEXTILE-01",
            "direct_emissions": {
                "quantity": result.get('annual_emission', 0),
                "unit": "tCO2e",
                "methodology": "Parametric Inversion (ISO 14067)"
            },
            "indirect_emissions": {
                "electricity": result.get('electricity_emission', 0),
                "steam": result.get('steam_emission', 0)
            },
            "verification": {
                "body": "CarbonWise SaaS (Self-declared)",
                "uncertainty": result.get('uncertainty', 0),
                "confidence_level": "90%"
            }
        }

        return json.dumps(cbam_data, indent=2, ensure_ascii=False)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化可视化引擎
    viz = CarbonVisualizer()

    # 示例1: 桑基图
    carbon_flows = [450, 320, 430, 470, 890, 210, 120, 95, 85]  # 各环节碳排放
    fig1 = viz.generate_sankey(carbon_flows)
    fig1.write_html("/mnt/agents/output/sankey_chart.html")
    print("✅ 桑基图已保存")

    # 示例2: 雷达图
    scores = {
        'energy_efficiency': 75,
        'carbon_intensity': 82,
        'waste_recycling': 60,
        'water_usage': 70,
        'chemical_mgmt': 65,
        'renewable_ratio': 45
    }
    fig2 = viz.generate_radar(scores)
    fig2.write_html("/mnt/agents/output/radar_chart.html")
    print("✅ 雷达图已保存")

    # 示例3: 月度趋势
    monthly_df = pd.DataFrame({
        '月份': ['1月', '2月', '3月', '4月', '5月', '6月'],
        '本企业': [5.69, 5.45, 5.21, 5.38, 5.15, 4.98],
        '行业平均': [5.50, 5.50, 5.50, 5.50, 5.50, 5.50],
        '行业先进': [4.20, 4.15, 4.10, 4.05, 4.00, 3.95]
    })
    fig3 = viz.generate_monthly_trend(monthly_df)
    fig3.write_html("/mnt/agents/output/monthly_trend.html")
    print("✅ 月度趋势图已保存")

    # 示例4: 热力图
    equipment_df = pd.DataFrame(
        np.random.rand(5, 6) * 1000,
        index=['细纱机', '浆纱机', '喷气织机', '溢流染色机', '空压机'],
        columns=['1月', '2月', '3月', '4月', '5月', '6月']
    )
    fig4 = viz.generate_heatmap(equipment_df)
    fig4.write_html("/mnt/agents/output/heatmap.html")
    print("✅ 热力图已保存")

    # 示例5: 报告生成
    reporter = ReportGenerator()
    company = {'name': '蓝天纺织', 'product': '涤纶染色布', 'output': 1200}
    result = {'annual_emission': 6826, 'intensity': 5.69, 'uncertainty': 0.34}

    iso_report = reporter.generate_iso14067_report(company, result)
    with open('/mnt/agents/output/iso14067_report.html', 'w', encoding='utf-8') as f:
        f.write(iso_report)
    print("✅ ISO 14067报告已保存")

    cbam_data = reporter.generate_cbam_template(company, result)
    with open('/mnt/agents/output/cbam_template.json', 'w', encoding='utf-8') as f:
        f.write(cbam_data)
    print("✅ CBAM模板已保存")
