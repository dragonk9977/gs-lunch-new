import os
import folium

# MacroDroid로부터 전달받은 메뉴 텍스트
payload_text = os.environ.get("MENU_TEXT", "")
if not payload_text:
    payload_text = "MacroDroid 알림 대기 중..."

scraped_data = []

# 1. 밥심
scraped_data.append({
    'name': '밥심',
    'lat': 37.4812,
    'lng': 126.8815,
    'walk_min': 4,
    'dist': 250,
    'html': "<div style='font-size:14px; text-align:center; color:#555;'>기본 식당 정보</div>"
})

# 2. 런치투게더
scraped_data.append({
    'name': '런치투게더',
    'lat': 37.4780,
    'lng': 126.8850,
    'walk_min': 5,
    'dist': 320,
    'html': "<div style='font-size:14px; text-align:center; color:#555;'>기본 식당 정보</div>"
})

# 3. 런치타임 (MacroDroid 연동 데이터)
lunchtime_html = f"""
<div style='font-size:15px; line-height:1.6; color:#333; text-align:left; padding:12px; background-color:#f9f9f9; border-radius:10px; border-left: 5px solid #2ecc71;'>
    <strong style="color:#27ae60;">📢 오늘의 메뉴 (런치타임)</strong><br>
    <hr style="border:0; border-top:1px solid #ddd; margin:10px 0;">
    {payload_text.replace(chr(10), '<br>')}
</div>
"""
scraped_data.append({
    'name': '런치타임',
    'lat': 37.4785,
    'lng': 126.8820,
    'walk_min': 3,
    'dist': 180,
    'html': lunchtime_html
})

# 4. 오정 (온정찬)
onjeongchan_html = """
<div style='font-size:14px; line-height:1.6; color:#333; text-align:center; padding:12px; background-color:#fff8f0; border-radius:10px; border-left: 5px solid #e67e22;'>
    <strong style="color:#e67e22; font-size:16px;">🔥 오정 (온정찬)</strong><br>
    <p style="margin:8px 0; color:#555; font-size:13px;">최신 메뉴를 바로 확인할 수 있습니다.</p>
    <a href="https://pf.kakao.com/_UIdXn/posts" target="_blank" style="display:inline-block; margin-top:8px; background:#fee500; color:#3c1e1e; padding:10px 18px; border-radius:6px; font-weight:bold; text-decoration:none; font-size:14px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
        👉 오정 최신 메뉴 보러가기
    </a>
</div>
"""
scraped_data.append({
    'name': '오정',
    'lat': 37.4798,
    'lng': 126.8835,
    'walk_min': 3,
    'dist': 200,
    'html': onjeongchan_html
})

# 구글 지도 생성
menu_map = folium.Map(
    location=[37.4790, 126.8820],
    zoom_start=16,
    tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    attr='Google'
)

# 상단 전체보기 버튼
custom_header = """
<style>
.reset-map-btn { position: fixed; top: 15px; right: 15px; z-index: 99999; background: #fff; border: 3px solid #000; padding: 10px 16px; font-weight: bold; border-radius: 10px; cursor: pointer; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); }
</style>
<script>
window.addEventListener('load', function() {
    setTimeout(function() {
        for (var key in window) {
            if (window[key] && window[key] instanceof L.Map) {
                var mapObj = window[key];
                var btn = document.createElement('div');
                btn.innerHTML = '🗺️ 전체보기';
                btn.className = 'reset-map-btn';
                btn.onclick = function() { mapObj.closePopup(); mapObj.setView([37.4790, 126.8820], 16); };
                document.body.appendChild(btn);
                break;
            }
        }
    }, 500);
});
</script>
"""
menu_map.get_root().html.add_child(folium.Element(custom_header))

# 마커 추가
for data in scraped_data:
    popup_html = f"""
    <div style="width:280px; text-align:center; padding:5px;">
        <h3 style="margin:8px 0; font-size:18px;">{data['name']}</h3>
        <p style="font-size:12px; color:#e74c3c; font-weight:bold;">도보 {data['walk_min']}분 ({data['dist']}m)</p>
        <hr style="margin:5px 0;">
        {data['html']}
    </div>
    """
    folium.Marker(
        location=[data["lat"], data["lng"]],
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=data["name"],
        icon=folium.DivIcon(html=f'<div style="background:#fff; border:2px solid #000; padding:5px 10px; font-weight:bold; border-radius:5px; font-size:13px; box-shadow:0 2px 5px rgba(0,0,0,0.2);">{data["name"]}</div>')
    ).add_to(menu_map)

# 지도 영역 자동 조절
all_lats = [d["lat"] for d in scraped_data]
all_lngs = [d["lng"] for d in scraped_data]
if all_lats and all_lngs:
    menu_map.fit_bounds([[min(all_lats), min(all_lngs)], [max(all_lats), max(all_lngs)]], padding=(50, 50))

# 지도 저장
menu_map.save("gasan_lunch_map.html")
print("오정 포함 전체 지도 생성 완료!")
