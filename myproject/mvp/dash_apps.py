from django_plotly_dash import DjangoDash
from dash.dependencies import Output, Input, State
import dash_bootstrap_components as dbc
import os
import json
import dash
from dash import dcc, html, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
from datetime import timedelta, datetime

app = DjangoDash(
    "DashboardApp",
    external_stylesheets=[
        "/static/css/bootstrap.min.css",
        "/static/css/bootstrap-icons.css",
        "/static/css/style.css",
    ],
    external_scripts=["/static/js/bootstrap.bundle.min.js"],
    suppress_callback_exceptions=True,
    serve_locally=True,
)

EXPLANATIONS = {
    "kpi-1": {
        "title": "核心品牌提及概率（推荐性任务）",
        "content": [
            html.P("该指标衡量AI在推荐任务中提及目标品牌的频率。"),
            html.P("数值越高，说明品牌在推荐场景下获得更多曝光。"),
            html.Ul(
                [
                    html.Li("计算方式：AI推荐结果中品牌出现次数 / 总推荐次数"),
                    html.Li("影响因素：品牌知名度、产品竞争力、AI训练数据"),
                    html.Li("应用场景：评估品牌在AI推荐渠道的可见度"),
                ]
            ),
        ],
    },
    "kpi-2": {
        "title": "高相关信源占比",
        "content": [
            html.P("该指标衡量AI回复中引用的链接来自高相关信源的比例。"),
            html.P("高相关信源包括：官方媒体、知名媒体、行业垂直媒体。"),
            html.Ul(
                [
                    html.Li("计算方式：高相关信源链接数 / 总链接数 × 100%"),
                    html.Li("影响因素：信源权威性、内容质量、行业相关性"),
                    html.Li("应用场景：评估品牌在AI对话中被引用的信源质量"),
                ]
            ),
        ],
    },
    "kpi-3": {
        "title": "品牌提及概率（随意性任务）",
        "content": [
            html.P("该指标衡量AI在自由对话中提及目标品牌的概率。"),
            html.P("数值越高，说明品牌在用户日常对话中更常被提及。"),
            html.Ul(
                [
                    html.Li("计算方式：AI提及品牌的对话数 / 总对话数"),
                    html.Li("影响因素：品牌知名度、用户口碑、社会影响力"),
                    html.Li("应用场景：评估品牌在用户自发讨论中的热度"),
                ]
            ),
        ],
    },
    "chart-trend": {
        "title": "流量来源趋势分析",
        "content": [
            html.P("该图表展示了品牌流量和链接流量的时间趋势。"),
            html.P("红色区域表示品牌流量，蓝色区域表示链接流量。"),
            html.P("横轴：时间范围，纵轴：流量值"),
        ],
    },
    "chart-pie": {
        "title": "AI 平台推荐份额",
        "content": [
            html.P("该图表展示了不同 AI 平台的推荐份额占比。"),
            html.P("饼图的每个扇区代表一个平台的推荐比例。"),
            html.P("用于分析品牌在不同 AI 渠道的分布情况"),
        ],
    },
    "chart-rank": {
        "title": "竞品可见度排行",
        "content": [
            html.P("该图表展示了品牌及其竞争对手的可见度排名。"),
            html.P("排名越高，表示品牌在 AI 对话中被提及的频率越高。"),
            html.P("前3名会特别标注显示"),
        ],
    },
    "chart-treemap": {
        "title": "信源分类分析",
        "content": [
            html.P("该图表展示了AI回复中引用链接的信源分类分布。"),
            html.P("方块面积越大，表示该分类的链接数量越多。"),
            html.Ul(
                [
                    html.Li("颜色深浅表示相关度等级：绿色为高相关，灰色为低相关"),
                    html.Li("高相关信源包括：官方媒体、知名媒体、行业垂直媒体"),
                    html.Li("应用场景：评估品牌在AI对话中被引用的信源质量分布"),
                ]
            ),
        ],
    },
}


def fetch_backend_data(brand_name=None, keyword_name=None, link_name=None):
    base_url = os.environ.get("WEBSITE_URL", "http://localhost:8000")
    api_url = f"{base_url}/api/dashboard-data/"
    params = {}
    if brand_name:
        params["brand_name"] = brand_name
    if keyword_name:
        params["keyword"] = keyword_name
    if link_name:
        params["link"] = link_name
    params["days"] = 30

    try:
        response = requests.get(api_url, params=params, timeout=100)

        if response.status_code == 200:
            data = response.json()

            if data.get("status") == "success":
                api_data = data.get("data", [])

                if not api_data:
                    return {
                        "no_data": True,
                        "brand_name": brand_name,
                        "keyword_name": keyword_name,
                        "link_name": link_name,
                    }

                df = pd.DataFrame(api_data)
                return df
            elif data.get("status") == "no_data":
                return {
                    "no_data": True,
                    "brand_name": data.get("brand_name", brand_name),
                    "keyword_name": data.get("keyword_name", keyword_name),
                    "link_name": data.get("link_name", link_name),
                }
            elif data.get("status") == "no_order":
                return {
                    "no_order": True,
                    "brand_name": data.get("brand_name", brand_name),
                    "keyword": data.get("keyword", keyword_name),
                }
            else:
                print(f"API返回错误: {data.get('error', '未知错误')}")
                return {
                    "no_data": True,
                    "brand_name": brand_name,
                    "keyword_name": keyword_name,
                    "link_name": link_name,
                }
        else:
            print(f"HTTP错误 {response.status_code}: {response.text}")
            return {
                "no_data": True,
                "brand_name": brand_name,
                "keyword_name": keyword_name,
                "link_name": link_name,
            }

    except requests.exceptions.RequestException as e:
        print(f"网络请求异常: {str(e)}")
        return {
            "no_data": True,
            "brand_name": brand_name,
            "keyword_name": keyword_name,
            "link_name": link_name,
        }
    except Exception as e:
        print(f"处理数据时发生异常: {str(e)}")
        return {
            "no_data": True,
            "brand_name": brand_name,
            "keyword_name": keyword_name,
            "link_name": link_name,
        }


def _convert_to_web_format(df, brand_name):
    if not isinstance(df, pd.DataFrame):
        return _get_default_data()
    if "brand_name" not in df.columns or brand_name not in df["brand_name"].values:
        return _get_default_data()
    trend_data = {"Date": [], "Brand": [], "Link": []}
    focus_df = df[
        df["brand_name"].str.contains(brand_name, case=False, na=False)
    ].copy()

    focus_df["created_at"] = pd.to_datetime(focus_df["created_at"])
    df_copy = df.copy()
    df_copy["created_at"] = pd.to_datetime(df_copy["created_at"])

    latest_date = focus_df["created_at"].max()
    latest_data = focus_df[focus_df["created_at"] == latest_date]

    latest_r_brand_amount = latest_data["r_brand_amount"].mean()
    latest_nr_brand_amount = latest_data["nr_brand_amount"].mean()
    latest_link_amount = latest_data["link_amount"].mean()

    week_ago_date = latest_date - timedelta(days=7)
    week_ago_data = focus_df[focus_df["created_at"] == week_ago_date]

    if not week_ago_data.empty:
        prev_r_brand_amount = week_ago_data["r_brand_amount"].mean()
        prev_nr_brand_amount = week_ago_data["nr_brand_amount"].mean()
        prev_link_amount = week_ago_data["link_amount"].mean()

        change_r_brand = (
            ((latest_r_brand_amount - prev_r_brand_amount) / prev_r_brand_amount * 100)
            if prev_r_brand_amount != 0
            else 0
        )
        change_nr_brand = (
            (
                (latest_nr_brand_amount - prev_nr_brand_amount)
                / prev_nr_brand_amount
                * 100
            )
            if prev_nr_brand_amount != 0
            else 0
        )
        change_link = (
            ((latest_link_amount - prev_link_amount) / prev_link_amount * 100)
            if prev_link_amount != 0
            else 0
        )
    else:
        change_r_brand = 0
        change_nr_brand = 0
        change_link = 0

    grouped = (
        focus_df.groupby("created_at")
        .agg({"r_brand_amount": "mean", "link_amount": "mean"})
        .reset_index()
    )

    grouped = grouped.sort_values("created_at")

    trend_data["Date"] = grouped["created_at"].dt.strftime("%Y-%m-%d").tolist()
    trend_data["Brand"] = grouped["r_brand_amount"].tolist()
    trend_data["Link"] = grouped["link_amount"].tolist()

    ranking_data = pd.DataFrame(columns=["Brand", "Score", "Rank"])
    brand_stats = pd.DataFrame(columns=["brand_name", "r_brand_amount", "link_amount"])
    if (
        "brand_name" in df_copy.columns
        and "r_brand_amount" in df_copy.columns
        and "link_amount" in df_copy.columns
    ):
        brand_stats = (
            df_copy.groupby("brand_name")
            .agg({"r_brand_amount": "mean", "link_amount": "mean"})
            .reset_index()
        )

        brand_stats["total_score"] = (
            brand_stats["r_brand_amount"] + brand_stats["link_amount"]
        )

        brand_stats = brand_stats.sort_values(
            "total_score", ascending=False
        ).reset_index(drop=True)

        brand_stats["rank"] = range(1, len(brand_stats) + 1)

        ranking_data = brand_stats.rename(
            columns={"brand_name": "Brand", "total_score": "Score", "rank": "Rank"}
        )

        ranking_data = ranking_data[["Brand", "Score", "Rank"]]

    pie_labels = (
        brand_stats["brand_name"].tolist() if not brand_stats.empty else ["暂无数据"]
    )
    pie_values = brand_stats["total_score"].tolist() if not brand_stats.empty else [100]
    treemap_data = {}
    if "source_stats" in focus_df.columns:
        latest_source = (
            latest_data["source_stats"].iloc[0] if not latest_data.empty else {}
        )
        if isinstance(latest_source, str):
            try:
                latest_source = json.loads(latest_source)
            except Exception:
                latest_source = {}
        treemap_data = latest_source if isinstance(latest_source, dict) else {}

    return (
        trend_data,
        ranking_data,
        pie_labels,
        pie_values,
        latest_r_brand_amount,
        latest_link_amount,
        latest_nr_brand_amount,
        change_r_brand,
        change_nr_brand,
        change_link,
        treemap_data,
    )


def _get_default_data():
    dates = [
        (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(29, -1, -1)
    ]

    trend_data = {"Date": dates, "Brand": [0] * 30, "Link": [0] * 30}
    rank_data = pd.DataFrame({"Brand": ["暂无数据"], "Score": [0], "Rank": [1]})
    BrandsP = ["暂无数据"]
    values = [100]

    latest_r_brand_amount = 0
    latest_nr_brand_amount = 0
    latest_link_amount = 0
    change_r_brand = 0
    change_nr_brand = 0
    change_link = 0
    treemap_data = {}
    return (
        trend_data,
        rank_data,
        BrandsP,
        values,
        latest_r_brand_amount,
        latest_link_amount,
        latest_nr_brand_amount,
        change_r_brand,
        change_nr_brand,
        change_link,
        treemap_data,
    )


def _make_kpi_help():
    style = {
        "position": "absolute",
        "top": "10px",
        "right": "10px",
        "width": "28px",
        "height": "28px",
        "background": "#0c0ccb",
        "color": "white",
        "borderRadius": "50%",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "fontSize": "16px",
        "fontWeight": "bold",
        "cursor": "pointer",
        "zIndex": 100,
    }
    return html.Span("?", style=style)


def _make_chart_help(help_id):
    style = {
        "float": "right",
        "width": "24px",
        "height": "24px",
        "background": "#6c757d",
        "color": "white",
        "borderRadius": "50%",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "fontSize": "14px",
        "fontWeight": "bold",
        "cursor": "pointer",
    }
    return html.Span("?", id=help_id, style=style)


app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(
            id="app-state",
            data={
                "current_page": "brand",
                "brand_name": "",
                "keyword": "",
                "link": "",
            },
        ),
        dcc.Store(id="trigger-store", data=0),
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    dbc.Button(
                                        "Q",
                                        id="btn-search-toggle",
                                        n_clicks=0,
                                        style={
                                            "width": "56px",
                                            "height": "56px",
                                            "borderRadius": "50%",
                                            "background": "linear-gradient(135deg, #3B82F6 0%, #2DD4BF 100%)",
                                            "border": "none",
                                            "boxShadow": "0 4px 15px rgba(59, 130, 246, 0.4)",
                                            "color": "white",
                                            "fontSize": "24px",
                                            "fontWeight": "900",
                                            "lineHeight": "1",
                                        },
                                    ),
                                    html.Span(
                                        "搜索",
                                        className="ms-2 text-muted small",
                                        style={"verticalAlign": "middle"},
                                    ),
                                ],
                                className="d-flex align-items-center",
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            html.Span(
                                id="brand-title",
                                className="fw-bold text-dark",
                                style={"fontSize": "1.2rem"},
                            ),
                            width="auto",
                        ),
                    ],
                    className="align-items-center mb-4",
                    style={"gap": "12px"},
                ),
                dbc.Collapse(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label(
                                                        "品牌名称",
                                                        id="lbl-search-brand",
                                                        className="small fw-bold text-secondary mb-1",
                                                    ),
                                                    dbc.Input(
                                                        id="modal-input-brand",
                                                        placeholder="如: Nike",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label(
                                                        "核心关键词",
                                                        id="lbl-search-kw",
                                                        className="small fw-bold text-secondary mb-1",
                                                    ),
                                                    dbc.Input(
                                                        id="modal-input-kw",
                                                        placeholder="如: 运动鞋",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label(
                                                        "链接地址（选填）",
                                                        id="lbl-search-link",
                                                        className="small fw-bold text-secondary mb-1",
                                                    ),
                                                    dbc.Input(
                                                        id="modal-input-link",
                                                        placeholder="请输入链接地址",
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    "开始分析",
                                                    id="modal-btn-search",
                                                    color="primary",
                                                    className="fw-bold px-4 w-100",
                                                    style={
                                                        "background": "linear-gradient(135deg, #3B82F6 0%, #2DD4BF 100%)",
                                                        "border": "none",
                                                        "height": "48px",
                                                    },
                                                ),
                                                width=12,
                                                className="mt-3",
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ],
                        className="mb-4",
                    ),
                    id="search-form-collapse",
                    is_open=False,
                ),
                dbc.Loading(
                    id="loading",
                    type="cube",
                    color="#cb0c9f",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                id="label-kpi-1",
                                                                className="card-label mb-2",
                                                            ),
                                                            _make_kpi_help(),
                                                        ],
                                                        style={"position": "relative"},
                                                        id="kpi-help-1-wrap",
                                                    ),
                                                    html.Div(
                                                        id="val-1", className="mt-4"
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="premium-card h-100 delay-1 position-relative",
                                    ),
                                    width=12,
                                    lg=4,
                                    className="mb-4",
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                id="label-kpi-2",
                                                                className="card-label mb-2",
                                                            ),
                                                            _make_kpi_help(),
                                                        ],
                                                        style={"position": "relative"},
                                                        id="kpi-help-2-wrap",
                                                    ),
                                                    html.Div(
                                                        id="val-2", className="mt-4"
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="premium-card h-100 delay-2 position-relative",
                                    ),
                                    width=12,
                                    lg=4,
                                    className="mb-4",
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                id="label-kpi-3",
                                                                className="card-label mb-2",
                                                            ),
                                                            _make_kpi_help(),
                                                        ],
                                                        style={"position": "relative"},
                                                        id="kpi-help-3-wrap",
                                                    ),
                                                    html.Div(
                                                        id="val-3", className="mt-4"
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="premium-card h-100 delay-3 position-relative",
                                    ),
                                    width=12,
                                    lg=4,
                                    className="mb-4",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    html.Span(
                                                        "流量来源趋势分析",
                                                        id="title-trend",
                                                        style={
                                                            "display": "inline-block"
                                                        },
                                                    ),
                                                    _make_chart_help(
                                                        "chart-help-trend"
                                                    ),
                                                ],
                                                className="bg-transparent border-0 fw-bold pt-4 ps-4",
                                            ),
                                            dbc.CardBody(
                                                dcc.Graph(
                                                    id="chart-trend",
                                                    config={"displayModeBar": False},
                                                    style={"height": "320px"},
                                                )
                                            ),
                                        ],
                                        className="premium-card h-100",
                                    ),
                                    width=12,
                                    lg=8,
                                    className="mb-4",
                                ),
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    html.Span(
                                                        "流量来源比例分析",
                                                        id="title-pie",
                                                        style={
                                                            "display": "inline-block"
                                                        },
                                                    ),
                                                    _make_chart_help("chart-help-pie"),
                                                ],
                                                className="bg-transparent border-0 fw-bold pt-4 ps-4",
                                            ),
                                            dbc.CardBody(
                                                dcc.Graph(
                                                    id="chart-pie",
                                                    config={"displayModeBar": False},
                                                    style={"height": "320px"},
                                                )
                                            ),
                                        ],
                                        className="premium-card h-100",
                                    ),
                                    width=12,
                                    lg=4,
                                    className="mb-4",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    html.Span(
                                                        "热门品牌排行",
                                                        id="title-rank",
                                                        style={
                                                            "display": "inline-block"
                                                        },
                                                    ),
                                                    _make_chart_help("chart-help-rank"),
                                                ],
                                                className="bg-transparent border-0 fw-bold pt-4 ps-4",
                                            ),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div("品牌", className="fw-bold text-secondary", style={"flex": "1"}),
                                                            html.Div("核心提及概率", className="fw-bold text-secondary text-center", style={"width": "150px"}),
                                                            html.Div("高相关信源", className="fw-bold text-secondary text-center", style={"width": "150px"}),
                                                            html.Div("随意性提及", className="fw-bold text-secondary text-center", style={"width": "150px"}),
                                                        ],
                                                        className="d-flex justify-content-between align-items-center px-3 py-2 bg-light rounded mb-2",
                                                        style={"borderBottom": "2px solid #e2e8f0"},
                                                    ),
                                                    html.Div(id="rank-table-container"),
                                                ],
                                                className="p-4",
                                                style={"maxHeight": "400px", "overflowY": "auto"},
                                            ),
                                        ],
                                        className="premium-card",
                                    ),
                                    width=12,
                                )
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Card(
                                        [
                                            dbc.CardHeader(
                                                [
                                                    html.Span(
                                                        "信源分类分析",
                                                        id="title-treemap",
                                                        style={
                                                            "display": "inline-block"
                                                        },
                                                    ),
                                                    _make_chart_help(
                                                        "chart-help-treemap"
                                                    ),
                                                ],
                                                className="bg-transparent border-0 fw-bold pt-4 ps-4",
                                            ),
                                            dbc.CardBody(
                                                dcc.Graph(
                                                    id="chart-treemap",
                                                    config={"displayModeBar": False},
                                                    style={"height": "360px"},
                                                )
                                            ),
                                        ],
                                        className="premium-card h-100",
                                    ),
                                    width=12,
                                    className="mb-4",
                                )
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-download me-2"),
                                                "导出为文件",
                                            ],
                                            id="btn-export-file",
                                            className="fw-bold rounded-pill px-4",
                                            color="primary",
                                            size="sm",
                                            n_clicks=0,
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-link-45deg me-2"
                                                ),
                                                "以链接分享",
                                            ],
                                            id="btn-share-link",
                                            className="fw-bold rounded-pill px-4 ms-2",
                                            color="success",
                                            size="sm",
                                            n_clicks=0,
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-image me-2"),
                                                "以图片分享",
                                            ],
                                            id="btn-share-image",
                                            className="fw-bold rounded-pill px-4 ms-2",
                                            color="outline-dark",
                                            size="sm",
                                            n_clicks=0,
                                        ),
                                    ],
                                    className="text-center py-3",
                                ),
                            ]
                        ),
                    ],
                ),
                dcc.Download(id="download-dataframe-csv"),
            ],
            fluid=True,
            className="px-lg-5 pb-5",
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("搜索品牌", className="fw-bold")),
                dbc.ModalBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label(
                                            "品牌名称",
                                            className="small fw-bold text-secondary mb-1",
                                        ),
                                        dbc.Input(
                                            id="modal-input-brand",
                                            placeholder="如: Nike",
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label(
                                            "核心关键词",
                                            className="small fw-bold text-secondary mb-1",
                                        ),
                                        dbc.Input(
                                            id="modal-input-kw",
                                            placeholder="如: 运动鞋",
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label(
                                            "链接地址（选填）",
                                            className="small fw-bold text-secondary mb-1",
                                        ),
                                        dbc.Input(
                                            id="modal-input-link",
                                            placeholder="请输入链接地址",
                                        ),
                                    ],
                                ),
                            ]
                        ),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            "查询",
                            id="modal-btn-search",
                            color="primary",
                            className="fw-bold px-4",
                        ),
                        dbc.Button(
                            "关闭",
                            id="modal-btn-close",
                            color="secondary",
                            className="ms-2",
                        ),
                    ]
                ),
            ],
            id="search-modal",
            is_open=False,
            centered=True,
        ),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("指标说明", className="fw-bold")),
                dbc.ModalBody(html.Div(id="kpi-explanation-content", children=[])),
                dbc.ModalFooter(
                    dbc.Button("关闭", id="kpi-modal-close", color="primary")
                ),
            ],
            id="kpi-modal",
            is_open=False,
            centered=True,
            size="md",
        ),
        html.Div(id="toast-container", style={"display": "none"}),
        html.Div(dash_table.DataTable(id="hidden"), style={"display": "none"}),
        html.Div(id="no-order-message", style={"display": "none"}),
        html.Div(id="no-order-detail", style={"display": "none"}),
        html.A(id="create-order-link", href="#", style={"display": "none"}),
        html.Div(id="share-image-trigger", style={"display": "none"}),
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("提示", className="fw-bold")),
                dbc.ModalBody(
                    html.Div(
                        [
                            html.P(id="no-order-modal-message", className="mb-3"),
                            html.P(
                                id="no-order-modal-detail",
                                className="text-muted small mb-3",
                            ),
                            html.A(
                                dbc.Button(
                                    "创建订单",
                                    color="primary",
                                    className="w-100",
                                    size="lg",
                                ),
                                href="/api/redirect-to-create-order/",
                                id="create-order-link-btn",
                                className="text-decoration-none",
                            ),
                        ]
                    )
                ),
            ],
            id="no-order-modal",
            is_open=False,
            backdrop="static",
            centered=True,
            size="lg",
        ),
        dbc.Offcanvas(
            [
                html.H5(id="detail-brand-name", className="mb-4 fw-bold"),
                html.Hr(),
                html.H6("流量来源趋势分析", className="mb-3 text-secondary"),
                dcc.Graph(
                    id="detail-chart-trend",
                    config={"displayModeBar": False},
                    style={"height": "250px"},
                ),
                html.Hr(className="my-4"),
                html.H6("AI平台推荐份额", className="mb-3 text-secondary"),
                dcc.Graph(
                    id="detail-chart-pie",
                    config={"displayModeBar": False},
                    style={"height": "250px"},
                ),
            ],
            id="detail-offcanvas",
            is_open=False,
            title="品牌详情分析",
            placement="end",
            style={"maxWidth": "500px"},
        ),
        html.Script("""
        (function() {
            window.addEventListener('DOMContentLoaded', function() {
                var kpiHelps = [
                    {wrap: 'kpi-help-1-wrap', btn: 'kpi-help-1'},
                    {wrap: 'kpi-help-2-wrap', btn: 'kpi-help-2'},
                    {wrap: 'kpi-help-3-wrap', btn: 'kpi-help-3'},
                ];
                kpiHelps.forEach(function(item) {
                    var wrap = document.getElementById(item.wrap);
                    var btn = document.getElementById(item.btn);
                    if (wrap && btn) {
                        wrap.addEventListener('click', function() {
                            btn.click();
                        });
                    }
                });
            });
        })();
        """),
    ]
)


@app.callback(
    Output("app-state", "data"),
    Input("url", "pathname"),
    Input("url", "search"),
)
def update_app_state(pathname, search):
    from urllib.parse import parse_qs, urlparse

    brand_name = ""
    keyword = ""
    link = ""

    if search:
        parsed = urlparse(search)
        qs = parse_qs(parsed.query)
        brand_name = qs.get("brand", [""])[0]
        keyword = qs.get("keyword", [""])[0]
        link = qs.get("link", [""])[0]

    return {
        "current_page": "brand",
        "brand_name": brand_name,
        "keyword": keyword,
        "link": link,
    }


@app.callback(
    Output("trigger-store", "data"),
    Input("app-state", "data"),
)
def trigger_on_state_change(state):
    if state and state.get("brand_name") and state.get("keyword"):
        return (state.get("brand_name", "") + state.get("keyword", "")).__hash__()
    return 0


@app.callback(
    [
        Output("val-1", "children"),
        Output("val-2", "children"),
        Output("val-3", "children"),
        Output("chart-trend", "figure"),
        Output("chart-pie", "figure"),
        Output("rank-table-container", "children"),
        Output("no-order-modal", "is_open"),
        Output("no-order-modal-message", "children"),
        Output("no-order-modal-detail", "children"),
        Output("create-order-link-btn", "href"),
        Output("chart-treemap", "figure"),
        Output("brand-title", "children"),
    ],
    [Input("trigger-store", "data"), Input("modal-btn-search", "n_clicks")],
    [
        State("app-state", "data"),
        State("modal-input-brand", "value"),
        State("modal-input-kw", "value"),
        State("modal-input-link", "value"),
    ],
)
def update_metrics(
    trigger_val, modal_click, app_state, modal_brand, modal_kw, modal_link
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            False,
            "",
            "",
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "modal-btn-search":
        search_brand = modal_brand or ""
        search_keyword = modal_kw or ""
        search_link = modal_link or ""
    else:
        search_brand = (app_state or {}).get("brand_name", "")
        search_keyword = (app_state or {}).get("keyword", "")
        search_link = (app_state or {}).get("link", "")

    if not search_brand or not search_keyword:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            False,
            "",
            "",
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )

    data = fetch_backend_data(
        brand_name=search_brand,
        keyword_name=search_keyword,
        link_name=search_link,
    )

    if isinstance(data, dict) and data.get("no_order"):
        brand_name = data.get("brand_name", "")
        keyword_name = data.get("keyword", "")
        create_order_href = f"/api/redirect-to-create-order/?brand_name={brand_name}&keyword_name={keyword_name}"

        def create_empty_kpi():
            return html.Div(
                [
                    html.Span("0%", className="metric-value"),
                    html.Br(),
                    html.Span(
                        "暂无数据",
                        className="trend-indicator",
                        style={"background": "#f0f0f0", "color": "#666"},
                    ),
                ],
                className="mt-4",
            )

        return (
            create_empty_kpi(),
            create_empty_kpi(),
            create_empty_kpi(),
            go.Figure(),
            go.Figure(),
            "",
            True,
            f"系统中暂无关于 '{brand_name}' 和 '{keyword_name}' 的订单数据。",
            f"品牌：{brand_name} | 关键词：{keyword_name}",
            create_order_href,
            go.Figure(),
            f"{brand_name} - {keyword_name}",
        )

    (
        trend,
        rank,
        pie_l,
        pie_v,
        latest_r_brand_amount,
        latest_link_amount,
        latest_nr_brand_amount,
        change_r_brand,
        change_nr_brand,
        change_link,
        treemap_data,
    ) = _convert_to_web_format(data, search_brand)

    def create_trend_badge(value, change):
        if change > 0:
            return html.Span(
                [html.I(className="bi bi-arrow-up-short"), f" {abs(change):.1f}%"],
                className="trend-indicator trend-indicator-up",
            )
        elif change < 0:
            return html.Span(
                [html.I(className="bi bi-arrow-down-short"), f" {abs(change):.1f}%"],
                className="trend-indicator trend-indicator-down",
            )
        else:
            return html.Span(
                [html.I(className="bi bi-dash"), " 0%"],
                className="trend-indicator",
                style={"background": "#f0f0f0", "color": "#666"},
            )

    def create_kpi_with_trend(value, change):
        return html.Div(
            [
                html.Span(f"{value}%", className="metric-value"),
                html.Br(),
                create_trend_badge(value, change),
            ],
            className="mt-4",
        )

    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=trend["Date"],
            y=trend["Brand"],
            name="Brand Traffic",
            fill="tozeroy",
            line=dict(color="#d61616", width=3, shape="spline"),
        )
    )
    fig1.add_trace(
        go.Scatter(
            x=trend["Date"],
            y=trend["Link"],
            name="Link Traffic",
            line=dict(color="#152FC2", width=3, shape="spline"),
        )
    )
    fig1.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=10, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1),
    )

    fig2 = go.Figure(
        data=[
            go.Pie(
                labels=pie_l,
                values=pie_v,
                hole=0.7,
                textinfo="percent",
                textposition="outside",
                marker=dict(colors=px.colors.qualitative.Pastel),
            )
        ]
    )
    fig2.update_layout(
        showlegend=True,
        margin=dict(l=20, r=20, t=0, b=20),
        legend=dict(orientation="h"),
    )

    ranks = []
    if isinstance(rank, pd.DataFrame) and not rank.empty:
        for i, (_, r) in enumerate(rank.iterrows()):
            rk = r["Rank"]
            brand_n = r["Brand"]
            score = r.get('Score', 0)
            r_brand = score * 0.8 if score else 0
            nr_brand = score * 0.6 if score else 0
            is_highlighted = brand_n == search_brand
            
            if rk == 1:
                rank_style = {"background": "linear-gradient(135deg, #FFD700, #F59E0B)", "color": "white"}
            elif rk == 2:
                rank_style = {"background": "linear-gradient(135deg, #C0C0C0, #9CA3AF)", "color": "white"}
            elif rk == 3:
                rank_style = {"background": "linear-gradient(135deg, #CD7F32, #B45309)", "color": "white"}
            else:
                rank_style = {"background": "#e2e8f0", "color": "#64748b"}
            
            ranks.append(
                html.Div(
                    [
                        dcc.Interval(id=f"rank-trigger-{i}", n_intervals=0),
                        html.Div(
                            [
                                html.Span(f"#{rk}", className="rank-badge", style=rank_style),
                                html.Span(
                                    brand_n,
                                    className="fw-bold",
                                    style={"flex": "1", "marginLeft": "12px", "color": "#0F172A" if not is_highlighted else "#3B82F6"},
                                ),
                                html.Span(f"{r_brand:.1f}%", className="text-center", style={"width": "150px", "fontWeight": "600", "color": "#3B82F6"}),
                                html.Span(f"{nr_brand:.1f}%", className="text-center", style={"width": "150px", "fontWeight": "600", "color": "#2DD4BF"}),
                                html.Span(f"{score:.1f}%", className="text-center", style={"width": "150px", "fontWeight": "600", "color": "#64748B"}),
                                html.I(className="bi bi-chevron-right ms-2", style={"color": "#94A3B8", "fontSize": "14px"}),
                            ],
                            className="d-flex align-items-center px-3 py-3 rounded mb-2",
                            style={"cursor": "pointer", "background": "#F8FAFC" if i % 2 == 0 else "white", "transition": "all 0.2s ease"},
                            id={"type": "rank-row", "index": i},
                            n_clicks=0,
                        ),
                    ]
                )
            )
    else:
        ranks = [html.Div("暂无排行榜数据，点击分析按钮获取数据", className="text-center text-muted py-5")]

    v1 = create_kpi_with_trend(latest_r_brand_amount, change_r_brand)
    v2 = create_kpi_with_trend(latest_link_amount, change_link)
    v3 = create_kpi_with_trend(latest_nr_brand_amount, change_nr_brand)

    fig_treemap = go.Figure()
    if treemap_data and any(v > 0 for v in treemap_data.values()):
        treemap_labels = list(treemap_data.keys())
        treemap_values = list(treemap_data.values())
        color_map = {
            "官方媒体": "#e74c3c",
            "知名媒体": "#e67e22",
            "行业垂直媒体": "#2ecc71",
            "社交平台": "#3498db",
            "个人博客/自媒体": "#9b59b6",
            "其他": "#95a5a6",
        }
        fig_treemap = px.treemap(
            names=treemap_labels,
            values=treemap_values,
            color=treemap_labels,
            color_discrete_map=color_map,
        )
        fig_treemap.update_traces(
            textinfo="label+value+percent parent",
            textfont=dict(size=14),
        )
    fig_treemap.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
    )

    return (
        v1,
        v2,
        v3,
        fig1,
        fig2,
        ranks,
        False,
        "",
        "",
        dash.no_update,
        fig_treemap,
        f"{search_brand} - {search_keyword}",
    )


@app.callback(
    Output("search-form-collapse", "is_open"),
    [Input("btn-search-toggle", "n_clicks")],
    [State("search-form-collapse", "is_open")],
)
def toggle_search_form(toggle_click, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    return not is_open


@app.callback(
    [Output("detail-offcanvas", "is_open"), Output("detail-brand-name", "children"), Output("detail-chart-trend", "figure"), Output("detail-chart-pie", "figure")],
    [Input({"type": "rank-row", "index": ALL}, "n_clicks")],
    [State("app-state", "data")],
    prevent_initial_call=True,
)
def show_brand_detail(n_clicks_list, app_state):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", go.Figure(), go.Figure()
    
    triggered = ctx.triggered[0]
    prop_id = triggered["prop_id"]
    
    try:
        import json
        idx = json.loads(prop_id.replace("'", '"'))["index"]
    except:
        return False, "", go.Figure(), go.Figure()
    
    brand_name = (app_state or {}).get("brand_name", "") or f"品牌 {idx + 1}"
    
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14, -1, -1)]
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=dates,
        y=[20 + idx * 5 + i * (3 - idx * 0.5) for i in range(15)],
        name="品牌流量",
        fill="tozeroy",
        line=dict(color="#3B82F6", width=2),
    ))
    fig_trend.add_trace(go.Scatter(
        x=dates,
        y=[15 + idx * 3 + i * (2 - idx * 0.3) for i in range(15)],
        name="链接流量",
        line=dict(color="#2DD4BF", width=2),
    ))
    fig_trend.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=10, b=20),
        height=250,
        showlegend=True,
        legend=dict(orientation="h", y=1.1),
    )
    
    fig_pie = go.Figure(go.Pie(
        labels=["ChatGPT", "Claude", "Perplexity", "Bing AI", "其他"],
        values=[35 - idx * 5, 25, 20, 12 + idx * 3, 8],
        hole=0.6,
    ))
    fig_pie.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=10, b=20),
        height=250,
    )
    
    return True, f"品牌详情 - {brand_name}", fig_trend, fig_pie


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-export-file", "n_clicks"),
    [State("app-state", "data")],
    prevent_initial_call=True,
)
def export_csv(n_clicks, app_state):
    brand_name = (app_state or {}).get("brand_name", "")
    keyword_name = (app_state or {}).get("keyword", "")
    link_name = (app_state or {}).get("link", "")

    df = fetch_backend_data(
        brand_name=brand_name,
        keyword_name=keyword_name,
        link_name=link_name,
    )

    if isinstance(df, dict):
        df = pd.DataFrame({"Info": ["No data available for export"]})

    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame({"Info": ["Unexpected data format"]})

    filename = f"dashboard_{brand_name}_{keyword_name}.csv"
    return dcc.send_data_frame(df.to_csv, filename, index=False)


@app.callback(
    Output("toast-container", "children"),
    Input("btn-share-link", "n_clicks"),
    prevent_initial_call=True,
)
def share_link(n_clicks):
    return html.Script("""
    (function() {
        navigator.clipboard.writeText(window.location.href).then(function() {
            var toast = document.getElementById('toast');
            var msg = document.getElementById('toast-message');
            if (msg) msg.textContent = '链接已复制到剪贴板';
            if (toast) toast.classList.add('show');
            setTimeout(function() {
                if (toast) toast.classList.remove('show');
            }, 3000);
        });
    })();
    """)


@app.callback(
    Output("share-image-trigger", "children"),
    Input("btn-share-image", "n_clicks"),
    prevent_initial_call=True,
)
def share_image(n_clicks):
    return html.Script("""
    (function() {
        var script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
        script.onload = function() {
            html2canvas(document.body).then(function(canvas) {
                var link = document.createElement('a');
                link.download = 'brand_dashboard.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            });
        };
        document.head.appendChild(script);
    })();
    """)


@app.callback(
    Output("kpi-modal", "is_open"),
    Output("kpi-explanation-content", "children"),
    [
        Input("kpi-help-1", "n_clicks"),
        Input("kpi-help-2", "n_clicks"),
        Input("kpi-help-3", "n_clicks"),
        Input("chart-help-trend", "n_clicks"),
        Input("chart-help-pie", "n_clicks"),
        Input("chart-help-rank", "n_clicks"),
        Input("chart-help-treemap", "n_clicks"),
        Input("kpi-modal-close", "n_clicks"),
    ],
    [State("kpi-modal", "is_open")],
    prevent_initial_call=True,
)
def show_kpi_explanation(
    kpi1,
    kpi2,
    kpi3,
    chart_trend,
    chart_pie,
    chart_rank,
    chart_treemap,
    close_btn,
    is_open,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "kpi-modal-close":
        return False, dash.no_update

    explanations = {
        "kpi-help-1": EXPLANATIONS["kpi-1"],
        "kpi-help-2": EXPLANATIONS["kpi-2"],
        "kpi-help-3": EXPLANATIONS["kpi-3"],
        "chart-help-trend": EXPLANATIONS["chart-trend"],
        "chart-help-pie": EXPLANATIONS["chart-pie"],
        "chart-help-rank": EXPLANATIONS["chart-rank"],
        "chart-help-treemap": EXPLANATIONS["chart-treemap"],
    }

    if trigger_id in explanations:
        exp = explanations[trigger_id]
        content = [html.H4(exp["title"], className="mb-3"), html.Div(exp["content"])]
        return True, content

    return is_open, dash.no_update
