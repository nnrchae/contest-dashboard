import json
import re
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. Gemini Client 및 헤더 설정
# ---------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6LjkxF6Z4j0xAhyquj5ASu690ME094iRNmcv7JD3M1PYw") 
client = genai.Client(api_key=GEMINI_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wevity.com/"
}

# ---------------------------------------------------------
# 날짜 파싱 및 D-Day 정확 계산 함수 (수정 완료)
# ---------------------------------------------------------
def calculate_dday_from_text(text):
    """
    텍스트 내에서 YYYY-MM-DD 또는 YYYY.MM.DD 형식의 날짜들을 모두 찾아,
    시작일~종료일 패턴 중 '마감일(가장 마지막 날짜)'을 기준으로 D-Day를 정확히 계산합니다.
    """
    if not text:
        return "접수중"
    
    # D-33, D-5 등의 텍스트가 직접 존재하는 경우 최우선 활용
    dday_match = re.search(r'D-(\d+)', text, re.IGNORECASE)
    
    # 2026-10-01, 2026.10.01 등 YYYY-MM-DD 형태 추출
    dates = re.findall(r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})', text)
    
    if not dates:
        if dday_match:
            days_left = int(dday_match.group(1))
            return f"D-{days_left}"
        return "접수중"
    
    # 여러 날짜(시작일 ~ 종료일) 중 가장 '마지막' 날짜를 마감일로 지정
    year, month, day = map(int, dates[-1])
    
    try:
        end_date = datetime(year, month, day).date()
        today = datetime.now().date()
        diff = (end_date - today).days

        if diff > 0:
            return f"D-{diff} (~{end_date.strftime('%m/%d')})"
        elif diff == 0:
            return f"D-Day (오늘마감)"
        else:
            return "접수마감"
    except Exception:
        return "접수중"

def fetch_wevity_detail_info(detail_url):
    """위비티 상세 페이지에서 정확한 접수 기간 및 D-Day를 추출합니다."""
    try:
        res = requests.get(detail_url, headers=HEADERS, timeout=5)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 위비티 D-day 표시 태그 또는 접수기간 영역 우선 탐색
            dday_elem = soup.select_one('.dday, .day-box, .cd-info')
            text_content = soup.text if not dday_elem else dday_elem.text
            
            # '접수기간 2026-10-01 ~ 2026-11-02 D-33' 전체 텍스트 전달
            return calculate_dday_from_text(text_content)
    except Exception as e:
        print(f"    ⚠️ 위비티 상세페이지 파싱 실패 ({detail_url}): {e}")
    return "접수중"

# ---------------------------------------------------------
# 2. 크롤링 함수들
# ---------------------------------------------------------
def fetch_wevity_contests():
    url = "https://www.wevity.com/?c=find&s=1&cidx=14"
    print("🌐 [1/3] 위비티(Wevity) 최신 디자인 공모전 크롤링 중 (마감일 정밀 분석)...")
    extracted_items = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            contest_items = soup.select('ul.list > li, div.list > div, .day-list li')
            for item in contest_items:
                link_tag = item.select_one('.tit a') or item.select_one('a[href*="c=find&s=1"]')
                if not link_tag: continue
                title = link_tag.text.strip()
                if not title: continue
                href = link_tag.get('href', '')
                link = f"https://www.wevity.com/{href}" if href.startswith('?') else href
                organizer_tag = item.select_one('.organ') or item.select_one('.sub-tit')
                organizer = organizer_tag.text.strip() if organizer_tag else "주최사 정보 참조"
                
                # 상세 페이지에 들어가 마감일/D-Day 계산
                exact_dday = fetch_wevity_detail_info(link)
                
                extracted_items.append({
                    "source": "위비티", 
                    "title": title, 
                    "organizer": organizer, 
                    "dday": exact_dday, 
                    "link": link
                })
    except Exception as e:
        print(f"  ⚠️ 위비티 예외: {e}")
    print(f"  └ 위비티에서 {len(extracted_items)}개 수집 및 마감일 검증 완료.")
    return extracted_items

def fetch_allforyoung_contests():
    url = "https://allforyoung.com/api/v1/posts?category=1&subCategory=15&page=1&size=15"
    print("🌐 [2/3] 요즘것들(AllForYoung) 최신 디자인 공모전 크롤링 중...")
    extracted_items = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", []) or data.get("posts", []) or []
            for p in posts:
                title = p.get("title", "").strip()
                post_id = p.get("id") or p.get("postId")
                organizer_info = p.get("organizer", {})
                organizer = organizer_info.get("name") if isinstance(organizer_info, dict) else "요즘것들 등록 주최사"
                
                finish_date = p.get("finishDate", "") or p.get("endDate", "")
                dday_text = p.get("dDayText", "")
                calculated_dday = calculate_dday_from_text(finish_date) if finish_date else (dday_text or "접수중")

                if title and post_id:
                    extracted_items.append({
                        "source": "요즘것들", 
                        "title": title, 
                        "organizer": organizer, 
                        "dday": calculated_dday, 
                        "link": f"https://allforyoung.com/posts/{post_id}"
                    })
    except Exception as e:
        print(f"  ⚠️ 요즘것들 예외: {e}")
    print(f"  └ 요즘것들에서 {len(extracted_items)}개 수집 완료.")
    return extracted_items

def fetch_campuspick_contests():
    url = "https://www.campuspick.com/contest"
    print("🌐 [3/3] 캠퍼스픽(CampusPick) 최신 공모전 크롤링 중...")
    extracted_items = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('.item, a[href*="/contest/view"]')
            for item in items:
                title_elem = item.select_one('.title, h2, h3')
                title = title_elem.text.strip() if title_elem else item.text.strip()
                if not title or len(title) < 4: continue
                
                href = item.get('href', '')
                full_link = f"https://www.campuspick.com{href}" if href.startswith('/') else href
                organizer_elem = item.select_one('.company, .organ')
                organizer = organizer_elem.text.strip() if organizer_elem else "주최사 참조"
                
                dday_elem = item.select_one('.dday, .badge, .d-day')
                dday_str = dday_elem.text.strip() if dday_elem else calculate_dday_from_text(item.text)

                extracted_items.append({
                    "source": "캠퍼스픽", 
                    "title": title, 
                    "organizer": organizer, 
                    "dday": dday_str, 
                    "link": full_link
                })
    except Exception as e:
        print(f"  ⚠️ 캠퍼스픽 예외: {e}")
    seen = set()
    unique_items = []
    for item in extracted_items:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique_items.append(item)
    print(f"  └ 캠퍼스픽에서 {len(unique_items)}개 수집 완료.")
    return unique_items

# ---------------------------------------------------------
# 3. Gemini AI 분석 (dday 원본 유지 강제화)
# ---------------------------------------------------------
def parse_contest_data(raw_data_list):
    raw_data_json = json.dumps(raw_data_list, ensure_ascii=False)
    prompt = f"""
    다음은 여러 공모전 웹사이트에서 수집한 최신 디자인 공모전 데이터입니다:
    {raw_data_json}

    이 정보들을 바탕으로 포트폴리오 가치를 분석하고 JSON 배열로 응답해 주세요.
    
    [엄격 지침]
    1. 'link' 필드 값은 절대로 변경하거나 생략하지 마세요.
    2. 입력 데이터의 'dday' 값을 절대로 스스로 판단하거나 수정하지 말고, 'deadline' 필드에 그대로 복사하세요.

    [
      {{
        "id": 1,
        "title": "공모전 제목",
        "organizer": "주최 기관명",
        "organizer_type": "대기업 / 지자체/공공기관 / 중소기업 / 기타 중 하나",
        "deadline": "입력 데이터의 dday 필드값 그대로 유지",
        "link": "입력 데이터 원본 상세 링크 주소 그대로 포함",
        "portfolio_value_score": 1~5 정수,
        "portfolio_reason": "포트폴리오 가치 분석 (1-2문장)",
        "summary": "공모전 개요 한 줄 요약"
      }}
    ]
    다른 설명 없이 순수 JSON 배열만 출력해 주세요.
    """
    print(f"\n🤖 Gemini AI가 수집된 총 {len(raw_data_list)}개의 공모전 데이터를 분석 중...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1),
    )
    clean_text = re.sub(r'```json\s*|\s*```', '', response.text).strip()
    return json.loads(clean_text)

# ---------------------------------------------------------
# 4. 단일 HTML 파일 생성 함수
# ---------------------------------------------------------
def generate_html_dashboard(parsed_data):
    json_str = json.dumps(parsed_data, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>최신 디자인 공모전 대시보드</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #FAF8F5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #2C2C2C;
            padding: 40px 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 40px; }}
        header h1 {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; color: #111827; }}
        header p {{ color: #6B7280; font-size: 16px; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 24px;
        }}
        .card {{
            text-decoration: none;
            color: inherit;
            background-color: #FFFFFF;
            border: 1px solid #E8E2D9;
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}
        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
        }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
        .badge {{
            background-color: #EEF2FF;
            color: #4338CA;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .dday {{ color: #EF4444; font-size: 13px; font-weight: 700; }}
        .title {{ font-size: 18px; font-weight: bold; margin-bottom: 8px; line-height: 1.4; color: #1F2937; }}
        .organizer {{ color: #6B7280; font-size: 14px; margin-bottom: 16px; }}
        .score-box {{
            background-color: #F9FAFB;
            border: 1px solid #F3F4F6;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 14px;
        }}
        .score-title {{ font-weight: bold; color: #111827; font-size: 14px; margin-bottom: 4px; }}
        .score-reason {{ font-size: 13px; color: #4B5563; line-height: 1.4; }}
        .summary {{ font-size: 13px; color: #374151; line-height: 1.4; }}
        .card-footer {{
            margin-top: 20px;
            padding-top: 12px;
            border-top: 1px solid #F3F4F6;
            text-align: right;
            font-size: 13px;
            color: #2563EB;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎨 최신 디자인 공모전 대시보드</h1>
            <p>AI가 분석한 포트폴리오 가치 기반 추천 공모전 목록입니다.</p>
        </header>
        <div class="grid" id="contestGrid"></div>
    </div>

    <script>
        const contests = {json_str};
        const grid = document.getElementById('contestGrid');

        contests.forEach(item => {{
            const card = document.createElement('a');
            card.className = 'card';
            card.href = item.link && item.link !== '#' ? item.link : '#';
            card.target = '_blank';
            card.rel = 'noopener noreferrer';

            card.innerHTML = `
                <div>
                    <div class="card-header">
                        <span class="badge">${{item.organizer_type || '공모전'}}</span>
                        <span class="dday">${{item.deadline || item.dday || '접수중'}}</span>
                    </div>
                    <div class="title">${{item.title}}</div>
                    <div class="organizer">🏢 ${{item.organizer}}</div>
                    
                    ${{item.portfolio_value_score ? `
                    <div class="score-box">
                        <div class="score-title">⭐ 포트폴리오 가치: ${{item.portfolio_value_score}} / 5</div>
                        <div class="score-reason">${{item.portfolio_reason || ''}}</div>
                    </div>` : ''}}

                    ${{item.summary ? `<div class="summary">💡 ${{item.summary}}</div>` : ''}}
                </div>
                <div class="card-footer">상세내용 및 지원하기 ↗</div>
            `;
            grid.appendChild(card);
        }});
    </script>
</body>
</html>
"""
    output_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n🎉 성공적으로 'index.html' 단일 대시보드 파일이 생성되었습니다!")
    return output_path

# ---------------------------------------------------------
# 5. 메인 실행
# ---------------------------------------------------------
if __name__ == "__main__":
    wevity = fetch_wevity_contests()
    afy = fetch_allforyoung_contests()
    cp = fetch_campuspick_contests()

    all_items = wevity + afy + cp
    print(f"\n📊 총 {len(all_items)}개의 공모전을 수집했습니다.")

    if all_items:
        parsed_list = parse_contest_data(all_items)
        html_file = generate_html_dashboard(parsed_list)