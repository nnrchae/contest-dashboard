# ---------------------------------------------------------
# 3. Gemini AI 분석 및 포트폴리오 가치(관련성) 최우선 정렬
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

    # 과부하 대비 재시도(Retry) 로직
    max_retries = 3
    response = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1),
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait_seconds = 5 * (attempt + 1)
                print(f"  ⚠️ API 오류 발생. {wait_seconds}초 후 재시도합니다... ({attempt + 1}/{max_retries})")
                time.sleep(wait_seconds)
            else:
                print("  ❌ Gemini API 재시도 횟수를 초과했습니다.")
                raise e

    clean_text = re.sub(r'```json\s*|\s*```', '', response.text).strip()
    parsed_data = json.loads(clean_text)

    # ---------------------------------------------------------
    # 마감일 영향 없이 오직 '포트폴리오 가치 점수(관련성)'가 높은 순서대로만 정렬
    # ---------------------------------------------------------
    sorted_data = sorted(
        parsed_data, 
        key=lambda x: x.get("portfolio_value_score", 3), 
        reverse=True
    )
    
    return sorted_data
