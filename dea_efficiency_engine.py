"""
碳智评 - DEA(数据包络分析)效率评估模块
功能：非期望产出SBM-DEA模型、技改优化建议生成
理论基础：陈云锋2025年纺织产品基准碳足迹研究
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, LinearConstraint, Bounds
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DEAResult:
    """DEA评估结果"""
    efficiency_score: float          # 效率评分(0-1)
    target_reduction: float          # 目标碳减排量(吨)
    target_energy_save: float        # 目标节能(kWh)
    improvement_path: Dict[str, float]  # 各投入改进方向
    peer_companies: List[int]        # 参考标杆企业ID
    projection_point: Dict[str, float]  # 投影点坐标


class SBM_DEA_Engine:
    """
    非期望产出SBM-DEA模型

    将碳排放视为"非期望产出"，产品产量视为"期望产出"，
    能源消耗视为"投入"，构建效率前沿面。
    """

    def __init__(self, epsilon: float = 1e-6):
        """
        初始化DEA引擎

        Args:
            epsilon: 数值稳定性参数
        """
        self.epsilon = epsilon
        self.dmus = []  # 决策单元集合
        self.frontier = None  # 效率前沿面

    def add_dmu(self, dmu_id: int, inputs: np.ndarray, 
                good_outputs: np.ndarray, bad_outputs: np.ndarray,
                metadata: Dict = None):
        """
        添加决策单元(DMU)

        Args:
            dmu_id: 企业ID
            inputs: 投入向量 [能源消耗(kWh), 劳动力(人), 资本(万元)]
            good_outputs: 期望产出向量 [产量(吨), 产值(万元)]
            bad_outputs: 非期望产出向量 [碳排放(吨)]
            metadata: 附加信息
        """
        self.dmus.append({
            'id': dmu_id,
            'inputs': inputs.astype(float),
            'good_outputs': good_outputs.astype(float),
            'bad_outputs': bad_outputs.astype(float),
            'metadata': metadata or {}
        })

    def evaluate(self, target_dmu_id: int) -> DEAResult:
        """
        评估目标DMU的效率

        Args:
            target_dmu_id: 目标企业ID

        Returns:
            DEAResult: 评估结果
        """
        target = next(d for d in self.dmus if d['id'] == target_dmu_id)
        n = len(self.dmus)

        m = len(target['inputs'])       # 投入维度
        s1 = len(target['good_outputs'])  # 期望产出维度
        s2 = len(target['bad_outputs'])   # 非期望产出维度

        # 构建优化问题：最小化ρ
        # ρ = (1 - 1/m * Σ(s_i^- / x_i0)) / (1 + 1/(s1+s2) * (Σ(s_r^g / y_r0^g) + Σ(s_r^b / y_r0^b)))

        def objective(lambda_vars):
            """目标函数"""
            return -lambda_vars[-1]  # 最大化效率(转化为最小化-ρ)

        # 变量: [λ_1, ..., λ_n, ρ]
        x0 = np.ones(n + 1) / n
        x0[-1] = 0.5  # ρ初始值

        # 等式约束
        def equality_constraint(lambda_vars):
            lam = lambda_vars[:-1]
            rho = lambda_vars[-1]

            # 投入约束: Σλ_j * x_ij + s_i^- = x_i0
            # 期望产出约束: Σλ_j * y_rj^g - s_r^g = y_r0^g
            # 非期望产出约束: Σλ_j * y_rj^b + s_r^b = y_r0^b

            # 简化：使用线性规划求解
            constraints = []

            # 投入约束
            for i in range(m):
                val = sum(lam[j] * self.dmus[j]['inputs'][i] for j in range(n))
                constraints.append(val - target['inputs'][i])

            # 期望产出约束
            for r in range(s1):
                val = sum(lam[j] * self.dmus[j]['good_outputs'][r] for j in range(n))
                constraints.append(target['good_outputs'][r] - val)

            # 非期望产出约束
            for r in range(s2):
                val = sum(lam[j] * self.dmus[j]['bad_outputs'][r] for j in range(n))
                constraints.append(target['bad_outputs'][r] - val)

            return np.array(constraints)

        # 使用scipy优化(简化实现)
        # 实际生产环境应使用专业LP求解器(Gurobi/CPLEX)

        # 简化的效率计算：基于距离前沿面的比例
        efficiency = self._calculate_efficiency_simplified(target)

        # 计算改进路径
        improvement = self._calculate_improvement_path(target, efficiency)

        # 识别标杆企业
        peers = self._identify_peers(target)

        return DEAResult(
            efficiency_score=efficiency,
            target_reduction=improvement['carbon_reduction'],
            target_energy_save=improvement['energy_save'],
            improvement_path=improvement['path'],
            peer_companies=peers,
            projection_point=improvement['projection']
        )

    def _calculate_efficiency_simplified(self, target: Dict) -> float:
        """
        简化版效率计算(基于行业基准线)

        实际生产环境使用完整的SBM-DEA线性规划求解
        """
        # 计算各DMU的能源效率(产出/投入)
        efficiencies = []
        for dmu in self.dmus:
            energy_eff = dmu['good_outputs'][0] / (dmu['inputs'][0] + self.epsilon)
            carbon_eff = dmu['good_outputs'][0] / (dmu['bad_outputs'][0] + self.epsilon)
            efficiencies.append(energy_eff * carbon_eff)

        target_eff = target['good_outputs'][0] / (target['inputs'][0] + self.epsilon) * \
                     target['good_outputs'][0] / (target['bad_outputs'][0] + self.epsilon)

        max_eff = max(efficiencies)

        if max_eff < self.epsilon:
            return 1.0

        efficiency = target_eff / max_eff
        return min(efficiency, 1.0)

    def _calculate_improvement_path(self, target: Dict, 
                                     efficiency: float) -> Dict:
        """计算改进路径"""
        if efficiency >= 0.99:
            return {
                'carbon_reduction': 0.0,
                'energy_save': 0.0,
                'path': {},
                'projection': {}
            }

        # 目标：达到效率前沿
        # 需要减少的投入和产出
        input_reduction_ratio = 1 - efficiency

        energy_save = target['inputs'][0] * input_reduction_ratio * 0.3  # 30%通过节能
        carbon_reduction = target['bad_outputs'][0] * input_reduction_ratio

        path = {
            'energy_input': -energy_save,
            'carbon_output': -carbon_reduction,
            'labor_input': 0,
            'capital_input': 0
        }

        projection = {
            'energy': target['inputs'][0] - energy_save,
            'carbon': target['bad_outputs'][0] - carbon_reduction,
            'output': target['good_outputs'][0]
        }

        return {
            'carbon_reduction': carbon_reduction,
            'energy_save': energy_save,
            'path': path,
            'projection': projection
        }

    def _identify_peers(self, target: Dict) -> List[int]:
        """识别标杆企业(效率前沿面上的DMU)"""
        peers = []
        for dmu in self.dmus:
            if dmu['id'] == target['id']:
                continue
            # 简化的标杆识别：效率更高且相似规模
            if dmu['good_outputs'][0] >= target['good_outputs'][0] * 0.8 and \
               dmu['bad_outputs'][0] <= target['bad_outputs'][0] * 0.9:
                peers.append(dmu['id'])

        return peers[:3]  # 返回前3个标杆


class RetrofitOptimizer:
    """
    技改优化建议生成器

    基于DEA结果，结合设备技改数据库，
    自动生成个性化技改建议。
    """

    # 技改方案数据库
    RETROFIT_DATABASE = [
        {
            'name': '空压机余热回收改造',
            'category': '辅助设备',
            'investment': 15.0,      # 万元
            'annual_save': 12.0,     # 万元/年
            'carbon_reduce': 145.0,  # 吨CO2e/年
            'payback_period': 1.25,  # 年
            'applicable_processes': ['辅助'],
            'priority': 1
        },
        {
            'name': '定型机废气热回收',
            'category': '后整理',
            'investment': 20.0,
            'annual_save': 15.0,
            'carbon_reduce': 180.0,
            'payback_period': 1.33,
            'applicable_processes': ['后整理', '印染'],
            'priority': 2
        },
        {
            'name': 'LED照明全厂改造',
            'category': '照明',
            'investment': 5.0,
            'annual_save': 3.6,
            'carbon_reduce': 43.0,
            'payback_period': 1.39,
            'applicable_processes': ['全部'],
            'priority': 3
        },
        {
            'name': '细纱机变频改造',
            'category': '纺纱',
            'investment': 30.0,
            'annual_save': 18.0,
            'carbon_reduce': 216.0,
            'payback_period': 1.67,
            'applicable_processes': ['纺纱'],
            'priority': 4
        },
        {
            'name': '分布式光伏(屋顶2MW)',
            'category': '清洁能源',
            'investment': 80.0,
            'annual_save': 45.0,
            'carbon_reduce': 540.0,
            'payback_period': 1.78,
            'applicable_processes': ['全部'],
            'priority': 5
        },
        {
            'name': '数码印花替代传统印花',
            'category': '印染',
            'investment': 50.0,
            'annual_save': 25.0,
            'carbon_reduce': 300.0,
            'payback_period': 2.0,
            'applicable_processes': ['印染'],
            'priority': 6
        }
    ]

    def __init__(self, dea_result: DEAResult, company_processes: List[str],
                 budget_limit: Optional[float] = None):
        """
        初始化优化器

        Args:
            dea_result: DEA评估结果
            company_processes: 企业拥有的工序列表
            budget_limit: 预算上限(万元)
        """
        self.dea_result = dea_result
        self.company_processes = company_processes
        self.budget_limit = budget_limit

    def generate_recommendations(self, top_n: int = 3) -> List[Dict]:
        """
        生成技改建议列表

        Args:
            top_n: 返回前N条建议

        Returns:
            List[Dict]: 技改建议列表
        """
        recommendations = []

        for retrofit in self.RETROFIT_DATABASE:
            # 检查适用性
            applicable = self._check_applicability(retrofit)
            if not applicable:
                continue

            # 计算匹配度得分
            score = self._calculate_match_score(retrofit)

            # 检查预算
            if self.budget_limit and retrofit['investment'] > self.budget_limit:
                continue

            recommendation = {
                'priority': retrofit['priority'],
                'name': retrofit['name'],
                'category': retrofit['category'],
                'investment': retrofit['investment'],
                'annual_save': retrofit['annual_save'],
                'carbon_reduce': retrofit['carbon_reduce'],
                'payback_period': retrofit['payback_period'],
                'match_score': round(score, 2),
                'applicable': True,
                'roi': round(retrofit['annual_save'] / retrofit['investment'] * 100, 1),
                'carbon_roi': round(retrofit['carbon_reduce'] / retrofit['investment'], 1)
            }

            recommendations.append(recommendation)

        # 按匹配度排序
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)

        return recommendations[:top_n]

    def _check_applicability(self, retrofit: Dict) -> bool:
        """检查技改方案是否适用于当前企业"""
        applicable_processes = retrofit['applicable_processes']

        if '全部' in applicable_processes:
            return True

        for process in self.company_processes:
            if process in applicable_processes:
                return True

        return False

    def _calculate_match_score(self, retrofit: Dict) -> float:
        """
        计算技改方案匹配度得分

        考虑因素：
        - 回收期(越短越好)
        - 碳减排量(越多越好)
        - 投资回报率(越高越好)
        - 与企业效率差距的匹配度
        """
        # 回收期得分(满分30)
        payback_score = max(0, 30 - retrofit['payback_period'] * 10)

        # 碳减排得分(满分30)
        carbon_score = min(30, retrofit['carbon_reduce'] / 20)

        # ROI得分(满分20)
        roi_score = min(20, retrofit['annual_save'] / retrofit['investment'] * 5)

        # 效率匹配得分(满分20)
        efficiency_gap = 1 - self.dea_result.efficiency_score
        if efficiency_gap > 0.3:
            efficiency_score = 20  # 效率差距大，急需改造
        elif efficiency_gap > 0.15:
            efficiency_score = 15
        else:
            efficiency_score = 10

        return payback_score + carbon_score + roi_score + efficiency_score

    def generate_investment_plan(self, years: int = 3) -> Dict:
        """
        生成分年度投资计划

        Args:
            years: 规划年限

        Returns:
            Dict: 投资计划
        """
        recommendations = self.generate_recommendations(top_n=5)

        if not recommendations:
            return {'message': 'No applicable retrofit found'}

        total_investment = sum(r['investment'] for r in recommendations)
        total_annual_save = sum(r['annual_save'] for r in recommendations)
        total_carbon_reduce = sum(r['carbon_reduce'] for r in recommendations)

        # 分年度安排(优先短回收期项目)
        yearly_plan = []
        remaining_budget = self.budget_limit or float('inf')

        for year in range(1, years + 1):
            year_investment = 0
            year_projects = []

            for rec in recommendations:
                if rec['investment'] <= remaining_budget:
                    year_projects.append(rec)
                    year_investment += rec['investment']
                    remaining_budget -= rec['investment']

            yearly_plan.append({
                'year': year,
                'projects': year_projects,
                'investment': year_investment,
                'cumulative_investment': sum(y['investment'] for y in yearly_plan) + year_investment
            })

        return {
            'total_investment': total_investment,
            'total_annual_save': total_annual_save,
            'total_carbon_reduce': total_carbon_reduce,
            'average_payback': total_investment / total_annual_save if total_annual_save > 0 else 0,
            'yearly_plan': yearly_plan,
            'recommendations': recommendations
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 初始化DEA引擎
    dea = SBM_DEA_Engine()

    # 添加行业DMU(模拟数据)
    np.random.seed(42)
    for i in range(20):
        dea.add_dmu(
            dmu_id=i,
            inputs=np.array([100000 + np.random.randint(-20000, 20000),  # 能源消耗
                           100 + np.random.randint(-20, 20),             # 劳动力
                           500 + np.random.randint(-100, 100)]),          # 资本
            good_outputs=np.array([1200 + np.random.randint(-200, 200),  # 产量
                                  4800 + np.random.randint(-800, 800)]),  # 产值
            bad_outputs=np.array([5000 + np.random.randint(-1000, 1000)]),  # 碳排放
            metadata={'name': f'企业{i+1}'}
        )

    # 评估蓝天纺织(假设ID=0)
    result = dea.evaluate(target_dmu_id=0)

    print("=== DEA效率评估结果 ===")
    print(f"效率评分: {result.efficiency_score:.2f}")
    print(f"目标碳减排: {result.target_reduction:.1f} 吨CO2e/年")
    print(f"目标节能: {result.target_energy_save:.1f} kWh/年")
    print(f"标杆企业: {result.peer_companies}")

    # 生成技改建议
    optimizer = RetrofitOptimizer(
        dea_result=result,
        company_processes=['纺纱', '织造', '印染', '辅助'],
        budget_limit=100  # 万元
    )

    recommendations = optimizer.generate_recommendations(top_n=3)

    print("\n=== 优先技改建议 ===")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['name']}")
        print(f"   投资: {rec['investment']}万元 | 年节省: {rec['annual_save']}万元")
        print(f"   年减碳: {rec['carbon_reduce']}吨 | 回收期: {rec['payback_period']}年")
        print(f"   匹配度得分: {rec['match_score']}")

    # 生成投资计划
    plan = optimizer.generate_investment_plan(years=3)

    print(f"\n=== 三年投资计划 ===")
    print(f"总投资: {plan['total_investment']}万元")
    print(f"总年节省: {plan['total_annual_save']}万元")
    print(f"总减碳: {plan['total_carbon_reduce']}吨CO2e")
    print(f"平均回收期: {plan['average_payback']:.2f}年")
