import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_table
import plotly.graph_objects as go
import plotly.express as px
import requests
import logging
import os

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
API_HOST = os.getenv('API_HOST', 'localhost')
API_PORT = os.getenv('API_PORT', '8000')

app = dash.Dash(__name__)

# Dash Layout
app.layout = html.Div([
    html.H1("상품에 대해 질문하세요!"),

    # 상품 번호 입력
    html.P('안내: 상품 번호는 0부터 100까지 입력 가능합니다.'),
    dcc.Input(id='product-id', type='number', placeholder='상품 번호 입력', style={'margin-right': '10px'}),
    
    # 질문 입력
    dcc.Input(id='question', type='text', placeholder='질문 입력', style={'margin-right': '10px'}, size='100'),
    
    # 제출 버튼
    html.Button('제출', id='submit-button', n_clicks=0),

    # 구분선
    html.Hr(),

    html.H1("상품 기본 정보"),

    # 상품명, 리뷰 개수, 점수 분포 그래프
    html.Div([
        html.H3(id='product-name'),
        html.P(id='review-count'),
        dcc.Graph(id='score-graph'),

        # 키워드 비율 (피부타입, 피부고민, 자극도 파이 차트)
        html.Div([
            html.Div([
                dcc.Graph(id='skin-type-graph')
            ], style={'flex': '1', 'padding': '10px'}),  # 차트 1
            html.Div([
                dcc.Graph(id='skin-concern-graph')
            ], style={'flex': '1', 'padding': '10px'}),  # 차트 2
            html.Div([
                dcc.Graph(id='sensitivity-graph')
            ], style={'flex': '1', 'padding': '10px'})   # 차트 3
        ], style={'display': 'flex'}),  # Flexbox 설정
    ], style={'padding': '10px'}),

    html.Hr(),

    html.H1("질문에 대한 답변과 리뷰 분석"),

    # 질문에 대한 답변
    html.Div(id='answer-content'),

    html.H1("관련 리뷰 상위 10개"),

    # 긍/부정 비율
    dcc.Graph(id='sentiment-graph', figure=go.Figure()),

    

    # 리뷰 테이블 (긍정/부정, 점수, 작성 날짜, 리뷰 내용)
    dash_table.DataTable(
        id='review-table',
        columns=[
            {"name": "긍정/부정", "id": "sentiment"},
            {"name": "점수", "id": "score"},
            {"name": "작성 날짜", "id": "date"},
            {"name": "리뷰 내용", "id": "review_text"},
        ],
        data=[],  # 초기 데이터 비우기
        style_cell={
            'textAlign': 'left',  # 텍스트 왼쪽 정렬
            'whiteSpace': 'normal',  # 텍스트 자동 줄바꿈
            'height': 'auto',  # 자동 높이 조정
            'maxWidth': '600px',  # 최대 너비를 제한
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'review_text'},  # 리뷰 텍스트 열에 대한 설정
                'whiteSpace': 'normal',
                'textOverflow': 'ellipsis',  # 텍스트가 너무 길면 줄바꿈 대신 "..."으로 표시
                'overflow': 'hidden',
            }
        ],
        style_table={
            'maxHeight': '500px',  # 테이블 최대 높이
            'overflowY': 'auto',  # 세로 스크롤 허용
        }
    )
])

@app.callback(
    [Output('sentiment-graph', 'figure'), Output('review-table', 'data'), Output('answer-content', 'children'), 
     Output('product-name', 'children'), Output('review-count', 'children'), Output('score-graph', 'figure'),
     Output('skin-type-graph', 'figure'), Output('skin-concern-graph', 'figure'), Output('sensitivity-graph', 'figure')], 
    [Input('submit-button', 'n_clicks')],
    [State('product-id', 'value'), State('question', 'value')]
)
def update_output(n_clicks, product_id, question):
    print(f"버튼 클릭 횟수: {n_clicks}, 상품 번호: {product_id}, 질문: {question}")
    if n_clicks == 0 or product_id is None or question is None:
        return go.Figure(), [], html.P("상품 번호와 질문을 입력해주세요."), "", "", go.Figure(), go.Figure(), go.Figure(), go.Figure()

    if product_id is not None and question:
        # FastAPI 서버에 요청을 보냄
        api_url = f"http://{API_HOST}:{API_PORT}/ask"
        payload = {
            'product_id': product_id,
            'question': question
        }

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            logging.info(f"API 요청 성공: {response.status_code}")

            data = response.json()
            similar_reviews = data['similar_reviews']
            answer = data['generated_answer']
            metadata = data['metadata']

            product_name = f"상품명: {metadata['name']}"
            review_count = f"리뷰 개수: {metadata['count']}"
            score_distribution = metadata['score_distribution']
            keyword_distribution = metadata['keyword_distribution']

            '''메타데이터 정보를 바탕으로 그래프 및 테이블 업데이트'''
            # 점수 분포 그래프 업데이트
            score_graph = update_score_graph(score_distribution)

            # 키워드 분포 그래프 업데이트
            skin_type_graph = update_skin_type_graph(keyword_distribution['피부타입'])
            skin_concern_graph = update_skin_concern_graph(keyword_distribution['피부고민'])
            sensitivity_graph = update_sensitivity_graph(keyword_distribution['자극도'])


            '''질문에 대한 답변 및 리뷰 분석 업데이트'''
            # 리뷰 테이블 업데이트
            sentiment_graph, review_data = create_sentiment_graph(similar_reviews)

            # 질문 답변 업데이트
            answer_content = html.Div([
                html.H3("관련 리뷰를 기반으로 생성된 요약 답변입니다."),
                html.H3(answer)
            ])

            return (
                sentiment_graph, review_data, answer_content, 
                product_name, review_count, 
                score_graph, skin_type_graph, skin_concern_graph, sensitivity_graph
            )
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP 오류 발생: {http_err}")
            return go.Figure(), [], html.P(f"API 요청 중 오류가 발생했습니다: {http_err}"), "", "", go.Figure(), go.Figure(), go.Figure(), go.Figure()
        except Exception as e:
            print(f"API 요청 중 오류 발생: {e}")
            return go.Figure(), [], html.P(f"API 요청 중 오류가 발생했습니다: {e}"), "", "", go.Figure(), go.Figure(), go.Figure(), go.Figure()

    return go.Figure(), [], html.P("질문에 대한 답변을 기다리고 있습니다."), "", "", go.Figure(), go.Figure(), go.Figure(), go.Figure()

# 점수 비율 막대그래프 생성 함수
def update_score_graph(score_data):
    score_labels = list(score_data.keys())
    score_values = list(score_data.values())

    fig = go.Figure(go.Bar(
        x=score_values,
        y=score_labels,
        orientation='h',
        text=[f"{value}%" for value in score_values],
        textposition='auto',
        marker_color='blue'
    ))

    fig.update_layout(
        title="점수 분포",
        xaxis_title="비율 (%)",
        yaxis_title="점수",
        height=400
    )
    return fig

# 키워드 비율 (피부타입) 파이차트 생성 함수
def update_skin_type_graph(skin_type_data):
    labels = list(skin_type_data.keys())
    values = list(skin_type_data.values())

    fig = px.pie(
        values=values, 
        names=labels, 
        title="피부 타입 분포",
        hole=0.3  # 도넛 형태로
    )
    return fig


# 키워드 비율 (피부고민) 파이차트 생성 함수
def update_skin_concern_graph(skin_concern_data):
    labels = list(skin_concern_data.keys())
    values = list(skin_concern_data.values())

    fig = px.pie(
        values=values, 
        names=labels, 
        title="피부 고민 분포",
        hole=0.3  # 도넛 형태로
    )
    return fig


# 키워드 비율 (자극도) 파이차트 생성 함수
def update_sensitivity_graph(sensitivity_data):
    labels = list(sensitivity_data.keys())
    values = list(sensitivity_data.values())

    fig = px.pie(
        values=values, 
        names=labels, 
        title="자극도 분포",
        hole=0.3  # 도넛 형태로
    )
    return fig

# 긍정/부정 비율 막대그래프 생성 및 리뷰테이블 데이터 생성 함수
def create_sentiment_graph(data):
    # 긍정/부정 해석 (숫자 -> 텍스트 변환)
    for d in data:
        d["sentiment"] = "긍정" if d["review_sentiment"] == 1 else "부정"

    # 긍정/부정 리뷰 비율 계산
    total_reviews = len(data)
    positive_reviews = len([d for d in data if d["sentiment"] == "긍정"])
    negative_reviews = len([d for d in data if d["sentiment"] == "부정"])

    # 긍정/부정 비율 계산 (백분율로 표현)
    positive_ratio = positive_reviews / total_reviews * 100
    negative_ratio = 100 - positive_ratio  # 부정 비율은 나머지 비율


    # 하나의 막대그래프 생성
    fig = go.Figure()


    # 긍정 비율 (파란색)
    fig.add_trace(go.Bar(
        x=[positive_ratio],  # 긍정 리뷰 비율
        y=["리뷰 비율"],  # Y축 이름
        orientation='h',  # 가로 막대그래프
        name='긍정',
        marker_color='blue',  # 파란색
        marker_line_width=0,  # 막대 외곽선 제거
        text=[f'긍정 {positive_ratio:.2f}%'],  # 텍스트로 비율 표시
        textposition='inside',
        textfont=dict(size=20)
    ))

    # 나머지 부정 비율 (빨간색)
    fig.add_trace(go.Bar(
        x=[negative_ratio],  # 나머지 부정 리뷰 비율
        y=["리뷰 비율"],
        orientation='h',
        name='부정',
        marker_color='red',
        marker_line_width=0,
        text=[f'부정 {negative_ratio:.2f}%'],  # 텍스트로 비율 표시
        textposition='inside',
        textfont=dict(size=20)
    ))


    # 레이아웃 설정
    fig.update_layout(
        title="",
        barmode='stack',  # 스택형 막대그래프로 설정하여 하나의 막대를 채움
        height=50,
        xaxis=dict(
            title="",  # X축 타이틀 제거
            showticklabels=False,  # X축 눈금 제거
            showgrid=False,  # X축 그리드 제거
            zeroline=False  # X축 0선 제거
        ),
        yaxis=dict(
            title="",  # Y축 타이틀 제거
            showticklabels=False,  # Y축 눈금 제거
            showgrid=False,  # Y축 그리드 제거
            zeroline=False  # Y축 0선 제거
        ),
        showlegend=False,  # 범례 숨김,
        plot_bgcolor='rgba(0,0,0,0)',  # 그래프 배경색 제거
        margin=dict(l=0, r=0, t=0, b=10)  # 그래프 여백 제거
    )

    # 리뷰 데이터를 테이블에 맞게 변환
    review_data = [
        {
            "review_text": review["review_text"],
            "score": review["score"],
            "date": review["date"],
            "sentiment": "😁" if review["review_sentiment"] == 1 else "😡"
        }
        for review in data
    ]


    return fig, review_data

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
