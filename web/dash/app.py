import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_table
import plotly.graph_objects as go
import requests
import logging
import os

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')
API_HOST = os.getenv('API_HOST', 'localhost')
API_PORT = os.getenv('API_PORT', '8000')

app = dash.Dash(__name__)

# Dash Layout
app.layout = html.Div([
    html.H1("상품 리뷰 시각화"),

    # 상품 번호 입력
    dcc.Input(id='product-id', type='number', placeholder='상품 번호 입력', style={'margin-right': '10px'}),
    
    # 질문 입력
    dcc.Input(id='question', type='text', placeholder='질문 입력', style={'margin-right': '10px'}),
    
    # 제출 버튼
    html.Button('제출', id='submit-button', n_clicks=0),

    # 그래프와 테이블이 업데이트되는 Div
    html.Div(id='output-content'),

    # 빈 그래프 및 테이블 초기화
    dcc.Graph(id='sentiment-graph'),
    dash_table.DataTable(id='review-table')
])

@app.callback(
    [Output('sentiment-graph', 'figure'), Output('review-table', 'data')],
    [Input('submit-button', 'n_clicks')],
    [State('product-id', 'value'), State('question', 'value')]
)
def update_output(n_clicks, product_id, question):
    print(f"버튼 클릭 횟수: {n_clicks}, 상품 번호: {product_id}, 질문: {question}")
    if n_clicks == 0 or product_id is None or question is None:
        return go.Figure(), []

    if product_id and question:
        # FastAPI 서버에 요청을 보냄
        api_url = f"http://{API_HOST}:{API_PORT}/ask"
        payload = {
            'product_id': product_id,
            'question': question
        }

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            print(f"API 요청 성공: {response.status_code}")

            data = response.json()
            similar_reviews = data['similar_reviews']
            answer = data['generated_answer']
            sentiment_graph, review_data = create_sentiment_graph(similar_reviews, answer)
            return sentiment_graph, review_data
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP 오류 발생: {http_err}")
        except Exception as e:
            print(f"API 요청 중 오류 발생: {e}")

        
        
        
    return go.Figure(), []


def create_sentiment_graph(data, answer):
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
            "sentiment": "긍정" if review["review_sentiment"] == 1 else "부정"
        }
        for review in data
    ]


    return fig, review_data

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
