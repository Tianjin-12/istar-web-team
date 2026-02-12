# mvp/dash_apps.py
from django_plotly_dash import DjangoDash
from dash.dependencies import Output, Input, State
import dash_bootstrap_components as dbc
import os
import json
import subprocess
import dash
from dash import dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np 
import requests
from datetime import timedelta,datetime
from django.urls import reverse
# 创建DjangoDash实例，名称必须与模板中的name属性匹配
app = DjangoDash('DashboardApp', external_stylesheets=["/static/css/bootstrap.min.css","/static/css/bootstrap-icons.css",  "/static/css/style.css"],
                  suppress_callback_exceptions=True,
                  serve_locally=True)

# --- 1. 多语言配置 ---
TRANSLATIONS = {
    'zh': {
        'nav_dash': '仪表盘', 'nav_rank': '行业榜单',
        'nav_wiki': 'AI 知识库', 'nav_setting': '系统设置',
        'login': '登录', 'welcome': '管理员', 'guest': '游客访问',
        # 搜索区
        'lbl_brand': '监测对象', 'ph_brand': '品牌名称 (如: Nike)',
        'lbl_kw': '核心关键词', 'ph_kw': '关键词 (如: 蓝牙耳机)',
        'lbl_link': '链接地址', 'ph_link': '请输入链接地址 (如: https://example.com)',
        'btn_start': '开始分析',
        # KPI & 图表
        'kpi_vis': '核心品牌提及概率(推荐性任务)', 'kpi_sent': '链接提及概率',
        'kpi_rev': '品牌提及概率（随意性任务）', 'chart_trend': '流量来源趋势分析',
        'chart_rank': '竞品可见度排行 ', 'chart_pie': 'AI 平台推荐份额',
        'download': '导出分析报告', 'lang_label': 'EN'
    },
    'en': {
        'nav_dash': 'Dashboard', 'nav_rank': 'Rankings',
        'nav_wiki': 'Wiki', 'nav_setting': 'Settings',
        'login': 'Login', 'welcome': 'Admin', 'guest': 'Guest Mode',
        # Search Section
        'lbl_brand': 'Target Brand', 'ph_brand': 'e.g. Nike',
        'lbl_kw': 'Keywords', 'ph_kw': 'e.g. Wireless Earbuds',
        'lbl_link': 'Link URL', 'ph_link': 'Enter link URL (e.g., https://example.com)',
        'btn_start': 'Analyze',
        # KPI & Charts
        'kpi_vis': 'Core Brand Mention percentage(recommend task)', 'kpi_sent': 'Link Mention percentage',
        'kpi_rev': 'Brand Mention percentage(random task)', 'chart_trend': 'Traffic Source Trends',
        'chart_rank': 'Visibility Ranking', 'chart_pie': 'AI Rec. Share',
        'download': 'Export Report', 'lang_label': '中'
    }
}
EXPLANATIONS = {
        'kpi-1': {
            'title': '核心品牌提及概率（推荐性任务）',
            'content': [
                html.P("该指标衡量AI在推荐任务中提及目标品牌的频率。"),
                html.P("数值越高，说明品牌在推荐场景下获得更多曝光。"),
                html.Ul([
                    html.Li("计算方式：AI推荐结果中品牌出现次数 / 总推荐次数"),
                    html.Li("影响因素：品牌知名度、产品竞争力、AI训练数据"),
                    html.Li("应用场景：评估品牌在AI推荐渠道的可见度")
                ])
            ]
        },
        'kpi-2': {
            'title': '链接提及概率',
            'content': [
                html.P("该指标衡量AI回复中包含目标链接的概率。"),
                html.P("数值越高，说明链接在AI对话中被引用越多。"),
                html.Ul([
                    html.Li("计算方式：包含链接的回复数 / 总回复数"),
                    html.Li("影响因素：链接质量、内容相关性、权威性"),
                    html.Li("应用场景：评估品牌官方内容在AI对话中的传播")
                ])
            ]
        },
        'kpi-3': {
            'title': '品牌提及概率（随意性任务）',
            'content': [
                html.P("该指标衡量AI在自由对话中提及目标品牌的概率。"),
                html.P("数值越高，说明品牌在用户日常对话中更常被提及。"),
                html.Ul([
                    html.Li("计算方式：AI提及品牌的对话数 / 总对话数"),
                    html.Li("影响因素：品牌知名度、用户口碑、社会影响力"),
                    html.Li("应用场景：评估品牌在用户自发讨论中的热度")
                ])
            ]
        },
        'chart-trend': {
            'title': '流量来源趋势分析',
            'content': [
                html.P("该图表展示了品牌流量和链接流量的时间趋势。"),
                html.P("红色区域表示品牌流量，蓝色区域表示链接流量。"),
                html.P("横轴：时间范围，纵轴：流量值")
            ]
        },
        'chart-pie': {
            'title': 'AI 平台推荐份额',
            'content': [
                html.P("该图表展示了不同 AI 平台的推荐份额占比。"),
                html.P("饼图的每个扇区代表一个平台的推荐比例。"),
                html.P("用于分析品牌在不同 AI 渠道的分布情况")
            ]
        },
        'chart-rank': {
            'title': '竞品可见度排行',
            'content': [
                html.P("该图表展示了品牌及其竞争对手的可见度排名。"),
                html.P("排名越高，表示品牌在 AI 对话中被提及的频率越高。"),
                html.P("前3名会特别标注显示")
            ]
        }
    }
def fetch_backend_data(brand_name=None, keyword_name=None,link_name=None):
    # API端点URL
    base_url = os.environ.get("https://istar-geo.com",'http://localhost:8000')
    api_url = f"{base_url}/api/dashboard-data/"
    # 构建查询参数
    params = {}
    if brand_name:
        params['brand_name'] = brand_name
    if keyword_name:
        params['keyword'] = keyword_name
    if link_name:
        params['link'] = link_name
    params['days'] = 30  # 默认获取30天的数据
    
    try:
        # 发送GET请求到API
        response = requests.get(api_url, params=params, timeout=100)
        
        # 检查响应状态
        if response.status_code == 200:
            # 解析JSON响应
            data = response.json()
            
            if data.get('status') == 'success':
                # 获取API数据
                api_data = data.get('data', [])
                
                if not api_data:
                    # 如果没有数据，返回特殊标记
                    return {"no_data": True, "brand_name": brand_name, "keyword_name": keyword_name,"link_name": link_name}
                
                # 将API数据转换为DataFrame
                df = pd.DataFrame(api_data)
                
                print(type(df))
                # 转换为网页需要的数据格式
                return df
            elif data.get('status') == 'no_data':
                # API返回没有数据的标记
                return {"no_data": True, "brand_name": data.get('brand_name', brand_name), "keyword_name": data.get('keyword_name', keyword_name),"link_name":data.get("link_name",link_name)}
            elif data.get('status') == 'no_order':
                # API返回没有订单的标记
                return {"no_order": True, "brand_name": data.get('brand_name', brand_name), "keyword": data.get('keyword', keyword_name)}
            else:
                # API返回错误
                print(f"API返回错误: {data.get('error', '未知错误')}")
                return {"no_data": True, "brand_name": brand_name, "keyword_name": keyword_name,"link_name":link_name}
        else:
            # HTTP错误
            print(f"HTTP错误 {response.status_code}: {response.text}")
            return {"no_data": True, "brand_name": brand_name, "keyword_name": keyword_name,"link_name":link_name}
            
    except requests.exceptions.RequestException as e:
        # 网络请求异常
        print(f"网络请求异常: {str(e)}")
        return {"no_data": True, "brand_name": brand_name, "keyword_name": keyword_name,"link_name":link_name}
    except Exception as e:
        # 其他异常
        print(f"处理数据时发生异常: {str(e)}")
        return {"no_data": True, "brand_name": brand_name, "keyword_name": keyword_name,"link_name":link_name}
 

def _convert_to_web_format(df,brand_name):
    # 处理趋势图数据
    if not isinstance(df, pd.DataFrame) or df.empty:
        return _get_default_data()
    if 'brand_name' not in df.columns or brand_name not in df['brand_name'].values:
        return _get_default_data()
    trend_data = {"Date": [],"Brand": [],"Link": []}
    focus_df = df[df["brand_name"] == brand_name]
    # 按日期分组并计算平均值
    
    focus_df["created_at"] = pd.to_datetime(focus_df["created_at"])
    df["created_at"] = pd.to_datetime(df["created_at"])
        # 获取最近的日期
    latest_date = focus_df["created_at"].max()    
        # 筛选出最近日期的数据
    latest_data = focus_df[focus_df["created_at"] == latest_date]   
        # 计算最近一天的平均值
    latest_r_brand_amount = latest_data['r_brand_amount'].mean()
    latest_nr_brand_amount = latest_data['nr_brand_amount'].mean()
    latest_link_amount = latest_data['link_amount'].mean()
    grouped = focus_df.groupby("created_at").agg({
            'r_brand_amount': 'mean',
            'link_amount': 'mean'
        }).reset_index()
        
        # 按日期排序
    grouped = grouped.sort_values("created_at")
        
        # 将日期转换为字符串格式
    trend_data["Date"] = grouped["created_at"].dt.strftime('%Y-%m-%d').tolist()
    trend_data["Brand"] = grouped['r_brand_amount'].tolist()
    trend_data["Link"] = grouped['link_amount'].tolist()
   
    # 处理排行榜数据
    ranking_data = pd.DataFrame(columns=['Brand', 'Score', 'Rank'])
    if 'brand_name' in df.columns and 'r_brand_amount' in df.columns and 'link_amount' in df.columns:
        # 按品牌分组，计算brand_amount和link_amount的平均值
        brand_stats = df.groupby('brand_name').agg({
            'r_brand_amount': 'mean',
            'link_amount': 'mean'
        }).reset_index()
        
        # 计算总分（brand_amount + link_amount）
        brand_stats['total_score'] = brand_stats['r_brand_amount'] + brand_stats['link_amount']
        
        # 按总分降序排列
        brand_stats = brand_stats.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        # 添加排名列（从1开始）
        brand_stats['rank'] = range(1, len(brand_stats) +1)
        
        # 重命名列以匹配期望的输出格式
        ranking_data = brand_stats.rename(columns={
            'brand_name': 'Brand',
            'total_score': 'Score',
            'rank': 'Rank'
        })
        
        # 选择需要的列
        ranking_data = ranking_data[['Brand', 'Score', 'Rank']]
    # 处理饼图数据
    pie_labels = brand_stats['brand_name'].tolist()
    pie_values = brand_stats['total_score'].tolist()
    return trend_data, ranking_data, pie_labels, pie_values,latest_r_brand_amount,latest_link_amount,latest_nr_brand_amount 

 

def _get_default_data():
    # 生成默认日期范围
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(29, -1, -1)]
    
    # 默认趋势数据
    trend_data = {
        "Date": dates,
        "Brand": [0] * 30,
        "Link": [0] * 30
    }
    
    # 默认排行榜数据
    rank_data = pd.DataFrame({
        'Brand': ['暂无数据'],
        'Score': [0],
        'Rank': [1]
    })
    
    # 默认饼图数据
    BrandsP = ['暂无数据']
    values = [100]
    
    latest_r_brand_amount = 0
    latest_nr_brand_amount = 0
    latest_link_amount = 0
    return trend_data, rank_data, BrandsP, values,latest_r_brand_amount,latest_link_amount,latest_nr_brand_amount 
# --- 2. 布局设计 ---
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id='lang-store', data='zh'),
    dcc.Store(id='app-state', data={
        'current_page': 'brand',
        'first_time': True,
        'brand_name': '',
        'keyword': '',
        'link': '',
    }),

    # 浮动翻译按钮
    html.Div([
        dbc.Checklist(
            id="lang-switch-visible",
            options=[{"label": "EN", "value": "en"}],
            value=[],
            switch=True,
            inline=True,
            style={"cursor": "pointer"}
        )
    ], id="lang-switch-container", style={
        "position": "fixed",
        "top": "15px",
        "right": "20px",
        "zIndex": "1000",
        "background": "rgba(255, 255, 255, 0.95)",
        "padding": "10px 15px",
        "borderRadius": "25px",
        "boxShadow": "0 2px 10px rgba(0, 0, 0, 0.15)"
    }),

    # === C. 主要内容区域 ===
    html.Div(id="page-content", children=[]),
    dbc.Container([
 
        # --- 搜索控制台 ---
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    # 监测对象
                    dbc.Col([
                        html.Label(
                            id="lbl-search-brand",
                            className="small fw-bold text-secondary mb-1"
                        ),
                        dbc.Input(
                            id="input-search-brand",
                            className="form-control-premium"
                        )
                    ], width=12, md=4),

                    # 核心关键词
                    dbc.Col([
                        html.Label(
                            id="lbl-search-kw",
                            className="small fw-bold text-secondary mb-1"
                        ),
                        dbc.Input(
                            id="input-search-kw",
                            className="form-control-premium"
                        ),
                        
                    ], width=12, md=4),
                    dbc.Col([html.Label(
                            id="lbl-search-link",
                            className="small fw-bold text-secondary mb-1"
                        ),
                        dbc.Input(
                            id="input-search-link",
                            className="form-control-premium"
                        )],width=12, md=4),
                    # 按钮 (底部对齐)
                    dbc.Col([
                        html.Label(" ", className="d-block mb-1"),
                        dbc.Button(
                            id="btn-analyze",
                            className="w-100 fw-bold shadow-sm mb-2",
                            color="dark",
                            n_clicks=0
                        ),
                        dbc.Button(
                            id="btn-download",
                            className="w-100 fw-bold shadow-sm",
                            color="primary",
                            n_clicks=0
                        )
                    ], width=12, md=4)
                ], className="g-3 align-items-end")
            ], className="p-4")
        ], className="premium-card mb-5 border-0 shadow-sm"),
 
        # 添加下载组件
        dcc.Download(id="download-dataframe-csv"),
 
        dcc.Loading(
            id="loading",
            type="cube",
            color="#cb0c9f",
            children=[
dbc.Row([
dbc.Col(dbc.Card([
    dbc.CardBody([
        html.Div([
            html.Div(
                id="label-kpi-1",
                className="card-label mb-2"
            ),
            html.Span("?", id="kpi-help-1",
                   style={
                       'position': 'absolute',
                       'top': '10px',
                       'right': '10px',
                       'width': '28px',
                       'height': '28px',
                       'background': "#0c0ccb",
                       'color': 'white',
                       'borderRadius': '50%',
                       'display': 'flex',
                       'alignItems': 'center',
                       'justifyContent': 'center',
                       'fontSize': '16px',
                       'fontWeight': 'bold',
                       'cursor': 'pointer',
                       'zIndex': 100
                   })
        ], style={'position': 'relative'}),
        html.Div([
            html.Span(
                    id="val-1",
                    className="metric-value"
            ),
            html.Span(id="bad-1")
        ], className="mt-4")
    ])
], className="premium-card h-100 delay-1 position-relative"),
width=12, lg=4, className="mb-4"),

dbc.Col(dbc.Card([
    dbc.CardBody([
        html.Div([
            html.Div(
                id="label-kpi-2",
                className="card-label mb-2"
            ),
            html.Span("?", id="kpi-help-2",
                   style={
                       'position': 'absolute',
                       'top': '10px',
                       'right': '10px',
                       'width': '28px',
                       'height': '28px',
                       'background': '#0c0ccb',
                       'color': 'white',
                       'borderRadius': '50%',
                       'display': 'flex',
                       'alignItems': 'center',
                       'justifyContent': 'center',
                       'fontSize': '16px',
                       'fontWeight': 'bold',
                       'cursor': 'pointer',
                       'zIndex': 100
                   })
        ], style={'position': 'relative'}),
        html.Div([
            html.Span(
                    id="val-2",#这里是2的数值
                    className="metric-value"
            ),
            html.Span(id="bad-2")#这里是上升和下降的下标
        ], className="mt-4")
    ])
], className="premium-card h-100 delay-2 position-relative"),
width=12, lg=4, className="mb-4"),

                    dbc.Col(dbc.Card([
    dbc.CardBody([
        html.Div([
            html.Div(
                id="label-kpi-3",
                className="card-label mb-2"
            ),
            html.Span("?", id="kpi-help-3",
                   style={
                       'position': 'absolute',
                       'top': '10px',
                       'right': '10px',
                       'width': '28px',
                       'height': '28px',
                       'background': '#0c0ccb',
                       'color': 'white',
                       'borderRadius': '50%',
                       'display': 'flex',
                       'alignItems': 'center',
                       'justifyContent': 'center',
                       'fontSize': '16px',
                       'fontWeight': 'bold',
                       'cursor': 'pointer',
                       'zIndex': 100
                   })
        ], style={'position': 'relative'}),
        html.Div([
            html.Span(
                    id="val-3",
                    className="metric-value"
            ),
            html.Span(id="bad-3")
        ], className="mt-4")
    ])
], className="premium-card h-100 delay-3 position-relative"),
                        width=12, lg=4, className="mb-4")
                ]),
 
                # 2. 图表区
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardHeader([
                            html.Span("流量来源趋势分析", id="title-trend",
                            style={'display': 'inline-block'}),
                            html.Span("?", id="chart-help-trend",
                            style={
                      'float': 'right',
                      'width': '24px',
                      'height': '24px',
                      'background': '#6c757d',
                      'color': 'white',
                      'borderRadius': '50%',
                      'display': 'flex',
                      'alignItems': 'center',
                      'justifyContent': 'center',
                      'fontSize': '14px',
                      'fontWeight': 'bold',
                      'cursor': 'pointer'
                            })
                    ],
                            className="bg-transparent border-0 fw-bold pt-4 ps-4"
                        ),
                        dbc.CardBody(
                            dcc.Graph(
                                id='chart-trend',
                                config={'displayModeBar': False},
                                style={"height": "320px"}
                            )
                        )
                    ], className="premium-card h-100"), width=12, lg=8, className="mb-4"),
 
                    dbc.Col(dbc.Card([
                        dbc.CardHeader(
                            [
            html.Span("流量来源比例分析", id="title-pie",
                  style={'display': 'inline-block'}),
            html.Span("?", id="chart-help-pie",
                  style={
                      'float': 'right',
                      'width': '24px',
                      'height': '24px',
                      'background': '#6c757d',
                      'color': 'white',
                      'borderRadius': '50%',
                      'display': 'flex',
                      'alignItems': 'center',
                      'justifyContent': 'center',
                      'fontSize': '14px',
                      'fontWeight': 'bold',
                      'cursor': 'pointer'
                  })
        ],
                            className="bg-transparent border-0 fw-bold pt-4 ps-4"
                        ),
                        dbc.CardBody(
                            dcc.Graph(
                                id='chart-pie',
                                config={'displayModeBar': False},
                                style={"height": "320px"}
                            )
                        )
                    ], className="premium-card h-100"), width=12, lg=4, className="mb-4")
                ]),
 
                # 3. 排行榜
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardHeader(
                            [
            html.Span("竞品比较", id="title-rank",
                  style={'display': 'inline-block'}),
            html.Span("?", id="chart-help-rank",
                  style={
                      'float': 'right',
                      'width': '24px',
                      'height': '24px',
                      'background': '#6c757d',
                      'color': 'white',
                      'borderRadius': '50%',
                      'display': 'flex',
                      'alignItems': 'center',
                      'justifyContent': 'center',
                      'fontSize': '14px',
                      'fontWeight': 'bold',
                      'cursor': 'pointer'
                  })
        ],
                            className="bg-transparent border-0 fw-bold pt-4 ps-4"
                        ),
                        dbc.CardBody(id='rank-container', className="p-4")
                    ], className="premium-card"), width=12)
                ])
            ]
        )
    ], fluid=True, className="px-lg-5 pb-5"),
    
    dcc.Interval(id="interval-trigger", interval=120 * 1000, n_intervals=0),#一个计时器
    
    html.Div(dash_table.DataTable(id='hidden'), style={'display': 'none'}),# 隐藏的 DataTable 防止 Import unused 报错
    
    html.Div(id='logout-redirect', style={'display': 'none'}),# 用于接收退出登录JavaScript的隐藏div

    # 引导弹窗（三步骤输入）
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("开始您的分析", className="fw-bold")),
            dbc.ModalBody(
                [
                    # 步骤1: 品牌名称
                    html.Div(id="guide-step-1", children=[
                        html.Label("请输入您要监测的品牌名称", className="mb-2 fw-bold"),
                        dbc.Input(
                            id="guide-input-brand",
                            placeholder="如：Nike",
                            className="mb-3"
                        ),
                        dbc.Button("下一步", id="guide-btn-next-1", className="w-100")
                    ]),
                    # 步骤2: 关键词（初始定义所有按钮）
                    html.Div(id="guide-step-2", children=[
                        html.Label("请输入核心关键词", className="mb-2 fw-bold"),
                        dbc.Input(id="guide-input-keyword", placeholder="如：蓝牙耳机", className="mb-3"),
                        html.Div([
                            dbc.Button("上一步", id="guide-btn-prev-2", className="me-2", color="secondary"),
                            dbc.Button("下一步", id="guide-btn-next-2", className="flex-grow-1")
                        ], className="d-flex")
                    ], style={'display': 'none'}),
                    # 步骤3: 链接（初始定义所有按钮）
                    html.Div(id="guide-step-3", children=[
                        html.Label("请输入信源链接（选填）", className="mb-2 fw-bold"),
                        dbc.Input(id="guide-input-link", placeholder="如：https://example.com", className="mb-3"),
                        html.Div([
                            dbc.Button("上一步", id="guide-btn-prev-3", className="me-2", color="secondary"),
                            dbc.Button("完成并开始分析", id="guide-btn-complete", className="flex-grow-1", color="primary")
                        ], className="d-flex")
                    ], style={'display': 'none'})
                ]
            ),
            dbc.ModalFooter(
                [
                    html.Button("不再提示", id="guide-btn-skip", className="btn btn-link me-auto")
                ]
            )
        ],
        id="guide-modal",
        is_open=False,
        centered=True,
        size="lg",
        backdrop="static"
    ),

    # 指标解释弹窗
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("指标说明", className="fw-bold")),
            dbc.ModalBody(
                html.Div(
                    id="kpi-explanation-content",
                    children=[]
                )
            ),
            dbc.ModalFooter(
                dbc.Button("关闭", id="kpi-modal-close", color="primary")
            )
        ],
        id="kpi-modal",
        is_open=False,
        centered=True,
        size="md"
    ),

    # 点击标识（用于识别点击的卡片）
    html.Div(id="kpi-click-trigger", style={'display': 'none'}),

    # 无订单提示模态窗口
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("提示", className="fw-bold")),
            dbc.ModalBody(
                html.Div([
                    html.P(id="no-order-message", className="mb-3"),
                    html.P(id="no-order-detail", className="text-muted small mb-3"),
                    html.A(
                        dbc.Button("创建订单", color="primary", className="w-100", size="lg"),
                        href="/api/redirect-to-create-order/",
                        id="create-order-link",
                        className="text-decoration-none"
                    )
                ])
            ),
        ],
        id="no-order-modal",
        is_open=False,
        backdrop="static",
        centered=True,
        size="lg"
    ),

    # 客户端脚本：登录状态检查和按钮更新
    html.Script("""
        (function() {
            // ========== 1. Toast 功能 ==========
            function showToast(message, duration) {
                const toast = document.getElementById('toast');
                const messageElement = document.getElementById('toast-message');
                
                messageElement.textContent = message;
                toast.classList.add('show');
                
                setTimeout(function() {
                    hideToast();
                }, duration || 5000);
            }
            
            function hideToast() {
                const toast = document.getElementById('toast');
                toast.style.animation = 'slideOut 0.3s ease-out forwards';
                setTimeout(function() {
                    toast.classList.remove('show');
                    toast.style.animation = '';
                }, 300);
            }
            

             // ========== 9. 初始化 ==========
             window.addEventListener('DOMContentLoaded', function() {
                 // 8. 绑定 KPI 卡片点击事件（用于显示指标解释弹窗）
                  const kpiOverlays = ['kpi-overlay-1', 'kpi-overlay-2', 'kpi-overlay-3'];
                  const kpiButtons = ['kpi-btn-1', 'kpi-btn-2', 'kpi-btn-3'];
                  kpiOverlays.forEach(function(overlayId, index) {
                      const overlay = document.getElementById(overlayId);
                      if (overlay) {
                          overlay.addEventListener('click', function() {
                              const kpiBtn = document.getElementById(kpiButtons[index]);
                              if (kpiBtn) {
                                  kpiBtn.click();
                              }
                          });
                      }
                  });

                 // 9. 绑定报告页面按钮事件
                 const downloadImageButton = document.getElementById('btn-download-image');
                 const copyLinkButton = document.getElementById('btn-copy-link');

                 if (downloadImageButton) {
                     downloadImageButton.addEventListener('click', function() {
                         downloadAsImage('png');
                     });
                 }

                 if (copyLinkButton) {
                     copyLinkButton.addEventListener('click', function() {
                         copyLink();
                     });
                 }
             });
             
             // ========== 10. 网页分享功能 ==========
             function downloadAsImage(format) {
                 showToast('正在生成图片，请稍候...');
                 
                 // 动态加载 html2canvas
                 const script = document.createElement('script');
                 script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                 script.onload = function() {
                     html2canvas(document.body).then(canvas => {
                         const link = document.createElement('a');
                         link.download = `brand_dashboard.${format.toLowerCase()}`;
                         link.href = canvas.toDataURL(`image/${format}`);
                         link.click();
                         showToast('图片下载成功！');
                     }).catch(err => {
                         console.error('下载图片失败:', err);
                         showToast('图片下载失败，请重试');
                     });
                 };
                 document.head.appendChild(script);
             }
             
             function copyLink() {
                 const url = window.location.href;
                 navigator.clipboard.writeText(url).then(() => {
                     showToast('链接已复制到剪贴板');
                 }).catch(err => {
                     console.error('复制链接失败:', err);
                     showToast('复制失败，请重试');
                 });
          }
      })();
    """),

    dcc.Download(id="download-report-csv"),
])


@app.callback(
    Output('app-state', 'data'),
    Input('url', 'pathname'),
    Input('url', 'search')
)
def update_app_state(pathname, search):
    from urllib.parse import parse_qs
    
    current_page = 'brand'
    
    if pathname.startswith('/dashboard/brand/'):
        current_page = 'brand'
    elif pathname.startswith('/dashboard/geo-evaluate/'):
        current_page = 'geo-evaluate'
    elif pathname.startswith('/dashboard/ai-toxic/'):
        current_page = 'ai-toxic'
    elif pathname.startswith('/dashboard/cgeo-wiki/'):
        current_page = 'cgeo-wiki'
    elif pathname.startswith('/dashboard/about/'):
        current_page = 'about'
    
    return {
        'current_page': current_page,
        'brand_name': '',
        'keyword': '',
        'link': ''
    }



# C. 数据图表渲染 (监听自动刷新 OR 手动点击分析)
@app.callback(
    [Output('val-1', 'children'), Output('bad-1', 'children'),
     Output('val-2', 'children'), Output('bad-2', 'children'),
     Output('val-3', 'children'), Output('bad-3', 'children'),
     Output('chart-trend', 'figure'), Output('chart-pie', 'figure'),
     Output('rank-container', 'children'),
     Output('no-order-modal', 'is_open'),
     Output('no-order-message', 'children'),
     Output('no-order-detail', 'children'),
     Output('create-order-link', 'href')],
     [Input('interval-trigger', 'n_intervals'),
      Input('btn-analyze', 'n_clicks')],

    [State('input-search-brand', 'value'),State('input-search-kw', 'value'),State('input-search-link', 'value')]
)
def update_metrics(n_interval, n_click, search_brand, search_keyword, search_link):
    # 检查是否是点击了分析按钮
    ctx = dash.callback_context
    if not ctx.triggered:
        return (dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, False, "", "", dash.no_update)

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 获取数据
    data = fetch_backend_data(brand_name=search_brand, keyword_name=search_keyword, link_name=search_link)

    # 检查是否没有订单
    if isinstance(data, dict) and data.get("no_order"):
        brand_name = data.get("brand_name", "")
        keyword_name = data.get("keyword", "")
        create_order_href = f"/api/redirect-to-create-order/?brand_name={brand_name}&keyword_name={keyword_name}"

        # 打开Modal，显示无订单提示
        return (
            "0%", "", "0%", "", "0%", "",
            go.Figure(), go.Figure(), "",
            True,  # 打开Modal
            f"系统中暂无关于 '{brand_name}' 和 '{keyword_name}' 的订单数据。",
            f"品牌：{brand_name} | 关键词：{keyword_name}",
            create_order_href
        )
    
    # 触发 fetch_data，传入搜索词
    trend, rank, pie_l, pie_v ,latest_r_brand_amount,latest_link_amount,latest_nr_brand_amount = _convert_to_web_format(data,search_brand)

    def badge(v):
        change = np.random.randint(-10, 20)
        if change > 0:
            color, icon = "#ecfdf5", "text-success ▲"
        else:
            color, icon = "#fef2f2", "text-danger ▼"

        return f"{v}%", html.Span(
            f"{icon} {abs(change)}%",
            className="trend-badge",
            style={"background": color}
        )

    # 1. 趋势图
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=trend["Date"], y=trend["Brand"], name="Brand Traffic",
        fill='tozeroy',
        line=dict(color="#d61616", width=3, shape='spline')
    ))
    fig1.add_trace(go.Scatter(
        x=trend["Date"], y=trend["Link"], name="Link Traffic",
        line=dict(color="#152FC2", width=3, shape='spline')
    ))
    fig1.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=10, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )

    # 2. 饼图
    fig2 = go.Figure(data=[go.Pie(
        labels=pie_l, values=pie_v, hole=.7,
        textinfo='percent', textposition='outside',
        marker=dict(colors=px.colors.qualitative.Pastel)
    )])
    fig2.update_layout(
        showlegend=True,
        margin=dict(l=20, r=20, t=0, b=20),
        legend=dict(orientation="h")
    )

    # 3. 排行榜
    ranks = []
    if isinstance(rank, pd.DataFrame) and not rank.empty:
        for _, r in rank.iterrows():
            rk = r['Rank']
            cls = f"rank-{rk}" if rk <= 3 else "rank-other"

        # 如果是用户搜索的品牌(有输入)，加重显示
            extra_style = {}
            brand_n = r['Brand']
            if brand_n == search_brand:
                extra_style = {"color": "#cb0c9f"}

            ranks.append(dbc.Row([
                dbc.Col(
                    html.Div(f"{rk}", className=f"rank-circle {cls}"),
                    width="auto"
                ),
                dbc.Col(
                    html.Span(
                        r['Brand'],
                        className="fw-bold ms-3",
                        style=extra_style
                    ),
                    width=True
                ),
                dbc.Col(
                    html.Span(f"{r['Score']}", className="fw-bold text-dark"),
                    width="auto"
                )
            ], className="ranking-item align-items-center"))
    else:
        ranks = [html.Div("暂无排行榜数据", className="text-center text-muted")]
    
    
    v1, b1 = badge(latest_r_brand_amount)
    v2, b2 = badge(latest_link_amount)
    v3, b3 = badge(latest_nr_brand_amount)

    return v1, b1, v2, b2, v3, b3, fig1, fig2, ranks, False, "", "", dash.no_update


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download", "n_clicks"),
    [State('input-search-brand', 'value'),
     State('input-search-kw', 'value'),
     State('input-search-link','value')],
    prevent_initial_call=True,
)
def export_csv(n_clicks, search_brand, search_keyword,search_link):
    # 获取真实数据
    df = fetch_backend_data(brand_name=search_brand, keyword_name=search_keyword,link_name=search_link)
    
    # 检查返回的数据类型
    if isinstance(df, list) and len(df) > 0 and df[0] == 404:
        # 如果返回的是错误码
        df = pd.DataFrame({'Error': ['Data not found or API error']})
        #deflaut情况
    elif isinstance(df, tuple):
        df = pd.DataFrame({'Info': ['No data available for export']})
    elif df is None or df.empty:
        # 如果数据为空
        df = pd.DataFrame({'Info': ['No data available for export']})
    
    # 确保df是DataFrame类型
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame({'Info': ['Unexpected data format']})
    
    # 返回CSV数据以供下载
    return dcc.send_data_frame(df.to_csv, "dashboard_data.csv", index=False)

# --- 2. 多语言更新回调 ---
@app.callback(
    [Output('lbl-search-brand', 'children'),
     Output('input-search-brand', 'placeholder'),
     Output('lbl-search-kw', 'children'),
     Output('input-search-kw', 'placeholder'),
     Output('lbl-search-link', 'children'),
     Output('input-search-link', 'placeholder'),
     Output('btn-analyze', 'children'),
     Output('btn-download', 'children'),
     Output('label-kpi-1', 'children'),
     Output('label-kpi-2', 'children'),
     Output('label-kpi-3', 'children'),
     Output('title-trend', 'children'),
     Output('title-pie', 'children'),
     Output('title-rank', 'children'),
     Output('lang-store', 'data')],
     Input('lang-store', 'data'),
     Input('lang-switch-visible', 'value'),
     State('lang-store', 'data'),
     prevent_initial_call=False
)
def update_language(lang, switch_value, current_lang):
    ctx = dash.callback_context

    # 判断触发源
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # 如果是开关切换，切换语言
        if trigger_id == 'lang-switch-visible':
            if not current_lang:
                current_lang = 'zh'
            lang = 'en' if current_lang == 'zh' else 'zh'
        else:
            # 如果是 lang-store 变化，直接使用传入的语言
            if not lang:
                lang = 'zh'
    else:
        lang = 'zh'

    t = TRANSLATIONS.get(lang, TRANSLATIONS['zh'])

    return (
        t['lbl_brand'], t['ph_brand'],
        t['lbl_kw'], t['ph_kw'],
        t['lbl_link'], t['ph_link'],
        t['btn_start'], t['download'],
        t['kpi_vis'], t['kpi_sent'], t['kpi_rev'],
        t['chart_trend'], t['chart_pie'], t['chart_rank'],
        lang
    )



# 指标解释弹窗内容更新
@app.callback(
    Output('kpi-modal', 'is_open'),
    Output('kpi-explanation-content', 'children'),
    Input('kpi-help-1', 'n_clicks'),
    Input('kpi-help-2', 'n_clicks'),
    Input('kpi-help-3', 'n_clicks'),
    Input('chart-help-trend', 'n_clicks'),
    Input('chart-help-pie', 'n_clicks'),
    Input('chart-help-rank', 'n_clicks'),
    Input('kpi-modal-close', 'n_clicks'),
    State('kpi-modal', 'is_open'),
    prevent_initial_call=True
)
def show_kpi_explanation(kpi1, kpi2, kpi3, chart_trend, chart_pie, chart_rank, close_btn, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # 关闭按钮
    if trigger_id == 'kpi-modal-close':
        return False, dash.no_update
    
    # 根据触发按钮返回对应内容
    explanations = {
        'kpi-help-1': EXPLANATIONS['kpi-1'],
        'kpi-help-2': EXPLANATIONS['kpi-2'],
        'kpi-help-3': EXPLANATIONS['kpi-3'],
        'chart-help-trend': EXPLANATIONS['chart-trend'],
        'chart-help-pie': EXPLANATIONS['chart-pie'],
        'chart-help-rank': EXPLANATIONS['chart-rank']
    }
    
    if trigger_id in explanations:
        exp = explanations[trigger_id]
        content = [
            html.H4(exp['title'], className="mb-3"),
            html.Div(exp['content'])
        ]
        return True, content
    
    return is_open, dash.no_update



