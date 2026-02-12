@app.callback(
    Output('guide-step-1', 'children'),
    Output('guide-step-2', 'children'),
    Output('guide-step-3', 'children'),
    Output('guide-step-1', 'style'),
    Output('guide-step-2', 'style'),
    Output('guide-step-3', 'style'),
    Output('guide-modal', 'is_open'),
    Output('input-search-brand', 'value'),
    Output('input-search-kw', 'value'),
    Output('input-search-link', 'value'),
    Input('guide-btn-next-1', 'n_clicks'),
    Input('guide-btn-next-2', 'n_clicks'),
    Input('guide-btn-complete', 'n_clicks'),
    Input('guide-btn-prev-2', 'n_clicks'),
    Input('guide-btn-prev-3', 'n_clicks'),
    Input('guide-btn-skip', 'n_clicks'),
    State('guide-input-brand', 'value'),
    State('guide-input-keyword', 'value'),
    State('guide-input-link', 'value'),
    prevent_initial_call=True
)
def handle_guide_step(next1, next2, complete, prev2, prev3, skip, brand, keyword, link):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [dash.no_update] * 9

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    step1_content = [
        html.Label("请输入您要监测的品牌名称", className="mb-2 fw-bold"),
        dbc.Input(id="guide-input-brand", placeholder="如：Nike", className="mb-3"),
        dbc.Button("下一步", id="guide-btn-next-1", className="w-100")
    ]

    step2_content = [
        html.Label("请输入核心关键词", className="mb-2 fw-bold"),
        dbc.Input(id="guide-input-keyword", placeholder="如：蓝牙耳机", className="mb-3"),
        html.Div([
            dbc.Button("上一步", id="guide-btn-prev-2", className="me-2", color="secondary"),
            dbc.Button("下一步", id="guide-btn-next-2", className="flex-grow-1")
        ], className="d-flex")
    ]

    step3_content = [
        html.Label("请输入信源链接（选填）", className="mb-2 fw-bold"),
        dbc.Input(id="guide-input-link", placeholder="如：https://example.com", className="mb-3"),
        html.Div([
            dbc.Button("上一步", id="guide-btn-prev-3", className="me-2", color="secondary"),
            dbc.Button("完成并开始分析", id="guide-btn-complete", className="flex-grow-1", color="primary")
        ], className="d-flex")
    ]

    if trigger_id == 'guide-btn-next-1':
        return (step1_content, step2_content, step3_content,
                {'display': 'none'}, {'display': 'block'}, {'display': 'none'},
                True,
                dash.no_update, dash.no_update, dash.no_update)

    elif trigger_id == 'guide-btn-prev-2':
        return (step1_content, step2_content, step3_content,
                {'display': 'block'}, {'display': 'none'}, {'display': 'none'},
                True,
                dash.no_update, dash.no_update, dash.no_update)

    elif trigger_id == 'guide-btn-next-2':
        return (step1_content, step2_content, step3_content,
                {'display': 'none'}, {'display': 'none'}, {'display': 'block'},
                True,
                dash.no_update, dash.no_update, dash.no_update)

    elif trigger_id == 'guide-btn-prev-3':
        return (step1_content, step2_content, step3_content,
                {'display': 'none'}, {'display': 'block'}, {'display': 'none'},
                True,
                dash.no_update, dash.no_update, dash.no_update)

    elif trigger_id == 'guide-btn-complete':
        return (dash.no_update, dash.no_update, dash.no_update,
                dash.no_update, dash.no_update, dash.no_update,
                False,
                brand or '', keyword or '', link or '')

    elif trigger_id == 'guide-btn-skip':
        return (step1_content, step2_content, step3_content,
                dash.no_update, dash.no_update, dash.no_update,
                False,
                '', '', '')

    return [dash.no_update] * 9
