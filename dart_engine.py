"""이전 이름 호환용 shim.

기능은 dart_client / downloader / financials / dart_viewer / xml_fix 로
옮겨 갔다. scripts/ 아래 도구와 기존 배포본이 `from dart_engine import ...`
를 그대로 쓰고 있어 이 파일이 남아 있다. 새 코드는 각 모듈을 직접 임포트할 것.
"""
from dart_client import (  # noqa: F401
    AUDIT_TYPE,
    list_disclosures,
    load_corp_list,
    search_company,
)
from dart_viewer import convert_to_html  # noqa: F401
from downloader import download_document, safe_filename  # noqa: F401
from financials import (  # noqa: F401
    calculate_financial_ratios,
    get_audit_opinion_3y,
    get_capital_changes,
    get_capital_changes_3y,
    get_dividend_info,
    get_dividend_info_3y,
    get_employee_status,
    get_equity_investments,
    get_extended_financials,
    get_extended_financials_3y,
    get_key_financials,
    get_key_financials_3y,
    get_major_shareholder,
)
from xml_fix import fix_xml  # noqa: F401
