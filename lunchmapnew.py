import os
import time
import base64
import requests
from io import BytesIO
from datetime import datetime

import folium
from PIL import Image
import pytesseract
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# ==========================================================
# 1. 환경 설정 및 함수
# ==========================================================
OFFICE_ADDRESS = "서울 금천구 가산디지털2로 30"
today = datetime.now()

# OCR 함수: 이미지를 받아 텍스트 추출
def ocr_image_to_text(image_source):
    try:
        # 소스가 URL인 경우 다운로드
        if isinstance(image_source, str) and image_source.startswith("http"):
            response = requests.get(image_source, headers={'User-Agent': 'Mozilla/5.0'})
            img = Image.open(BytesIO(response.content))
        # 소스가 로컬 파일 경로인 경우
        else:
            img = Image.open(image_source)
        
        # OCR 수행 (한글)
        text = pytesseract.image_to_string(img, lang='kor')
        
        # 텍스트 정리
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines: return "<div>메뉴 인식 실패</div>"
        
        return f'<div style="background-color:#f9f9f9; border:1px solid #ddd; padding:10px; border-radius:8px; text-align:left; font-size:14px; line-height:1.6; color:#333;">{"<br>".join(lines)}</div>'
    except Exception as e:
        return f"<div>인식 오류: {e}</div>"

# 기타 기존 함수들 (get_coords, calculate_walking_info 등) 동일 유지...
# [이전 코드의 get_coords, calculate_walking_info 함수를 여기에 그대로 복사하세요]

# ==========================================================
# 4. 식당 목록 (5곳 OCR 타입으로 통일)
# ==========================================================
cafeteria_list = [
    {"name": "오정", "address": "서울 금천구 가산디지털2로 30", "type": "ocr_local", "url": "오정메뉴.jpg"},
    {"name": "온정찬", "address": "서울 금천구 가산디지털1로 75-15", "type": "ocr_url", "url": "https://pf.kakao.com/_UIdXn/posts"},
    {"name": "런치투게더", "address": "서울 금천구 가산디지털1로 58", "type": "ocr_url", "url": "https://pf.kakao.com/_swtYxl"},
    {"name": "런치타임", "address": "서울 금천구 가산디지털2로 24", "type": "threads", "url": "https://www.threads.net/@lunchtime_ypp"},
    {"name": "밥심", "address": "서울 금천구 가산디지털2로 46", "type": "ocr_url", "url": "https://pf.kakao.com/_mHWxjX"}
]

# ... [get_kakao_... 함수들, get_threads_menu 함수 동일 유지] ...
# ... [Selenium 드라이버 설정 동일 유지] ...

# ==========================================================
# 11. 식당별 메뉴 수집 (OCR 방식 적용)
# ==========================================================
scraped_data = []

for item in cafeteria_list:
    lat, lng = get_coords(item["address"])
    dist, walk_min = calculate_walking_info((lat, lng))
    html_content = ""

    if item["type"] == "ocr_local":
        html_content = ocr_image_to_text(item["url"])
    elif item["type"] == "ocr_url":
        # 카카오 채널에서 이미지 URL을 먼저 따온 뒤 OCR 수행
        if "온정찬" in item["name"]: img_src = get_kakao_posts_image(driver, item["url"])
        elif "런치투게더" in item["name"]: img_src = get_kakao_profile_image(driver, item["url"], item["name"])
        else: img_src = get_kakao_first_image(driver, item["url"], item["name"])
        
        if img_src: html_content = ocr_image_to_text(img_src)
        else: html_content = "<div>이미지를 찾을 수 없습니다.</div>"
    elif item["type"] == "threads":
        html_content = get_threads_menu(driver, item["url"])

    scraped_data.append({"name": item["name"], "lat": lat, "lng": lng, "dist": dist, "walk_min": walk_min, "html": html_content})

# ... [이후 지도 생성 및 버튼 생성 코드 동일 유지] ...
