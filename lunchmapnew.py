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
# 1. 사용자 설정
# ==========================================================
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
# 4. 식당 목록 (총 5곳)
# ==========================================================
cafeteria_list = [
    {
        "name": "오정",
        "address": "서울 금천구 가산디지털2로 30",
        "type": "ojeong",
        "url": OJEONG_IMAGE_PATH
    },
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
# 7. 온정찬 전용 (카카오 포스트 이미지 수집)
# ==========================================================
def get_kakao_posts_image(driver, url):
    print(f"  -> [온정찬] 카카오 게시물 이미지 수집 중")
    try:
        driver.get(url)
        time.sleep(4)
        date_str_space = f"{today.month}월 {today.day}일"
        date_str_nospace = f"{today.month}월{today.day}일"
        
        posts = driver.find_elements(By.TAG_NAME, "div")
        for post in posts:
            try:
                text = post.text
                if date_str_space in text or date_str_nospace in text:
                    img = post.find_element(By.TAG_NAME, "img")
                    src = img.get_attribute("src")
                    if src and "k.kakaocdn.net/dn/" in src:
                        return src
            except:
                continue
        
        imgs = driver.find_elements(By.TAG_NAME, "img")
        for img in imgs:
            src = img.get_attribute("src")
            if src and "k.kakaocdn.net/dn/" in src:
                return src
        return None
    except Exception as e:
        print(f"  -> [온정찬] 오류 : {e}")
        return None

# ==========================================================
# 8. 카카오 - 런치투게더 전용
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
# 9. 카카오 - 밥심 전용
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
# 10. 스레드(Threads) - 런치타임 전용 크롤링
# ==========================================================
def get_threads_menu(driver, url):
    print(f"  -> [런치타임] 스레드 메뉴 수집 중 ({url})")
    try:
        driver.get(url)
        time.sleep(4)
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split("\n")
        
        target_date1 = today_date_str_nospace
        target_date2 = today_date_str_space
        
        start_idx = -1
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if target_date1 in line_clean or target_date2 in line_clean:
                start_idx = i
                break
        
        if start_idx == -1:
            start_idx = 0
            for i, line in enumerate(lines):
                if line.strip() in ["Reposts", "리포스트", "Media", "미디어"]:
                    start_idx = i + 1
                    break
        
        filtered_lines = []
        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue
            if "월" in line and "일" in line and target_date1 not in line and target_date2 not in line:
                break
            if line in ["스레드", "답글", "미디어", "리포스트", "팔로우", "언급", "로그인", "가입하기", "lunchtime_ypp", "Home", "Follow", "Mention", "Threads", "Replies", "Media", "Reposts", "Translate"]:
                continue
            if "팔로워" in line or "followers" in line or "시간 전" in line or "일 전" in line or line.endswith("h") or line.endswith("d") or line.isdigit():
                continue
            filtered_lines.append(line)
        
        last_tag_idx = -1
        for i, l in enumerate(filtered_lines):
            if l.startswith("#"):
                last_tag_idx = i
                
        if last_tag_idx != -1:
            filtered_lines = filtered_lines[:last_tag_idx + 1]
            
        if not filtered_lines:
            return "<div>오늘의 메뉴 내용을 찾지 못했습니다.</div>"
            
        formatted_text = "<br>".join(filtered_lines)
        return f'<div style="background-color:#f9f9f9; border:1px solid #ddd; padding:15px; border-radius:8px; text-align:left; font-size:15px; line-height:1.7; color:#333;">{formatted_text}</div>'
    except Exception as e:
        print(f"  -> [런치타임] 스레드 오류 : {e}")
        return "<div>스레드 메뉴를 불러오지 못했습니다.</div>"

# ==========================================================
# 11. 식당별 메뉴 수집
# ==========================================================
scraped_data = []

print(f"\n{'='*60}\n자동 수집 시작 (총 5곳)\n{'='*60}")

for item in cafeteria_list:
    print(f"\n[{item['name']}] 정보 수집 중...")
    lat, lng = get_coords(item["address"])
    dist, walk_min = calculate_walking_info((lat, lng))
    html_content = ""

    if item["type"] == "ojeong":
        src = crop_ojeong_by_weekday(item["url"])
        html_content = f'<img src="{src}" style="display:block; margin:0 auto; max-width:100%; width:auto; height:auto;">' if src else "<div>오정 메뉴를 불러오지 못했습니다.</div>"

    elif item["type"] == "kakao_posts":
        img_src = get_kakao_posts_image(driver, item["url"])
        html_content = f'<img src="{img_src}" style="display:block; margin:0 auto; max-width:100%; max-height:700px; border-radius:6px;">' if img_src else '<div style="padding:20px; font-weight:bold;">온정찬 메뉴 이미지를 찾지 못했습니다.</div>'

    elif item["type"] == "kakao_profile":
        img_src = get_kakao_profile_image(driver, item["url"], item["name"])
        html_content = f'<img src="{img_src}" style="display:block; margin:0 auto; max-width:100%; max-height:700px; border-radius:6px;">' if img_src else '<div style="padding:20px; font-weight:bold;">카카오 메뉴 이미지를 찾지 못했습니다.</div>'

    elif item["type"] == "kakao_first":
        img_src = get_kakao_first_image(driver, item["url"], item["name"])
        html_content = f'<img src="{img_src}" style="display:block; margin:0 auto; max-width:100%; max-height:700px; border-radius:6px;">' if img_src else '<div style="padding:20px; font-weight:bold;">카카오 메뉴 이미지를 찾지 못했습니다.</div>'

    elif item["type"] == "threads":
        html_content = get_threads_menu(driver, item["url"])

    scraped_data.append({"name": item["name"], "lat": lat, "lng": lng, "dist": dist, "walk_min": walk_min, "html": html_content})
    time.sleep(1.5)

# ==========================================================
# 12. Selenium 종료 및 구글 지도 생성 (모바일 반응형 완벽 대응)
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

.leaflet-popup-close-button {
    width: 40px !important;
    height: 40px !important;
    padding: 8px !important;
    font-size: 26px !important;
    color: #e74c3c !important;
    font-weight: bold !important;
}

.leaflet-popup-content-wrapper {
    background: rgba(255, 255, 255, 0.98) !important;
    box-shadow: 0 8px 25px rgba(0,0,0,0.4) !important;
    border-radius: 12px !important;
}

/* 우측 상단 '지도 정위치' 버튼 */
.reset-map-btn {
    position: fixed;
    top: 15px;
    right: 15px;
    z-index: 99999;
    background: #ffffff;
    border: 3px solid #000000;
    padding: 8px 14px;
    font-weight: bold;
    font-size: 14px;
    border-radius: 10px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    cursor: pointer;
    color: #111;
}

/* 우측 상단 '메뉴 한번에 보기 / 닫기' 버튼 */
.toggle-all-btn {
    position: fixed;
    top: 62px;
    right: 15px;
    z-index: 99999;
    background: #111111;
    border: 3px solid #000000;
    padding: 8px 14px;
    font-weight: bold;
    font-size: 14px;
    border-radius: 10px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    cursor: pointer;
    color: #ffffff;
    text-align: center;
}
.toggle-all-btn:hover {
    background: #333333;
}

/* 모바일 화면 대응 (너비 768px 이하) */
@media screen and (max-width: 768px) {
    .reset-map-btn { top: 10px; right: 10px; font-size: 12px; padding: 6px 10px; }
    .toggle-all-btn { top: 52px; right: 10px; font-size: 12px; padding: 6px 10px; }
}
</style>

<script>
let initialCenter = null;
let initialZoom = null;
let mapObj = null;
let allPopupsOpen = false;

window.addEventListener('load', function() {
    setTimeout(function() {
        for (var key in window) {
            if (window[key] && window[key] instanceof L.Map) {
                mapObj = window[key];
                window.mapObj = mapObj;
                initialCenter = mapObj.getCenter();
                initialZoom = mapObj.getZoom();

                // 1. 지도 정위치 버튼 기능
                var btn = document.createElement('div');
                btn.innerHTML = '🗺️ 지도 정위치';
                btn.className = 'reset-map-btn';
                btn.onclick = function() {
                    if (mapObj) {
                        mapObj.eachLayer(function(layer) {
                            if (layer instanceof L.Marker && layer.getPopup()) {
                                layer.closePopup();
                            }
                        });
                        allPopupsOpen = false;
                        var toggleBtn = document.querySelector('.toggle-all-btn');
                        if (toggleBtn) toggleBtn.innerHTML = '📋 메뉴 한번에 보기 / 닫기';
                        if (initialCenter && initialZoom) {
                            mapObj.setView(initialCenter, initialZoom);
                        }
                    }
                };
                document.body.appendChild(btn);

                // 2. 메뉴 한번에 보기 / 닫기 토글 버튼 기능 (모바일/PC 분기 처리)
                var toggleBtn = document.createElement('div');
                toggleBtn.innerHTML = '📋 메뉴 한번에 보기 / 닫기';
                toggleBtn.className = 'toggle-all-btn';
                toggleBtn.onclick = function() {
                    if (!mapObj) return;
                    
                    // 모바일 기기인 경우 화면 깨짐 방지를 위해 가로 강제 정렬을 하지 않고 기본 팝업으로 오픈
                    if (window.innerWidth <= 768) {
                        if (!allPopupsOpen) {
                            mapObj.eachLayer(function(layer) {
                                if (layer instanceof L.Marker && layer.getPopup()) {
                                    layer.openPopup();
                                }
                            });
                            toggleBtn.innerHTML = '❌ 메뉴 닫기';
                            allPopupsOpen = true;
                        } else {
                            mapObj.eachLayer(function(layer) {
                                if (layer instanceof L.Marker && layer.getPopup()) {
                                    layer.closePopup();
                                }
                            });
                            toggleBtn.innerHTML = '📋 메뉴 한번에 보기 / 닫기';
                            allPopupsOpen = false;
                        }
                        return;
                    }

                    // PC 화면 전용 가로 정렬 로직
                    if (!allPopupsOpen) {
                        let curCenter = mapObj.getCenter();
                        let curZoom = mapObj.getZoom();

                        mapObj.eachLayer(function(layer) {
                            if (layer instanceof L.Marker && layer.getPopup()) {
                                layer.openPopup();
                            }
                        });
                        
                        mapObj.setView(curCenter, curZoom, {animate: false});
                        
                        setTimeout(function() {
                            var popups = document.querySelectorAll('.leaflet-popup');
                            if (popups.length > 0) {
                                var screenW = window.innerWidth;
                                var maxRight = screenW - 210;
                                var startLeft = 15;
                                var availableW = maxRight - startLeft;
                                var popupW = Math.floor((availableW - (6 * (popups.length - 1))) / popups.length);
                                if (popupW < 220) popupW = 220;

                                popups.forEach(function(p, index) {
                                    p.style.position = 'fixed';
                                    p.style.top = '50px';
                                    
                                    var contentWrapper = p.querySelector('.leaflet-popup-content-wrapper');
                                    if (contentWrapper) {
                                        contentWrapper.style.width = popupW + 'px';
                                    }
                                    var content = p.querySelector('.leaflet-popup-content');
                                    if (content) {
                                        content.style.width = (popupW - 20) + 'px';
                                        content.style.margin = '10px';
                                    }
                                    
                                    var leftPos = startLeft + (index * (popupW + 6));
                                    p.style.left = leftPos + 'px';
                                    p.style.transform = 'none';
                                });
                            }
                        }, 50);

                        toggleBtn.innerHTML = '❌ 메뉴 닫기';
                        allPopupsOpen = true;
                    } else {
                        mapObj.eachLayer(function(layer) {
                            if (layer instanceof L.Marker && layer.getPopup()) {
                                layer.closePopup();
                            }
                        });
                        toggleBtn.innerHTML = '📋 메뉴 한번에 보기 / 닫기';
                        allPopupsOpen = false;
                    }
                };
                document.body.appendChild(toggleBtn);

                // 3. 개별 팝업이 닫힐 때 처리 (원래 지도 위치로 복구)
                mapObj.on('popupclose', function() {
                    setTimeout(function() {
                        var anyOpen = false;
                        mapObj.eachLayer(function(layer) {
                            if (layer instanceof L.Marker && layer.getPopup() && layer.isPopupOpen()) {
                                anyOpen = true;
                            }
                        });
                        if (!anyOpen) {
                            allPopupsOpen = false;
                            var toggleBtn = document.querySelector('.toggle-all-btn');
                            if (toggleBtn) toggleBtn.innerHTML = '📋 메뉴 한번에 보기 / 닫기';
                            
                            var popups = document.querySelectorAll('.leaflet-popup');
                            popups.forEach(function(p) {
                                p.style.position = '';
                                p.style.top = '';
                                p.style.left = '';
                                p.style.transform = '';
                                var cw = p.querySelector('.leaflet-popup-content-wrapper');
                                if (cw) cw.style.width = '';
                                var c = p.querySelector('.leaflet-popup-content');
                                if (c) { c.style.width = ''; c.style.margin = ''; }
                            });

                            // 모든 팝업이 닫혔을 때 원래 지정된 초기 위치로 부드럽게 복구
                            if (initialCenter && initialZoom) {
                                mapObj.setView(initialCenter, initialZoom);
                            }
                        }
                    }, 150);
                });

                break;
            }
        }
    }, 400);
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        if (mapObj) {
            mapObj.eachLayer(function(layer) {
                if (layer instanceof L.Marker && layer.getPopup()) {
                    layer.closePopup();
                }
            });
            allPopupsOpen = false;
            var toggleBtn = document.querySelector('.toggle-all-btn');
            if (toggleBtn) toggleBtn.innerHTML = '📋 메뉴 한번에 보기 / 닫기';
            var popups = document.querySelectorAll('.leaflet-popup');
            popups.forEach(function(p) {
                p.style.position = '';
                p.style.top = '';
                p.style.left = '';
                p.style.transform = '';
                var cw = p.querySelector('.leaflet-popup-content-wrapper');
                if (cw) cw.style.width = '';
                var c = p.querySelector('.leaflet-popup-content');
                if (c) { c.style.width = ''; c.style.margin = ''; }
            });
            if (initialCenter && initialZoom) {
                mapObj.setView(initialCenter, initialZoom);
            }
        }
    }
});
</script>
"""
menu_map.get_root().html.add_child(folium.Element(custom_header))

for data in scraped_data:
    # 모바일에서도 이미지와 레이아웃이 꽉 차게 반응하도록 너비 수정
    popup_html = f"""
    <div style="width:100%; max-width:280px; box-sizing:border-box; text-align:center; padding-top:5px; cursor:pointer;" onclick="if(window.mapObj) {{ window.mapObj.closePopup(); }}">
        <h3 style="margin:5px 0; font-size:18px; color:#333;">{data['name']}</h3>
        <p style="margin:0 0 8px 0; font-size:12px; color:#e74c3c; font-weight:bold;">
            🏢 회사에서 도보 약 {data['walk_min']}분 ({data['dist']}m)
        </p>
        <hr style="margin:5px 0 8px 0;">
        <div style="width:100%; overflow:hidden; text-align:center;">
            {data['html']}
        </div>
        <div style="font-size:11px; color:#888; margin-top:6px; font-style:italic;">(이미지나 상자를 터치하면 닫힙니다)</div>
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
        popup=folium.Popup(popup_html, max_width=320, auto_close=False, close_onclick=False),
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
print("🎉 모바일 반응형 대응 & 닫기 정위치 복구 완료!")
print(f"📄 파일 : {output_file}")
print("=" * 60)
