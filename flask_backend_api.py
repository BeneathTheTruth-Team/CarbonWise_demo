"""
碳智评 - Flask后端API服务
功能：RESTful API、银行端对接、OAuth2.0认证、数据脱敏
技术栈：Flask + MySQL + Redis + JWT
"""

from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import redis

# ==================== 应用配置 ====================

app = Flask(__name__)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'mysql+pymysql://carbonwise:password@localhost/carbonwise_db?charset=utf8mb4'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 20
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 30

# JWT配置
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# 初始化扩展
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Redis缓存
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# 限流器
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri=os.getenv('REDIS_URL', 'redis://localhost:6379')
)

# ==================== 数据库模型 ====================

class User(db.Model):
    """用户表(纺织企业/银行/管理员)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('enterprise', 'bank', 'admin'), default='enterprise')
    company_name = db.Column(db.String(200))
    credit_code = db.Column(db.String(50))  # 统一社会信用代码
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # 关系
    calculations = db.relationship('CarbonCalculation', backref='user', lazy='dynamic')
    api_keys = db.relationship('ApiKey', backref='user', lazy='dynamic')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'user_type': self.user_type,
            'company_name': self.company_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Equipment(db.Model):
    """设备参数表(脱敏存储)"""
    __tablename__ = 'equipments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # 设备参数(非敏感)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    rated_power = db.Column(db.Float, nullable=False)
    daily_hours = db.Column(db.Float, default=24.0)
    load_factor = db.Column(db.Float, default=0.8)
    years_used = db.Column(db.Integer, default=1)
    process = db.Column(db.String(50))

    # 数据脱敏标识
    data_hash = db.Column(db.String(64))  # 参数哈希，用于完整性校验
    is_anonymized = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def compute_hash(self) -> str:
        """计算设备参数哈希值"""
        data = f"{self.name}{self.model}{self.quantity}{self.rated_power}{self.daily_hours}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model,
            'quantity': self.quantity,
            'rated_power': self.rated_power,
            'daily_hours': self.daily_hours,
            'load_factor': self.load_factor,
            'years_used': self.years_used,
            'process': self.process
        }


class CarbonCalculation(db.Model):
    """碳核算结果表"""
    __tablename__ = 'calculations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # 核算结果
    annual_emission = db.Column(db.Float, nullable=False)
    intensity = db.Column(db.Float, nullable=False)
    env_cost = db.Column(db.Float)
    uncertainty = db.Column(db.Float)
    credit_rating = db.Column(db.String(10))
    benchmark = db.Column(db.Float, default=5.5)

    # 核算参数快照
    emission_factor_version = db.Column(db.String(20))
    carbon_price = db.Column(db.Float, default=80.0)
    annual_output = db.Column(db.Float, default=1200.0)

    # 报告生成状态
    report_status = db.Column(db.Enum('pending', 'generated', 'downloaded'), 
                               default='pending')
    report_url = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'annual_emission': round(self.annual_emission, 2),
            'intensity': round(self.intensity, 2),
            'env_cost': round(self.env_cost, 2) if self.env_cost else None,
            'uncertainty': round(self.uncertainty, 2) if self.uncertainty else None,
            'credit_rating': self.credit_rating,
            'benchmark': self.benchmark,
            'report_status': self.report_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ApiKey(db.Model):
    """银行端API密钥表"""
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    key_hash = db.Column(db.String(255), nullable=False, unique=True)
    key_prefix = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(100))
    permissions = db.Column(db.JSON, default=list)
    is_active = db.Column(db.Boolean, default=True)
    last_used_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_key() -> tuple:
        """生成API密钥(返回原始密钥和哈希)"""
        raw_key = f"cw_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:10]
        return raw_key, key_hash, prefix


class AuditLog(db.Model):
    """审计日志表"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== 认证装饰器 ====================

def bank_required(fn):
    """银行端权限校验装饰器"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or current_user.user_type != 'bank':
            return jsonify({'error': 'Bank access required'}), 403
        g.current_user = current_user
        return fn(*args, **kwargs)
    return wrapper


def api_key_required(fn):
    """API密钥认证装饰器(银行端批量接口)"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_obj = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()

        if not api_key_obj:
            return jsonify({'error': 'Invalid API key'}), 401

        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            return jsonify({'error': 'API key expired'}), 401

        # 更新最后使用时间
        api_key_obj.last_used_at = datetime.utcnow()
        db.session.commit()

        g.current_user = User.query.get(api_key_obj.user_id)
        g.api_key = api_key_obj

        return fn(*args, **kwargs)
    return wrapper


# ==================== API路由 ====================

@app.route('/api/v1/auth/register', methods=['POST'])
@limiter.limit("10 per minute")
def register():
    """用户注册"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    user = User(
        username=data['username'],
        email=data.get('email', ''),
        user_type=data.get('user_type', 'enterprise'),
        company_name=data.get('company_name', '')
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    # 记录审计日志
    log = AuditLog(
        user_id=user.id,
        action='REGISTER',
        resource_type='user',
        resource_id=user.id,
        ip_address=request.remote_addr,
        details={'username': user.username}
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("20 per minute")
def login():
    """用户登录，返回JWT令牌"""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account deactivated'}), 403

    user.last_login = datetime.utcnow()
    db.session.commit()

    access_token = create_access_token(identity=user.id)

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 28800,  # 8小时
        'user': user.to_dict()
    }), 200


@app.route('/api/v1/equipment', methods=['POST'])
@jwt_required()
@limiter.limit("100 per hour")
def add_equipment():
    """添加设备参数"""
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('equipments'):
        return jsonify({'error': 'Equipment data required'}), 400

    added = []
    for eq_data in data['equipments']:
        equipment = Equipment(
            user_id=current_user_id,
            name=eq_data.get('name'),
            model=eq_data.get('model'),
            quantity=eq_data.get('quantity', 1),
            rated_power=eq_data.get('rated_power'),
            daily_hours=eq_data.get('daily_hours', 24.0),
            load_factor=eq_data.get('load_factor', 0.8),
            years_used=eq_data.get('years_used', 1),
            process=eq_data.get('process')
        )
        equipment.data_hash = equipment.compute_hash()
        db.session.add(equipment)
        added.append(equipment)

    db.session.commit()

    return jsonify({
        'message': f'{len(added)} equipment added',
        'equipments': [eq.to_dict() for eq in added]
    }), 201


@app.route('/api/v1/calculation', methods=['POST'])
@jwt_required()
@limiter.limit("50 per hour")
def calculate_carbon():
    """
    执行碳核算

    Request Body:
        {
            "equipment_ids": [1, 2, 3],
            "annual_output": 1200,
            "region": "华东",
            "carbon_price": 80.0
        }
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()

    equipment_ids = data.get('equipment_ids', [])
    annual_output = data.get('annual_output', 1200.0)
    region = data.get('region', '华东')
    carbon_price = data.get('carbon_price', 80.0)

    # 查询设备
    equipments = Equipment.query.filter(
        Equipment.id.in_(equipment_ids),
        Equipment.user_id == current_user_id
    ).all()

    if len(equipments) != len(equipment_ids):
        return jsonify({'error': 'Some equipment not found or not owned'}), 404

    # 获取排放因子(从Redis缓存或数据库)
    ef_key = f"emission_factor:{region}"
    ef_data = redis_client.get(ef_key)

    if ef_data:
        ef = json.loads(ef_data)
    else:
        # 默认华东电网因子
        ef = {'ef_grid': 0.5708, 'ef_gas': 2.162, 'ef_steam': 0.15, 'ef_diesel': 2.68}
        redis_client.setex(ef_key, 3600, json.dumps(ef))

    # 执行核算(调用C++引擎的Python封装)
    result = perform_calculation(equipments, ef, annual_output, carbon_price)

    # 保存结果
    calculation = CarbonCalculation(
        user_id=current_user_id,
        annual_emission=result['annual_emission'],
        intensity=result['intensity'],
        env_cost=result['env_cost'],
        uncertainty=result['uncertainty'],
        credit_rating=result['credit_rating'],
        emission_factor_version='2024-v1',
        carbon_price=carbon_price,
        annual_output=annual_output
    )
    db.session.add(calculation)
    db.session.commit()

    return jsonify({
        'calculation_id': calculation.id,
        'result': calculation.to_dict(),
        'process_breakdown': result.get('process_breakdown', {})
    }), 200


def perform_calculation(equipments, ef, annual_output, carbon_price):
    """
    执行碳核算计算(Python实现，生产环境调用C++引擎)

    Returns:
        Dict: 核算结果
    """
    daily_emission = 0.0
    process_emissions = {}

    for eq in equipments:
        # 老化修正
        if eq.years_used <= 3:
            k_corr = 1.00
        elif eq.years_used <= 5:
            k_corr = 1.05
        elif eq.years_used <= 8:
            k_corr = 1.08
        else:
            k_corr = 1.12

        daily_eq = eq.quantity * eq.rated_power * eq.daily_hours * eq.load_factor * k_corr * ef['ef_grid']
        daily_emission += daily_eq

        process = eq.process or '其他'
        process_emissions[process] = process_emissions.get(process, 0) + daily_eq

    annual_emission = daily_emission * 330 / 1000.0  # 转换为吨
    intensity = annual_emission / annual_output
    env_cost = annual_emission * carbon_price

    # 碳效评级
    benchmark = 5.5
    ratio = intensity / benchmark
    if ratio < 0.6:
        rating = 'AAA'
    elif ratio < 0.8:
        rating = 'AA'
    elif ratio < 1.0:
        rating = 'A'
    elif ratio < 1.3:
        rating = 'BBB'
    else:
        rating = 'BB'

    # 简化不确定性计算
    uncertainty = intensity * 0.06  # 约6%不确定性

    return {
        'annual_emission': annual_emission,
        'intensity': intensity,
        'env_cost': env_cost,
        'uncertainty': uncertainty,
        'credit_rating': rating,
        'process_breakdown': process_emissions
    }


# ==================== 银行端API ====================

@app.route('/api/v1/bank/rating', methods=['POST'])
@api_key_required
@limiter.limit("500 per hour")
def bank_credit_rating():
    """
    银行端碳效评级查询

    Headers:
        X-API-Key: 银行API密钥

    Request Body:
        {
            "company_credit_code": "91330600MA2D8XXXX",
            "report_type": "full"  // full|summary
        }
    """
    data = request.get_json()
    credit_code = data.get('company_credit_code')
    report_type = data.get('report_type', 'summary')

    if not credit_code:
        return jsonify({'error': 'Company credit code required'}), 400

    # 查询企业最新核算结果(脱敏)
    user = User.query.filter_by(credit_code=credit_code).first()
    if not user:
        return jsonify({'error': 'Company not found'}), 404

    latest_calc = CarbonCalculation.query.filter_by(user_id=user.id)\
        .order_by(CarbonCalculation.created_at.desc()).first()

    if not latest_calc:
        return jsonify({'error': 'No carbon calculation found for this company'}), 404

    # 数据脱敏处理
    if report_type == 'summary':
        response = {
            'company_name': user.company_name,
            'credit_code': credit_code[:6] + '****' + credit_code[-4:],
            'credit_rating': latest_calc.credit_rating,
            'intensity_category': self_categorize(latest_calc.intensity),
            'rating_date': latest_calc.created_at.isoformat() if latest_calc.created_at else None,
            'report_id': f"CW-{latest_calc.id:08d}",
            'verification_status': 'self_declared'
        }
    else:
        response = {
            'company_name': user.company_name,
            'credit_code': credit_code[:6] + '****' + credit_code[-4:],
            'credit_rating': latest_calc.credit_rating,
            'intensity': round(latest_calc.intensity, 2),
            'annual_emission': round(latest_calc.annual_emission, 2),
            'env_cost_ratio': round(latest_calc.env_cost / (user.company_name.__len__() * 1000), 2),
            'uncertainty': round(latest_calc.uncertainty, 2),
            'benchmark': latest_calc.benchmark,
            'rating_date': latest_calc.created_at.isoformat() if latest_calc.created_at else None,
            'report_id': f"CW-{latest_calc.id:08d}",
            'verification_status': 'self_declared'
        }

    # 记录银行查询日志
    log = AuditLog(
        user_id=g.current_user.id,
        action='BANK_QUERY',
        resource_type='calculation',
        resource_id=latest_calc.id,
        ip_address=request.remote_addr,
        details={
            'bank': g.current_user.company_name,
            'target_company': credit_code,
            'report_type': report_type
        }
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(response), 200


def self_categorize(intensity: float) -> str:
    """碳排放强度分类"""
    if intensity < 4.0:
        return 'low'
    elif intensity < 6.0:
        return 'medium'
    else:
        return 'high'


@app.route('/api/v1/bank/batch-screening', methods=['POST'])
@api_key_required
@limiter.limit("100 per hour")
def bank_batch_screening():
    """
    银行端批量筛选AA级以上企业

    Request Body:
        {
            "filters": {
                "region": "浙江",
                "industry": "纺织",
                "min_rating": "AA"
            },
            "page": 1,
            "per_page": 50
        }
    """
    data = request.get_json()
    filters = data.get('filters', {})
    page = data.get('page', 1)
    per_page = min(data.get('per_page', 50), 100)

    min_rating = filters.get('min_rating', 'AA')

    # 评级映射为数值
    rating_order = {'AAA': 5, 'AA': 4, 'A': 3, 'BBB': 2, 'BB': 1}
    min_score = rating_order.get(min_rating, 4)

    # 查询符合条件的最新核算
    query = db.session.query(
        User.company_name,
        User.credit_code,
        CarbonCalculation.credit_rating,
        CarbonCalculation.intensity,
        CarbonCalculation.created_at
    ).join(CarbonCalculation, User.id == CarbonCalculation.user_id)\
     .filter(CarbonCalculation.credit_rating.in_(
         [k for k, v in rating_order.items() if v >= min_score]
     ))\
     .order_by(CarbonCalculation.created_at.desc())

    # 分页
    total = query.count()
    results = query.offset((page - 1) * per_page).limit(per_page).all()

    companies = []
    for row in results:
        companies.append({
            'company_name': row[0],
            'credit_code': row[1][:6] + '****' + row[1][-4:] if row[1] else None,
            'credit_rating': row[2],
            'intensity': round(row[3], 2),
            'rating_date': row[4].isoformat() if row[4] else None
        })

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'companies': companies,
        'query_id': f"QS-{secrets.token_hex(8)}"
    }), 200


# ==================== 管理接口 ====================

@app.route('/api/v1/admin/audit-logs', methods=['GET'])
@jwt_required()
def get_audit_logs():
    """获取审计日志(管理员)"""
    current_user = User.query.get(get_jwt_identity())
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    logs = AuditLog.query.order_by(AuditLog.created_at.desc())\
        .offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'logs': [{
            'id': log.id,
            'action': log.action,
            'user_id': log.user_id,
            'ip_address': log.ip_address,
            'details': log.details,
            'created_at': log.created_at.isoformat() if log.created_at else None
        } for log in logs]
    }), 200


# ==================== 健康检查 ====================

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """服务健康检查"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': 'connected' if db.session.execute('SELECT 1').scalar() else 'error',
            'redis': 'connected' if redis_client.ping() else 'error'
        }
    }), 200


# ==================== 错误处理 ====================

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'retry_after': e.description}), 429

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# ==================== 启动 ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # 生产环境使用Gunicorn部署
    # gunicorn -w 4 -b 0.0.0.0:5000 carbon_api:app
    app.run(host='0.0.0.0', port=5000, debug=False)
