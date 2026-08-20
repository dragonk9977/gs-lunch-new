import os
import time
import json
import base64
from io import BytesIO
from datetime import datetime

import folium
from PIL import Image
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
# 1. 사용자 설정 및 깃허브 이벤트 데이터 가져오기
# ==========================================================

def get_manual_menu_from_github_event():
    event_path = os.getenv('GITHUB_EVENT_PATH')
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, 'r') as f:
                event_data = json.load(f)
                return event_data.get('client_payload', {}).get('menu_text', None)
        except:
            pass
    return None

OJEONG_IMAGE_PATH = "오정메뉴.jpg"
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
ojeong_weekday_index = min(today_weekday_index, 4)

print(f"\n{'='*60}\n오늘 날짜 : {today_date_str_space} ({today_weekday}요일)\n{'='*60}")

# ==========================================================
# 3. 오정 메뉴 (요일별 Crop)
# ==========================================================

def crop_ojeong_by_weekday(image_path):
    try:
        img = Image.open(image_path)
        width, height = img.size

        left_margin = width * 0.16
        right_margin = width * 0.83
        top_margin = height * 0.18
        bottom_margin = height * 0.88

        table_width = right_margin - left_margin
        col_width = table_width / 5

        crop_left = left_margin + (col_width * ojeong_weekday_index)
        crop_right = crop_left + col_width

        cropped_img = img.crop((crop_left, top_margin, crop_right, bottom_margin))

        max_height = 700
        if cropped_img.height > max_height:
            ratio = max_height / cropped_img.height
            new_width = int(cropped_img.width * ratio)
            cropped_img = cropped_img.resize((new_width, max_height), Image.LANCZOS)

        buffered = BytesIO()
        cropped_img.save(buffered, format="JPEG", quality=95)
        encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")

        print(f"  -> [오정] {['월', '화', '수', '목', '금'][ojeong_weekday_index]}요일 메뉴 크롭 완료")
        return "data:image/jpeg;base64," + encoded_string
    except Exception as e:
        print(f"  -> [오정] Crop 실패 : {e}")
        return None

# ==========================================================
# 4. 식당 목록
# ==========================================================

cafeteria_list = [
    {
        "name": "오정",
        "address": "서울 금천구 가산디지털2로 30",
        "type": "ojeong",
        "url": OJEONG_IMAGE_PATH
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
        "type": "instagram",
        "url": "https://www.instagram.com/lunchtime_ypp/"
    },
    {
        "name": "밥심",
        "address": "서울 금천구 가산디지털2로 46",
        "type": "kakao_first",
        "url": "https://pf.kakao.com/_mHWxjX"
    }
]

# ==========================================================
# 5. 주소 → 좌표 및 도보 거리 계산
# ==========================================================

geolocator = Nominatim(user_agent="gasan_lunch_map")

def get_coords(address):
    try:
        loc = geolocator.geocode(address)
        if loc:
            return loc.latitude, loc.longitude
    except Exception:
        pass
    return 37.481, 126.882

office_coords = get_coords(OFFICE_ADDRESS)

def calculate_walking_info(dest_coords):
    try:
        dist_meters = geodesic(office_coords, dest_coords).meters
        walk_minutes = round(dist_meters / 70)
        if walk_minutes < 1:
            walk_minutes = 1
        return int(dist_meters), walk_minutes
    except:
        return 0, 0

# ==========================================================
# 6. Selenium 설정
# ==========================================================

chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1280,800")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

# ==========================================================
# 7. 카카오 - 런치투게더 전용
# ==========================================================

def get_kakao_profile_image(driver, url, store_name):
    print(f"  -> [{store_name}] 카카오 프로필 이미지 접근")
    try:
        driver.get(url)
        time.sleep(4)
        imgs = driver.find_elements(By.TAG_NAME, "img")
        kakao_imgs = []
        for img in imgs:
            try:
                src = img.get_attribute("src")
                if not src or "k.kakaocdn.net/dn/" not in src:
                    continue
                size = img.size
                kakao_imgs.append({
                    "element": img,
                    "src": src,
                    "width": size["width"],
                    "height": size["height"]
                })
            except:
                continue
        if not kakao_imgs:
            return None
        profile_candidates = [
            item for item in kakao_imgs
            if item["width"] <= 250 and item["height"] <= 250 and item["width"] > 0
        ]
        if not profile_candidates:
            profile_candidates = [kakao_imgs[0]]
        profile = profile_candidates[0]
        profile_element = profile["element"]
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", profile_element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", profile_element)
        except:
            try:
                profile_element.click()
            except:
                pass
        time.sleep(2)
        modal_imgs = driver.find_elements(By.TAG_NAME, "img")
        modal_candidates = []
        for img in modal_imgs:
            try:
                src = img.get_attribute("src")
                if not src or "k.kakaocdn.net/dn/" not in src:
                    continue
                size = img.size
                width, height = size["width"], size["height"]
                if width < 150 or height < 150:
                    continue
                modal_candidates.append({
                    "src": src,
                    "width": width,
                    "height": height,
                    "area": width * height
                })
            except:
                continue
        if modal_candidates:
            modal_candidates.sort(key=lambda x: x["area"], reverse=True)
            return modal_candidates[0]["src"]
        return profile["src"]
    except Exception as e:
        print(f"  -> [{store_name}] 카카오 오류 : {e}")
        return None

# ==========================================================
# 8. 카카오 - 밥심 전용
# ==========================================================

def get_kakao_first_image(driver, url, store_name):
    print(f"  -> [{store_name}] 카카오 최신 메뉴 이미지 수집")
    try:
        driver.get(url)
        time.sleep(3)
        imgs = driver.find_elements(By.TAG_NAME, "img")
        valid_candidates = []
        for img in imgs:
            try:
                src = img.get_attribute("src")
                if src and "k.kakaocdn.net/dn/" in src:
                    size = img.size
                    width = size.get("width", 0)
                    height = size.get("height", 0)
                    if width > 250 or height > 250 or (width == 0 and height == 0):
                        valid_candidates.append(src)
            except:
                continue
        if valid_candidates:
            return valid_candidates[0]
        for img in imgs:
            src = img.get_attribute("src")
            if src and "k.kakaocdn.net/dn/" in src:
                return src
        return None
    except Exception as e:
        print(f"  -> [{store_name}] 카카오 오류 : {e}")
        return None

# ==========================================================
# 9. 인스타그램 - 런치타임
# ==========================================================

def get_instagram_menu(driver, url):
    try:
        driver.get(url)
        time.sleep(3)
        post_links = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/p/')]"))
        )
        post_urls = []
        for link in post_links:
            href = link.get_attribute("href")
            if href and href not in post_urls:
                post_urls.append(href)
        post_urls = post_urls[:5]
        if not post_urls:
            return "<div>게시물을 찾지 못했습니다.</div>"
        
        target_text = None
        for index, post_url in enumerate(post_urls):
            try:
                driver.get(post_url)
                time.sleep(2)
                try:
                    more_btn = driver.find_element(By.XPATH, "//span[contains(text(), '더 보기')] | //div[contains(text(), '더 보기')]")
                    driver.execute_script("arguments[0].click();", more_btn)
                    time.sleep(1)
                except:
                    pass
                page_text = driver.find_element(By.TAG_NAME, "article").text
                if today_date_str_space in page_text or today_date_str_nospace in page_text or f"{today_weekday}요일" in page_text:
                    target_text = page_text
                    break
            except:
                pass
        
        if target_text is None and post_urls:
            driver.get(post_urls[0])
            time.sleep(2)
            try:
                more_btn = driver.find_element(By.XPATH, "//span[contains(text(), '더 보기')] | //div[contains(text(), '더 보기')]")
                driver.execute_script("arguments[0].click();", more_btn)
                time.sleep(1)
            except:
                pass
            target_text = driver.find_element(By.TAG_NAME, "article").text

        if not target_text:
            return "<div>메뉴 내용을 찾지 못했습니다.</div>"

        lines = target_text.split("\n")
        filtered_lines = []
        account_name = url.rstrip("/").split("/")[-1]
        ui_keywords = ["팔로우", "Following", "AI 정보", "더 보기", "좋아요", "댓글", "게시물", "팔로잉"]

        for line in lines:
            line = line.strip()
            if not line or line in ["•", "·"] or line.isdigit():
                continue
            if line.startswith("#") or "naver.me" in line:
                break
            if line == account_name or line in ui_keywords:
                continue
            if any(kw in line for kw in ["시간 전", "일 전", "주 전", "개월 전", "년 전", "좋아요", "댓글 달기"]):
                continue
            filtered_lines.append(line)

        if not filtered_lines:
            return "<div>메뉴 내용을 찾지 못했습니다.</div>"

        formatted_text = "<br>".join(filtered_lines)
        return f'<div style="background-color:#f9f9f9; border:1px solid #ddd; padding:15px; border-radius:8px; text-align:left; font-size:15px; line-height:1.7; color:#333;">{formatted_text}</div>'
    except Exception as e:
        return "<div>인스타그램 메뉴를 불러오지 못했습니다.</div>"

# ==========================================================
# 10. 식당별 메뉴 수집
# ==========================================================

scraped_data = []
manual_menu = get_manual_menu_from_github_event()

print(f"\n{'='*60}\n자동 수집 시작")
if manual_menu:
    print("  -> MacroDroid로부터 데이터를 받았습니다!")
else:
    print("  -> 받은 데이터가 없어 기존 방식대로 실행합니다.")
print(f"{'='*60}")

for item in cafeteria_list:
    print(f"\n[{item['name']}] 정보 수집 중...")
    lat, lng = get_coords(item["address"])
    dist, walk_min = calculate_walking_info((lat, lng))
    html_content = ""

    if item["type"] == "ojeong":
        src = crop_ojeong_by_weekday(item["url"])
        html_content = f'<img src="{src}" style="display:block; margin:0 auto; max-width:100%; width:auto; height:auto;">' if src else "<div>오정 메뉴를 불러오지 못했습니다.</div>"

    elif item["type"] == "kakao_profile":
        img_src = get_kakao_profile_image(driver, item["url"], item["name"])
        html_content = f'<img src="{img_src}" style="display:block; margin:0 auto; max-width:100%; max-height:700px; width:auto; height:auto; border-radius:6px;">' if img_src else '<div style="padding:20px; font-weight:bold;">카카오 메뉴 이미지를 찾지 못했습니다.</div>'

    elif item["type"] == "kakao_first":
        img_src = get_kakao_first_image(driver, item["url"], item["name"])
        html_content = f'<img src="{img_src}" style="display:block; margin:0 auto; max-width:100%; max-height:700px; width:auto; height:auto; border-radius:6px;">' if img_src else '<div style="padding:20px; font-weight:bold;">카카오 메뉴 이미지를 찾지 못했습니다.</div>'

    elif item["type"] == "instagram":
        if manual_menu:
            html_content = f'<div style="background-color:#f9f9f9; border:1px solid #ddd; padding:15px; border-radius:8px; text-align:left; font-size:15px; line-height:1.7; color:#333;">{manual_menu.replace(chr(10), "<br>")}</div>'
        else:
            html_content = get_instagram_menu(driver, item["url"])

    scraped_data.append({"name": item["name"], "lat": lat, "lng": lng, "dist": dist, "walk_min": walk_min, "html": html_content})
    time.sleep(1.5)

# ==========================================================
# 11. Selenium 종료 및 구글 지도 생성 (여백 터치 팝업 유지, 팝업 터치 시 닫힘 및 원위치 복귀)
# ==========================================================

driver.quit()

print()
print("=" * 60)
print("자동 수집 완료!")
print("=" * 60)

menu_map = folium.Map(
    location=[37.4795, 126.8820],
    zoom_start=16,
    tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    attr='Google'
)

custom_header = """
<style>
@font-face {
    font-family: 'KakaoBigFont';
    src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2503@1.0/KakaoBigSans-Regular.woff2') format('woff2');
    font-weight: 400;
}
* {
    font-family: 'KakaoBigFont', sans-serif !important;
}

/* 팝업 닫기(X) 버튼 확대 */
.leaflet-popup-close-button {
    width: 40px !important;
    height: 40px !important;
    padding: 8px !important;
    font-size: 26px !important;
    color: #e74c3c !important;
    font-weight: bold !important;
}

/* 우측 상단 '전체보기' 버튼 스타일 */
.reset-map-btn {
    position: fixed;
    top: 15px;
    right: 15px;
    z-index: 99999;
    background: #ffffff;
    border: 3px solid #000000;
    padding: 10px 16px;
    font-weight: bold;
    font-size: 15px;
    border-radius: 10px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    cursor: pointer;
    color: #111;
}
</style>

<script>
let initialCenter = null;
let initialZoom = null;
let mapObj = null;

window.addEventListener('load', function() {
    setTimeout(function() {
        for (var key in window) {
            if (window[key] && window[key] instanceof L.Map) {
                mapObj = window[key];
                window.mapObj = mapObj; // 팝업 내부에서 참조할 수 있도록 전역 등록
                initialCenter = mapObj.getCenter();
                initialZoom = mapObj.getZoom();

                // 우측 상단 전체보기 버튼
                var btn = document.createElement('div');
                btn.innerHTML = '🗺️ 전체보기';
                btn.className = 'reset-map-btn';
                btn.onclick = function() {
                    if (mapObj) {
                        mapObj.closePopup();
                        if (initialCenter && initialZoom) {
                            mapObj.setView(initialCenter, initialZoom);
                        }
                    }
                };
                document.body.appendChild(btn);

                // 팝업이 닫힐 때 원위치 복귀
                mapObj.on('popupclose', function() {
                    if (initialCenter && initialZoom) {
                        mapObj.setView(initialCenter, initialZoom);
                    }
                });
                break;
            }
        }
    }, 400);
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        if (mapObj) {
            mapObj.closePopup();
        }
    }
});
</script>
"""
menu_map.get_root().html.add_child(folium.Element(custom_header))

for data in scraped_data:
    # ★ 팝업 창 안쪽을 터치하면 팝업이 닫히며 초기 지도 위치로 이동하도록 설정
    popup_html = f"""
    <div style="width:320px; text-align:center; padding-top:10px; cursor:pointer;" onclick="if(window.mapObj) {{ window.mapObj.closePopup(); }}">
        <h3 style="margin:5px 0; font-size:20px; color:#333;">{data['name']}</h3>
        <p style="margin:0 0 10px 0; font-size:13px; color:#e74c3c; font-weight:bold;">
            🏢 회사에서 도보 약 {data['walk_min']}분 ({data['dist']}m)
        </p>
        <hr style="margin:5px 0 10px 0;">
        <div style="width:100%; overflow:visible; text-align:center;">
            {data['html']}
        </div>
        <div style="font-size:11px; color:#888; margin-top:8px; font-style:italic;">(이미지나 상자를 터치하면 닫힙니다)</div>
    </div>
    """

    custom_icon = folium.DivIcon(
        icon_size=(150, 50),
        icon_anchor=(75, 25),
        html=f"""
        <div style="
            background-color: rgba(255, 255, 255, 0.95);
            border: 3px solid #000000;
            padding: 6px 12px;
            font-weight: bold;
            font-size: 15px;
            color: #111111;
            border-radius: 8px;
            white-space: nowrap;
            box-shadow: 0px 4px 8px rgba(0,0,0,0.3);
            text-align: center;
        ">
            {data['name']}
        </div>
        """
    )

    folium.Marker(
        location=[data["lat"], data["lng"]],
        # ★ close_onclick=False를 주어 지도 여백을 터치해도 팝업이 닫히지 않도록 고정
        popup=folium.Popup(popup_html, max_width=380, close_onclick=False),
        tooltip=data["name"],
        icon=custom_icon
    ).add_to(menu_map)

all_lats = [data["lat"] for data in scraped_data]
all_lngs = [data["lng"] for data in scraped_data]

if all_lats and all_lngs:
    menu_map.fit_bounds(
        [
            [min(all_lats), min(all_lngs)],
            [max(all_lats), max(all_lngs)]
        ],
        padding=(30, 30)
    )

output_file = "gasan_lunch_map.html"
menu_map.save(output_file)

print()
print("=" * 60)
print("🎉 여백 터치 유지 및 팝업 터치 시 닫힘/원위치 복귀 적용 완료!")
print(f"📄 파일 : {output_file}")
print("=" * 60)
