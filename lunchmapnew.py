import os
import time
import json
import base64
from io import BytesIO
from datetime import datetime

import folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================================
# 1. 사용자 설정
# ==========================================================
OFFICE_ADDRESS = "서울 금천구 가산디지털2로 30"

# ==========================================================
# 2. 오늘 날짜 / 요일
# ==========================================================
today = datetime.now()
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
today_weekday_index = today.weekday()
today_weekday = weekdays[today_weekday_index]
today_date_str_space = f"{today.month}월 {today.day}일"
today_date_str_nospace = f"{today.month}월{today.day}일"

print(f"\n{'='*60}\n오늘 날짜 : {today_date_str_space} ({today_weekday}요일)\n{'='*60}")

# ==========================================================
# 4. 식당 목록
# ==========================================================
cafeteria_list = [
    {
        "name": "온정찬",
        "address": "서울 금천구 가산디지털1로 75-15",
        "type": "kakao_posts",
        "url": "https://pf.kakao.com/_UIdXn/posts"
    },
    {
        "name": "런치투게더",
        "address": "서울 금천구 가산디지털1로 58",
        "type": "kakao_profile",
        "url": "https://pf.kakao.com/_swtYxl"
    },
    {
        "name": "런치타임",
        "address": "서울 금천구 가산디지털2로 24",
        "type": "threads",
        "url": "https://www.threads.net/@lunchtime_ypp"
    },
    {
        "name": "밥심",
        "address": "서울 금천구 가산디지털2로 46",
        "type": "kakao_first",
        "url": "https://pf.kakao.com/_mHWxjX"
    }
]

# ==========================================================
# 5~9. 크롤링 함수들 (동일 유지)
# ==========================================================
geolocator = Nominatim(user_agent="gasan_lunch_map")

def get_coords(address):
    try:
        loc = geolocator.geocode(address)
        if loc: return loc.latitude, loc.longitude
    except: pass
    return 37.481, 126.882

office_coords = get_coords(OFFICE_ADDRESS)

def calculate_walking_info(dest_coords):
    try:
        dist_meters = geodesic(office_coords, dest_coords).meters
        return int(dist_meters), max(1, round(dist_meters / 70))
    except: return 0, 0

# (Selenium 설정은 동일)
chrome_options = Options()
chrome_options.add_argument("--no-sandbox"); chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu"); chrome_options.add_argument("--window-size=1280,800")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# 온정찬 전용 함수 (카카오 포스트 크롤링)
def get_kakao_posts_image(driver, url):
    print("  -> [온정찬] 카카오 게시물 이미지 수집 중...")
    try:
        driver.get(url)
        time.sleep(4)
        # 오늘 날짜를 포함하는 요소를 찾고 그 안의 이미지를 가져옴
        date_str = f"{today.month}월 {today.day}일"
        # 게시물 컨테이너를 찾음 (카카오 채널 구조에 따라 수정될 수 있음)
        posts = driver.find_elements(By.TAG_NAME, "div")
        for post in posts:
            if date_str in post.text:
                img = post.find_element(By.TAG_NAME, "img")
                return img.get_attribute("src")
        return None
    except Exception as e:
        print(f"  -> [온정찬] 오류: {e}")
        return None

# (기존 get_kakao_profile_image, get_kakao_first_image, get_threads_menu 함수들도 아래에 그대로 포함하세요)
# ... [이전과 동일한 7, 8, 9번 함수] ...

# ==========================================================
# 10. 식당별 메뉴 수집
# ==========================================================
scraped_data = []

for item in cafeteria_list:
    lat, lng = get_coords(item["address"])
    dist, walk_min = calculate_walking_info((lat, lng))
    html_content = ""

    if item["type"] == "kakao_posts":
        img_src = get_kakao_posts_image(driver, item["url"])
        html_content = f'<img src="{img_src}" style="max-width:100%; border-radius:6px;">' if img_src else "<div>메뉴를 찾지 못했습니다.</div>"
    elif item["type"] == "kakao_profile":
        img_src = get_kakao_profile_image(driver, item["url"], item["name"])
        html_content = f'<img src="{img_src}" style="max-width:100%; border-radius:6px;">' if img_src else "<div>이미지 없음</div>"
    elif item["type"] == "kakao_first":
        img_src = get_kakao_first_image(driver, item["url"], item["name"])
        html_content = f'<img src="{img_src}" style="max-width:100%; border-radius:6px;">' if img_src else "<div>이미지 없음</div>"
    elif item["type"] == "threads":
        html_content = get_threads_menu(driver, item["url"])

    scraped_data.append({"name": item["name"], "lat": lat, "lng": lng, "dist": dist, "walk_min": walk_min, "html": html_content})

driver.quit()
# ... [이후 지도를 생성하는 11번 섹션(기존과 동일)까지 이어서 붙이세요] ...
