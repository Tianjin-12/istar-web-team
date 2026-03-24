
import os
import sys
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Output, Input
from django_plotly_dash import DjangoDash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
from mvp.cluster_viz_utils import ClusterDataProcessor

COLORS = {
    0: {"primary": "#667eea"},
    1: {"primary": "#f093fb"},
    2: {"primary": "#4facfe"},
    3: {"primary": "#43e97b"},
    4: {"primary": "#fa709a"},
    -1: {"primary": "#cbd5e0"}
}

app = DjangoDash('ClusterVizApp',
                 external_stylesheets=[
                     '/static/css/bootstrap.min.css',
                     '/static/css/cluster_viz.css'
                 ],
                 suppress_callback_exceptions=True)

def create_3d_scatter(vectors, cluster_map, questions, dimension=3):
    fig = go.Figure()
    
    for cluster_id in sorted(set(cluster_map.values())):
        indices = [int(qid)-1 for qid, cid in cluster_map.items() if cid == cluster_id]
        if len(indices) == 0:
            continue
        
        x = vectors[indices, 0]
        y = vectors[indices, 1]
        color = COLORS.get(cluster_id, {"primary": "#667eea"})["primary"]
        
        hover_texts = []
        for idx in indices:
            qid = idx + 1
            question_text = questions.get(idx, "N/A")
            hover_texts.append(f"<b>问题 {qid}</b><br>簇: {cluster_id}<br>{question_text[:80]}...")
        
        if dimension == 3:
            z = vectors[indices, 2]
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode='markers',
                marker=dict(size=10 if cluster_id != -1 else 5, color=color, opacity=0.8 if cluster_id != -1 else 0.4),
                name=f'簇 {cluster_id}' if cluster_id >= 0 else '噪声',
                text=hover_texts,
                hovertemplate='%{text}<extra></extra>'
            ))
        else:
            fig.add_trace(go.Scatter(
                x=x, y=y,
                mode='markers',
                marker=dict(size=12 if cluster_id != -1 else 6, color=color, opacity=0.8 if cluster_id != -1 else 0.4),
                name=f'簇 {cluster_id}' if cluster_id >= 0 else '噪声',
                text=hover_texts,
                hovertemplate='%{text}<extra></extra>'
            ))
    
    if dimension == 3:
        fig.update_layout(
            scene=dict(
                xaxis=dict(showgrid=True, gridcolor='rgba(200,200,200,0.3)', title='维度 1'),
                yaxis=dict(showgrid=True, gridcolor='rgba(200,200,200,0.3)', title='维度 2'),
                zaxis=dict(showgrid=True, gridcolor='rgba(200,200,200,0.3)', title='维度 3'),
                bgcolor='rgba(245, 247, 250, 0.8)',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
            ),
            margin=dict(l=0, r=0, b=0, t=50),
            title=dict(text='聚类结果可视化', font=dict(size=20, color='#2d3748'))
        )
    else:
        fig.update_layout(
            xaxis=dict(title='维度 1', showgrid=True, gridcolor='rgba(200,200,200,0.3)'),
            yaxis=dict(title='维度 2', showgrid=True, gridcolor='rgba(200,200,200,0.3)'),
            plot_bgcolor='rgba(245, 247, 250, 0.8)',
            margin=dict(l=50, r=30, b=50, t=50),
            title=dict(text='聚类结果可视化', font=dict(size=20, color='#2d3748'))
        )
    
    return fig

app.layout = html.Div([
    dcc.Store(id='app-state'),
    dbc.Card([
        dbc.Row([
            dbc.Col([dbc.Label("关键词", className="fw-bold small mb-1"), dcc.Dropdown(id='keyword-dropdown', placeholder='选择关键词', options=[], value=None)], width=3),
            dbc.Col([dbc.Label("降维方法", className="fw-bold small mb-1"), dcc.Dropdown(id='dim-method-dropdown', options=[{'label': 'UMAP (推荐)', 'value': 'umap'}, {'label': 'PCA (快速)', 'value': 'pca'}, {'label': 't-SNE', 'value': 'tsne'}], value='umap', clearable=False)], width=2),
            dbc.Col([dbc.Label("可视化维度", className="fw-bold small mb-1"), dcc.Dropdown(id='dimension-dropdown', options=[{'label': '3D (立体)', 'value': '3'}, {'label': '2D (平面)', 'value': '2'}], value='3', clearable=False)], width=2),
            dbc.Col([dbc.Label("", className="fw-bold small mb-1"), dbc.Button([html.I(className="bi bi-download me-2"), "导出"], id='btn-export', className="btn-3d w-100")], width=2),
            dbc.Col([html.H4([html.I(className="bi bi-graph-3d me-2", style={"color": "#667eea"}), "聚类可视化"], className="fw-bold mb-0", style={"marginTop": "10px"})], width=3)
        ])
    ], className="glass-card mb-4"),
    dbc.Row([
        dbc.Col([html.Div(id='cluster-stats')], width=12, md=3),
        dbc.Col([dcc.Graph(id='scatter-3d', config={'displayModeBar': True}, style={"height": "500px"})], width=12, md=9)
    ]),
    dcc.Download(id='download-png')
])

@app.callback(Output('keyword-dropdown', 'options'), Input('keyword-dropdown', 'id'))
def init_keywords(_):
    try:
        keywords = ClusterDataProcessor('').get_available_keywords()
        return [{'label': kw, 'value': kw} for kw in keywords]
    except:
        return []

@app.callback([Output('scatter-3d', 'figure'), Output('cluster-stats', 'children')],
              [Input('keyword-dropdown', 'value'), Input('dim-method-dropdown', 'value'), Input('dimension-dropdown', 'value')])
def update_visualization(keyword, dim_method, dimension):
    if not keyword:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    try:
        processor = ClusterDataProcessor(keyword)
        n_components = int(dimension)
        reduced_vectors = processor.reduce_dimension(dim_method, n_components)
        
        fig = create_3d_scatter(reduced_vectors, processor.cluster_map, processor.questions, dimension=n_components)
        
        stats = processor.get_cluster_stats()
        stats_card = dbc.Card([
            dbc.CardBody([
                html.H5("聚类统计", className="fw-bold mb-3"),
                html.P(f"总问题数: {stats['total']}", className="mb-2"),
                html.P(f"有效簇: {stats['valid_clusters']} ({stats['valid_percent']}%)", className="mb-2"),
                html.P(f"噪声点: {stats['noise']} ({stats['noise_percent']}%)", className="mb-2"),
                html.P(f"簇数量: {stats['cluster_count']}", className="mb-0"),
            ])
        ])
        
        return fig, stats_card
    except Exception as e:
        print(f"Error: {e}")
        return go.Figure(), html.Div("加载失败")

@app.callback(Output('download-png', 'data'), [Input('btn-export', 'n_clicks')], prevent_initial_call=True)
def export_png(n_clicks):
    if not n_clicks:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    from datetime import datetime
    return dcc.send_bytes(lambda x: b'', f'cluster_viz_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
