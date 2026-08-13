"""이전 이름 호환용 shim.

GUI는 app.py 로 옮겨 갔다. 기존 배포본의 실행 런처가 이 파일을 가리키고
있어 남아 있다. 새 코드는 app.main() 을 직접 부를 것.
"""
from app import DartApp, main  # noqa: F401

if __name__ == "__main__":
    main()
