import subprocess
import os
import sys
import webbrowser
import time

# 현재 디렉토리 및 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_APP_DIR = os.path.join(BASE_DIR, "web-app")
DESIGN_SCRIPT = os.path.join(BASE_DIR, "Design.py")

def main():
    print("🚀 [1/3] 공모전 데이터 수집 및 AI 분석 시작...")
    # 1. Design.py 실행
    result = subprocess.run([sys.executable, DESIGN_SCRIPT], check=False)
    
    if result.returncode != 0:
        print("❌ 데이터 수집 및 분석 중 오류가 발생했습니다.")
        return

    print("\n🌐 [2/3] 웹 대시보드 서버(Next.js) 실행 중...")
    
    # 2. 브라우저 자동 열기 (2초 후 접속)
    def open_browser():
        time.sleep(2.5)
        webbrowser.open("http://localhost:3000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # 3. web-app 폴더에서 npm run dev 실행
    try:
        subprocess.run("npm run dev", shell=True, cwd=WEB_APP_DIR)
    except KeyboardInterrupt:
        print("\n👋 웹 서버가 종료되었습니다.")

if __name__ == "__main__":
    main()