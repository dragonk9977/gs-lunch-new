import os
import re
import time
import json
import base64
import requests
import google.generativeai as genai
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# ==========================================================
# 1. 기본 설정 및 Gemini API 설정
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OJEONG_IMAGE_PATH = os.path.join(BASE_DIR, "오정메뉴.jpg")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "menu.json")

OFFICE_ADDRESS = "서울 금천구 가산디지털2로 30"

weekdays = ["월", "화", "수", "목", "금", "토", "일"]

today = datetime.now(ZoneInfo("Asia/Seoul"))
today_weekday_index = today.weekday()
today_weekday = weekdays[today_weekday_index]

today_date_str_space = f"{today.month}월 {today.day}일"
today_date_str_nospace = f"{today.month}월{today.day}일"

ojeong_weekday_index = min(today_weekday_index, 4)

print()
print("=" * 60)
print(f"오늘 날짜 : {today_date_str_space} ({today_weekday}요일)")
print("=" * 60)

# Gemini API 초기화
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ==========================================================
# 2. 식당 정보 (호서구내식당 추가 완료)
# ==========================================================

cafeteria_list = [
    {
        "name": "오정",
        "address": "서울 금천구 가산디지털2로 30",
        "type": "ojeong",
        "url": OJEONG_IMAGE_PATH,
        "exact_lat": 37.47120020547345,
        "exact_lng": 126.88352033871539,
    },
    {
        "name": "온정찬",
        "address": "서울 금천구 가산디지털1로 75-15",
        "type": "kakao_posts",
        "url": "https://pf.kakao.com/_UIdXn/posts",
        "exact_lat": 37.47218918507373,
        "exact_lng": 126.88410160863671,
    },
    {
        "name": "런치투게더",
        "address": "서울 금천구 가산디지털1로 58",
        "type": "kakao_profile",
        "url": "https://pf.kakao.com/_swtYxl",
        "exact_lat": 37.471346435440815,
        "exact_lng": 126.88633772331427,
    },
    {
        "name": "런치타임",
        "address": "서울 금천구 가산디지털2로 24",
        "type": "instagram_threads",
        "instagram_url": "https://www.instagram.com/lunchtime_ypp/",
        "threads_url": "https://www.threads.net/@lunchtime_ypp",
        "exact_lat": 37.47089827252637,
        "exact_lng": 126.88388201555182,
    },
    {
        "name": "밥심",
        "address": "서울 금천구 가산디지털2로 46",
        "type": "kakao_first",
        "url": "https://pf.kakao.com/_mHWxjX",
        "exact_lat": 37.472650897653246,
        "exact_lng": 126.8826763789836,
    },
    {
        "name": "호서구내식당",
        "address": "서울 금천구 가산디지털1로 70",
        "type": "hoseo_ai",
        "profile_id": "hoseofood",
        "exact_lat": 37.47245465756811,
        "exact_lng": 126.88608348190839,
    },
]


# ==========================================================
# 3. 오정 메뉴 - 요일별 이미지 Crop
# ==========================================================

def crop_ojeong_by_weekday(image_path):
    try:
        img = Image.open(image_path)
        width, height = img.size

        left_margin = width * 0.05
        right_margin = width * 0.95
        top_margin = height * 0.08
        bottom_margin = height * 0.92

        table_width = right_margin - left_margin
        col_width = table_width / 5

        crop_left = left_margin + (col_width * ojeong_weekday_index)
        crop_right = crop_left + col_width

        cropped_img = img.crop(
            (crop_left, top_margin, crop_right, bottom_margin)
        )

        max_height = 420

        if cropped_img.height > max_height:
            ratio = max_height / cropped_img.height
            new_width = int(cropped_img.width * ratio)
            cropped_img = cropped_img.resize(
                (new_width, max_height),
                Image.LANCZOS
            )

        buffered = BytesIO()
        cropped_img.save(
            buffered,
            format="JPEG",
            quality=95
        )

        encoded_string = base64.b64encode(
            buffered.getvalue()
        ).decode("utf-8")

        print(
            f"  -> [오정] {weekdays[ojeong_weekday_index]}요일 메뉴 Crop 완료"
        )

        return "data:image/jpeg;base64," + encoded_string

    except Exception as e:
        print(f"  -> [오정] Crop 실패 : {e}")
        return None


# ==========================================================
# 4. Selenium
# ==========================================================

def create_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1000")

    options.add_argument(
        "--user-agent=Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(options=options)


# ==========================================================
# 5. 카카오 - 온정찬
# ==========================================================

def get_kakao_posts_image(driver, url):
    print("  -> [온정찬] 카카오 게시물 이미지 수집 중")

    try:
        driver.get(url)
        time.sleep(4)

        posts = driver.find_elements(By.TAG_NAME, "div")

        for post in posts:
            try:
                text = post.text

                if (
                    today_date_str_space in text
                    or today_date_str_nospace in text
                ):
                    img = post.find_element(By.TAG_NAME, "img")
                    src = img.get_attribute("src")

                    if src and "k.kakaocdn.net/dn/" in src:
                        return src

            except Exception:
                continue

        imgs = driver.find_elements(By.TAG_NAME, "img")

        for img in imgs:
            try:
                src = img.get_attribute("src")

                if src and "k.kakaocdn.net/dn/" in src:
                    return src

            except Exception:
                continue

        return None

    except Exception as e:
        print(f"  -> [온정찬] 오류 : {e}")
        return None


# ==========================================================
# 6. 카카오 - 런치투게더
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
                    "height": size["height"],
                })

            except Exception:
                continue

        if not kakao_imgs:
            return None

        profile_candidates = [
            item for item in kakao_imgs
            if (
                item["width"] <= 250
                and item["height"] <= 250
                and item["width"] > 0
            )
        ]

        if not profile_candidates:
            profile_candidates = [kakao_imgs[0]]

        profile = profile_candidates[0]
        profile_element = profile["element"]

        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                profile_element
            )
            time.sleep(0.5)
            driver.execute_script(
                "arguments[0].click();",
                profile_element
            )

        except Exception:
            try:
                profile_element.click()
            except Exception:
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
                width = size["width"]
                height = size["height"]

                if width < 150 or height < 150:
                    continue

                modal_candidates.append({
                    "src": src,
                    "width": width,
                    "height": height,
                    "area": width * height,
                })

            except Exception:
                continue

        if modal_candidates:
            modal_candidates.sort(
                key=lambda x: x["area"],
                reverse=True
            )
            return modal_candidates[0]["src"]

        return profile["src"]

    except Exception as e:
        print(f"  -> [{store_name}] 카카오 오류 : {e}")
        return None


# ==========================================================
# 7. 카카오 - 밥심
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

                if not src or "k.kakaocdn.net/dn/" not in src:
                    continue

                size = img.size
                width = size.get("width", 0)
                height = size.get("height", 0)

                if (
                    width > 250
                    or height > 250
                    or (width == 0 and height == 0)
                ):
                    valid_candidates.append(src)

            except Exception:
                continue

        if valid_candidates:
            return valid_candidates[0]

        for img in imgs:
            try:
                src = img.get_attribute("src")

                if src and "k.kakaocdn.net/dn/" in src:
                    return src

            except Exception:
                continue

        return None

    except Exception as e:
        print(f"  -> [{store_name}] 카카오 오류 : {e}")
        return None


# ==========================================================
# 8. Instagram - 런치타임
# ==========================================================

def find_instagram_post_links(driver, profile_url):
    driver.get(profile_url)
    time.sleep(5)

    links = []

    for a in driver.find_elements(By.TAG_NAME, "a"):
        try:
            href = a.get_attribute("href")

            if not href:
                continue

            if "/p/" in href or "/reel/" in href:
                clean = href.split("?")[0]

                if clean not in links:
                    links.append(clean)

        except Exception:
            continue

    return links


def parse_instagram_post_date(body_text):
    pattern = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")

    for line in body_text.splitlines():
        match = pattern.fullmatch(line.strip())

        if match:
            return int(match.group(1)), int(match.group(2))

    match = pattern.search(body_text)

    if match:
        return int(match.group(1)), int(match.group(2))

    return None


def extract_instagram_menu_from_post(body_text):
    lines = [
        line.strip().replace("\\", "")
        for line in body_text.splitlines()
    ]

    lines = [line for line in lines if line]

    date_index = -1

    date_pattern = re.compile(
        rf"{today.month}월\s*{today.day}일"
    )

    for i, line in enumerate(lines):
        if date_pattern.search(line):
            date_index = i
            break

    if date_index == -1:
        return None

    menu_lines = []

    ignored = {
        "로그인", "가입하기", "팔로우", "팔로우하기", "Follow", "Following", 
        "Threads", "Instagram", "홈", "Home", "좋아요", "댓글", "공유", 
        "보내기", "저장", "번역", "Translate", "더 보기", "More",
    }

    for line in lines[date_index + 1:]:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            break

        if line in ignored:
            continue

        if line == "lunchtime_ypp":
            continue

        if "팔로워" in line or "followers" in line:
            continue

        if re.fullmatch(r"\d+\s*(초|분|시간|일|주|개월|년)\s*전", line):
            continue

        if re.fullmatch(r"\d+\s*[smhdw]", line, re.IGNORECASE):
            continue

        if line.isdigit():
            continue

        menu_lines.append(line)

    if not menu_lines:
        return None

    return menu_lines


def get_instagram_menu(driver, profile_url):
    print("  -> [런치타임] Instagram 게시글 메뉴 수집 중")

    try:
        links = find_instagram_post_links(driver, profile_url)
        print(f"     Instagram 게시글 링크 {len(links)}개 발견")

        for post_url in links[:10]:
            try:
                driver.get(post_url)
                time.sleep(3)
                body_text = driver.find_element(By.TAG_NAME, "body").text
                post_date = parse_instagram_post_date(body_text)

                if not post_date:
                    continue

                post_month, post_day = post_date

                if post_month != today.month or post_day != today.day:
                    continue

                menu_lines = extract_instagram_menu_from_post(body_text)

                if menu_lines:
                    print("     Instagram 오늘 게시글 발견")
                    return {
                        "source": "instagram",
                        "source_url": post_url,
                        "menu_lines": menu_lines,
                    }

            except Exception as e:
                print(f"     게시글 확인 실패: {e}")
                continue

        print("     오늘 Instagram 게시글을 찾지 못했습니다.")

    except Exception as e:
        print(f"  -> [런치타임] Instagram 오류 : {e}")

    return None


# ==========================================================
# 9. Threads - 런치타임 fallback
# ==========================================================

def get_threads_menu(driver, url):
    print("  -> [런치타임] Threads fallback 수집 중")

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
            return None

        filtered_lines = []

        ignored = {
            "스레드", "답글", "미디어", "리포스트", "팔로우", "언급", "로그인", 
            "가입하기", "lunchtime_ypp", "Home", "Follow", "Mention", 
            "Threads", "Replies", "Media", "Reposts", "Translate",
        }

        for line in lines[start_idx + 1:]:
            line = line.strip().replace("\\", "")

            if not line:
                continue

            if "월" in line and "일" in line and target_date1 not in line and target_date2 not in line:
                break

            if line in ignored:
                continue

            if ("팔로워" in line or "followers" in line or "시간 전" in line 
                or "일 전" in line or line.endswith("h") or line.endswith("d") or line.isdigit()):
                continue

            filtered_lines.append(line)

        if not filtered_lines:
            return None

        for i, line in enumerate(filtered_lines):
            if line.startswith("#"):
                filtered_lines = filtered_lines[:i]
                break

        if not filtered_lines:
            return None

        return {
            "source": "threads",
            "source_url": url,
            "menu_lines": filtered_lines,
        }

    except Exception as e:
        print(f"  -> [런치타임] Threads 오류 : {e}")
        return None


# ==========================================================
# 10. (NEW) 호서구내식당 - Gemini AI 요약 및 데이터 수집
# ==========================================================

def summarize_with_gemini(content, is_image=False):
    """Gemini API를 이용해 장황한 텍스트나 이미지를 깔끔한 식단 리스트로 요약합니다."""
    if not GEMINI_API_KEY:
        print("     -> [오류] GEMINI_API_KEY가 깃허브 시크릿에 설정되지 않았습니다.")
        return None
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        제시된 자료는 '호서구내식당'의 식단 정보입니다.
        오늘({today.month}월 {today.day}일)의 메뉴이거나 '오늘의 메뉴'라는 언급이 있다면,
        '시원한 감칠맛을 담아', '호로록 즐기는', '육즙 가득 쪄낸' 등의 쓸데없는 수식어와 인사말, 해시태그를 모두 지우고
        오직 핵심 반찬 이름(예: 바지락칼국수, 보리밥, 계란후라이 등)만 추출해서 한 줄에 하나씩 출력해주세요.
        
        만약 식단 정보가 아니거나, 오늘 날짜가 아니라면 오직 "NOT_MENU"라고만 출력하세요.
        마크다운 기호(```html 등)나 부가 설명 없이 순수 텍스트 결과만 출력하세요.
        """
        
        if is_image:
            image_parts = [{"mime_type": "image/jpeg", "data": content}]
            response = model.generate_content([prompt, image_parts[0]])
        else:
            response = model.generate_content(f"{prompt}\n\n[식단 텍스트]\n{content}")
            
        result = response.text.strip()
        
        if "NOT_MENU" in result or not result:
            return None
            
        # AI가 반환한 텍스트를 HTML 태그로 묶어 깔끔하게 스타일링
        lines = result.split('\n')
        safe_lines = [f'<div class="menu-line" style="padding:4px 0;">{line.strip("- *")}</div>' for line in lines if line.strip()]
        
        html_out = f"""
        <div class="text-menu" style="background-color:#f9fafb; border:1px solid #e5e7eb; padding:15px; border-radius:10px; font-weight:700; color:#1f2937; text-align:center;">
            {"".join(safe_lines)}
        </div>
        """
        return html_out
        
    except Exception as e:
        print(f"     -> Gemini API 호출 실패: {e}")
        return None

def get_hoseo_menu(driver, profile_id):
    print("  -> [호서구내식당] Gemini AI 기반 메뉴 탐색 시작")
    
    # 1단계: Picuki 익명 뷰어에서 텍스트 게시물 먼저 확인 (가장 가볍고 빠름)
    try:
        driver.get(f"[https://www.picuki.com/profile/](https://www.picuki.com/profile/){profile_id}")
        time.sleep(4)
        posts = driver.find_elements(By.CSS_SELECTOR, ".photo-description")
        
        for post in posts[:2]:
            text = post.text.strip()
            if "오늘의 메뉴" in text or f"{today.month}월" in text:
                print("     -> 오늘 게시물 텍스트 발견! AI 요약 진행...")
                summary_html = summarize_with_gemini(text, is_image=False)
                if summary_html:
                    return {"html": summary_html, "source": "instagram_post_ai"}
    except Exception as e:
        print(f"     -> Picuki 게시물 확인 실패: {e}")
        
    # 2단계: 텍스트 게시물이 없다면 (오전 시간대), 익명 스토리 뷰어에서 이미지 추출 후 AI 비전 판독
    print("     -> 텍스트 게시물 없음. 스토리 뷰어를 통한 이미지 탐색 시도...")
    viewer_urls = [
        f"[https://instanavigation.com/user-profile/](https://instanavigation.com/user-profile/){profile_id}",
        f"[https://iganony.io/profile/](https://iganony.io/profile/){profile_id}"
    ]
    
    for url in viewer_urls:
        try:
            driver.get(url)
            time.sleep(5)
            imgs = driver.find_elements(By.TAG_NAME, "img")
            candidates = []
            
            for img in imgs:
                src = img.get_attribute("src")
                if not src or "avatar" in src or "logo" in src: 
                    continue
                # 스토리 이미지 해상도 특성(세로로 긴 형태)으로 1차 필터링
                width = img.size.get("width", 0)
                height = img.size.get("height", 0)
                if height > width and height > 150:
                    candidates.append(src)
                    
            # 최신 3개의 이미지만 다운로드하여 AI에게 "오늘 메뉴판이 맞는지" 판독 요청
            for src in candidates[:3]:
                resp = requests.get(src, timeout=5)
                if resp.status_code == 200:
                    print("     -> 스토리 이미지 분석 중...")
                    summary_html = summarize_with_gemini(resp.content, is_image=True)
                    if summary_html:
                        print("     -> AI가 스토리 이미지에서 메뉴를 성공적으로 요약했습니다!")
                        return {"html": summary_html, "source": "instagram_story_ai"}
        except Exception as e:
            print(f"     -> 스토리 탐색 중 오류: {e}")
            
    return None


# ==========================================================
# 11. 메뉴 HTML 변환 (기존 텍스트용)
# ==========================================================

def menu_lines_to_html(menu_lines):
    if not menu_lines:
        return "<div>오늘의 메뉴를 찾지 못했습니다.</div>"

    safe_lines = []

    for line in menu_lines:
        line = (
            line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )

        safe_lines.append(
            f'<div class="menu-line">{line}</div>'
        )

    return """
    <div class="text-menu">
        %s
    </div>
    """ % "\n".join(safe_lines)


# ==========================================================
# 12. 주소 → 좌표 (정확한 고정 좌표값 사용)
# ==========================================================

geolocator = Nominatim(user_agent="gasan_lunch_map_new")
geocode_cache = {}

def get_coords(address):
    if address in geocode_cache:
        return geocode_cache[address]
    try:
        loc = geolocator.geocode(address, timeout=10)
        if loc:
            coords = (float(loc.latitude), float(loc.longitude))
            geocode_cache[address] = coords
            return coords
    except Exception as e:
        print(f"  -> 주소 좌표 변환 실패: {address} / {e}")
    
    fallback = (37.471364252495015, 126.88404214632791) 
    geocode_cache[address] = fallback
    return fallback

office_coords = (37.471364252495015, 126.88404214632791)

def calculate_walking_info(dest_coords):
    try:
        dist_meters = geodesic(
            office_coords,
            dest_coords
        ).meters

        walk_minutes = round(
            dist_meters / 70
        )

        walk_minutes = max(
            1,
            walk_minutes
        )

        return int(dist_meters), walk_minutes

    except Exception:
        return 0, 0


# ==========================================================
# 13. 실제 데이터 수집
# ==========================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

previous_data = {}
if os.path.exists(OUTPUT_JSON):
    try:
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            previous_data = json.load(f)
    except Exception:
        previous_data = {}

previous_restaurants = {
    item.get("name"): item
    for item in previous_data.get("restaurants", [])
}

driver = None
scraped_data = []

try:
    driver = create_driver()

    print()
    print("=" * 60)
    print("자동 수집 시작")
    print("=" * 60)

    for item in cafeteria_list:

        print()
        print(f"[{item['name']}] 정보 수집 중...")

        if "exact_lat" in item and "exact_lng" in item:
            lat = item["exact_lat"]
            lng = item["exact_lng"]
        else:
            base_lat, base_lng = get_coords(item["address"])
            lat = base_lat + item.get("lat_offset", 0)
            lng = base_lng + item.get("lng_offset", 0)

        dist, walk_min = calculate_walking_info(
            (lat, lng)
        )

        html_content = ""
        source = ""

        if item["type"] == "ojeong":

            src = crop_ojeong_by_weekday(
                item["url"]
            )

            if src:
                html_content = f"""
                <img
                    src="{src}"
                    class="menu-image"
                    alt="오정 오늘의 메뉴"
                >
                """
                source = "local_image"
            else:
                html_content = """
                <div class="error-menu">
                    오정 메뉴를 불러오지 못했습니다.
                </div>
                """

        elif item["type"] == "kakao_posts":

            img_src = get_kakao_posts_image(
                driver,
                item["url"]
            )

            if img_src:
                html_content = f"""
                <img
                    src="{img_src}"
                    class="menu-image"
                    alt="온정찬 오늘의 메뉴"
                >
                """
                source = "kakao_posts"
            else:
                html_content = """
                <div class="error-menu">
                    온정찬 메뉴 이미지를 찾지 못했습니다.
                </div>
                """

        elif item["type"] == "kakao_profile":

            img_src = get_kakao_profile_image(
                driver,
                item["url"],
                item["name"]
            )

            if img_src:
                html_content = f"""
                <img
                    src="{img_src}"
                    class="menu-image"
                    alt="런치투게더 오늘의 메뉴"
                >
                """
                source = "kakao_profile"
            else:
                html_content = """
                <div class="error-menu">
                    카카오 메뉴 이미지를 찾지 못했습니다.
                </div>
                """

        elif item["type"] == "instagram_threads":

            result = get_instagram_menu(
                driver,
                item["instagram_url"]
            )

            if result:

                html_content = menu_lines_to_html(
                    result["menu_lines"]
                )

                source = result["source"]

            else:

                print(
                    "     → Instagram 실패. Threads로 전환합니다."
                )

                result = get_threads_menu(
                    driver,
                    item["threads_url"]
                )

                if result:

                    html_content = menu_lines_to_html(
                        result["menu_lines"]
                    )

                    source = result["source"]

                else:

                    html_content = """
                    <div class="error-menu">
                        오늘의 런치타임 메뉴를 찾지 못했습니다.
                    </div>
                    """

                    source = "none"

        elif item["type"] == "kakao_first":

            img_src = get_kakao_first_image(
                driver,
                item["url"],
                item["name"]
            )

            if img_src:
                html_content = f"""
                <img
                    src="{img_src}"
                    class="menu-image"
                    alt="밥심 오늘의 메뉴"
                >
                """
                source = "kakao_first"
            else:
                html_content = """
                <div class="error-menu">
                    카카오 메뉴 이미지를 찾지 못했습니다.
                </div>
                """

        # 호서구내식당 AI 처리기 연결 부분
        elif item["type"] == "hoseo_ai":
            
            result = get_hoseo_menu(driver, item["profile_id"])
            
            if result:
                html_content = result["html"]
                source = result["source"]
            else:
                html_content = """
                <div class="error-menu">
                    호서구내식당 오늘 메뉴를 찾지 못했습니다.
                </div>
                """
                source = "none"

        previous = previous_restaurants.get(item["name"])
        menu_status = "today"

        failed_this_run = (
            not html_content
            or source == "none"
            or "찾지 못했습니다" in html_content
            or "불러오지 못했습니다" in html_content
        )

        if (
            failed_this_run
            and previous
            and previous_data.get("date") == today.strftime("%Y-%m-%d")
            and previous.get("html")
            and previous.get("source") not in ("none", "")
        ):
            html_content = previous["html"]
            source = previous["source"]
            menu_status = "preserved_from_previous_run"
            print(f"     → [{item['name']}] 이전 정상 수집 메뉴 유지")

        elif failed_this_run:
            menu_status = "missing"

        scraped_data.append({
            "name": item["name"],
            "address": item["address"],
            "lat": lat,
            "lng": lng,
            "dist": dist,
            "walk_min": walk_min,
            "source": source,
            "html": html_content,
            "menu_status": menu_status,
            "menu_date": today.strftime("%Y-%m-%d") if menu_status != "missing" else None,
        })

        time.sleep(1.5)

finally:

    if driver:
        driver.quit()


# ==========================================================
# 14. menu.json 저장
# ==========================================================

result = {
    "updated_at": today.strftime(
        "%Y-%m-%d %H:%M:%S"
    ),
    "updated_at_display": today.strftime(
        "%Y.%m.%d %H:%M"
    ),
    "date": today.strftime(
        "%Y-%m-%d"
    ),
    "date_display": today_date_str_space,
    "weekday": today_weekday,
    "office": {
        "address": OFFICE_ADDRESS,
        "lat": office_coords[0],
        "lng": office_coords[1],
    },
    "restaurants": scraped_data,
}


with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("=" * 60)
print("자동 수집 완료")
print(f"저장 파일 : {OUTPUT_JSON}")
print("=" * 60)
