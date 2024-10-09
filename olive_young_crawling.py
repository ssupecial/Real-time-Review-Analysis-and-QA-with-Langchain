import os
import sys
import time
import click
import json
import logging
import warnings ; warnings.filterwarnings(action='ignore')

import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

logging.basicConfig(
    format="[%(asctime)-15s] %(levelname)s - %(message)s",
    level=logging.INFO
)

@click.command()
@click.option("--start_index", default=0, help="Start index for crawling", type=int)
@click.option("--finish_index", default=-1, help="Finish index for crawling", type=int)
@click.option("--broker_url", default="localhost:9092", help="Kafka broker url", type=str)
def main(start_index, finish_index, broker_url):
    '''
    Kafka Broker 연결
    '''
    producer = wait_for_broker(broker_url)

    df_url = pd.read_csv('./data/url_list.csv')
    df_url.columns = ['url']
    length = len(df_url) if finish_index == -1 else finish_index
    cur_index = start_index

    while True:
        try:
            if cur_index >= length:
                logging.info("Finished crawling all urls")
                break

            url = df_url.iloc[cur_index]['url']
            logging.info(f"Start crawling {cur_index}th/{length-1} url: {url}")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get(url)

            '''
            메타 데이터 수집
            '''

            # 상품명
            name = driver.find_element(By.XPATH, '//*[@id="Contents"]/div[2]/div[2]/div/p[2]').text

            # 리뷰 버튼
            review_button = driver.find_element(By.XPATH, '//*[@id="reviewInfo"]/a')
            review_button.click()
            time.sleep(3)

            # 평가
            eval = driver.find_elements(By.CSS_SELECTOR, ".grade_img")[0].text.strip()

            # 건수, 점수
            count, score = driver.find_elements(By.CSS_SELECTOR, ".star_area")[0].text.split('\n')

            # 5~1점 비율
            ratio = driver.find_elements(By.CSS_SELECTOR, ".graph_list")[0].text

            # 피부타입, 피부고민, 자극도 비율
            ratio_cate = driver.find_elements(By.CSS_SELECTOR, ".poll_all.clrfix")[0].text

            # 해시태그
            keywords = driver.find_elements(By.CSS_SELECTOR, ".reviewCate>ul>li")
            keywords_list = "|".join([keyword.get_attribute('data-keyword') for keyword in keywords])

            '''
            리뷰 데이터 수집
            '''
            review_page = 1
            while True:
                reviews = driver.find_elements(By.CSS_SELECTOR, ".review_cont")
                print(f"리뷰페이지 {review_page} 크롤링 중")
                for review in reviews:
                    score = review.find_element(By.CLASS_NAME, "review_point").text
                    date = review.find_element(By.CLASS_NAME, "date").text
                    review_text = review.find_element(By.CLASS_NAME, "txt_inner").text
                    review_data = {
                        "product_index": cur_index,
                        "score": score,
                        "date": date,
                        "review_text": review_text,
                        "finish": False
                    }
                    producer.send("oliveyoung_reviews", review_data)

                try:
                    driver.find_element(By.XPATH, f'//a[@data-page-no="{review_page+1}"]').click()
                    time.sleep(3)
                except:
                    try:
                        driver.find_element(By.CLASS_NAME, "next").click()
                        time.sleep(3)
                    except:
                        print(f"리뷰 마지막 페이지: {review_page}")
                        producer.send("oliveyoung_reviews", {"product_index": cur_index, "finish": True})
                        producer.flush()
                        break

                review_page += 1

            meta_data = {
                "product_index": cur_index,
                "name": name,
                "eval": eval,
                "count": count,
                "score": score,
                "ratio": ratio,
                "ratio_cate": ratio_cate,
                "keywords": keywords_list,
                "review_num": review_page
            }
            producer.send("oliveyoung_meta", meta_data)
            producer.flush()


            driver.close()
            cur_index += 1
            time.sleep(10)
        except Exception as e:
            logging.error(f"Failed to crawl {cur_index}th url: {url}, error: {e},\n Retry after 60 seconds")
            producer.flush()
            driver.close()
            time.sleep(60)

# Kafka broker가 준비될 때까지 대기하는 함수
def wait_for_broker(bootstrap_servers, retries=5, delay=5):
    for attempt in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            )
            print("Kafka broker 연결 성공")
            return producer
        except NoBrokersAvailable:
            print(
                f"Kafka broker에 연결할 수 없습니다. 재시도 중... ({attempt + 1}/{retries})"
            )
            time.sleep(delay)
    raise Exception("Kafka broker에 연결할 수 없습니다. 모든 재시도가 실패했습니다.")


if __name__ == "__main__":
    main()