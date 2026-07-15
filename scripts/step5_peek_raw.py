import re
import xml.etree.ElementTree as ET

FILE = r"downloads\SK하이닉스\사업보고서_2024\20250319000665.xml"
FIXED = r"downloads\SK하이닉스\사업보고서_2024\20250319000665_fixed.xml"

# 1. 인코딩 확인
text = None
for enc in ["utf-8", "euc-kr"]:
    try:
        with open(FILE, encoding=enc) as f:
            text = f.read()
        print(f"인코딩: {enc} 성공")
        break
    except UnicodeDecodeError:
        print(f"인코딩: {enc} 실패")

if text is None:
    print("두 인코딩 모두 실패 — 종료")
    exit(1)

# 2. 보정 함수
# 전략: 문자를 하나씩 순회하며 컨텍스트(태그 안/밖, 속성값 안/밖)를 추적한다.
#   - 텍스트 구간: 날것 & → &amp;, 비태그 < → &lt;
#   - 속성값 구간: 날것 & → &amp;  (< 는 원래 금지지만 실제론 안 나옴)
#   - 태그 구조 자체(태그명·속성명·따옴표·/>·>)는 그대로 유지

VALID_ENTITY = re.compile(
    r"&(?:\#\d+|\#x[\da-fA-F]+|amp|lt|gt|quot|apos);"
)
TAG_START = re.compile(r"</?[A-Za-z_!][\w:.-]*")

def fix_xml(s):
    result = []
    i = 0
    n = len(s)

    while i < n:
        c = s[i]

        # ── 태그/특수 구조 시작 ─────────────────────────────────────
        if c == "<":
            # CDATA
            if s[i:i+9] == "<![CDATA[":
                end = s.find("]]>", i + 9)
                if end != -1:
                    result.append(s[i:end + 3])
                    i = end + 3
                    continue

            # 주석
            if s[i:i+4] == "<!--":
                end = s.find("-->", i + 4)
                if end != -1:
                    result.append(s[i:end + 3])
                    i = end + 3
                    continue

            # 처리 지시
            if s[i:i+2] == "<?":
                end = s.find("?>", i + 2)
                if end != -1:
                    result.append(s[i:end + 2])
                    i = end + 2
                    continue

            # 유효한 태그 시작인지 확인 (<tagname 또는 </tagname)
            m = TAG_START.match(s, i)
            if m:
                # 태그 내부를 속성값까지 파싱하며 & 보정
                i, tag_str = parse_tag(s, i, n)
                result.append(tag_str)
                continue

            # 유효하지 않은 < → 이스케이프
            result.append("&lt;")
            i += 1

        # ── 텍스트 구간의 & ───────────────────────────────────────
        elif c == "&":
            m = VALID_ENTITY.match(s, i)
            if m:
                result.append(m.group())
                i = m.end()
            else:
                result.append("&amp;")
                i += 1

        else:
            result.append(c)
            i += 1

    return "".join(result)


def parse_tag(s, i, n):
    """태그 전체를 읽으면서 속성값 안의 & 만 보정한다. (i, fixed_str) 반환"""
    result = []
    in_quote = None  # '"' 또는 "'"

    while i < n:
        c = s[i]

        if in_quote:
            if c == in_quote:
                result.append(c)
                in_quote = None
                i += 1
            elif c == "&":
                m = VALID_ENTITY.match(s, i)
                if m:
                    result.append(m.group())
                    i = m.end()
                else:
                    result.append("&amp;")
                    i += 1
            else:
                result.append(c)
                i += 1
        else:
            if c in ('"', "'"):
                in_quote = c
                result.append(c)
                i += 1
            elif c == ">":
                result.append(">")
                i += 1
                break
            else:
                result.append(c)
                i += 1

    return i, "".join(result)


print("보정 중...")
fixed = fix_xml(text)

with open(FIXED, "w", encoding="utf-8") as f:
    f.write(fixed)
print(f"저장 완료: {FIXED}")

# 3. 파싱 검증
print("\nXML 파싱 검증...")
try:
    ET.parse(FIXED)
    print("파싱 성공 — 에러 없음")
except ET.ParseError as e:
    print(f"파싱 실패: {e}")
    lineno = e.position[0]
    lines = fixed.splitlines()
    start = max(0, lineno - 4)
    end = min(len(lines), lineno + 3)
    print(f"\n--- 문제 구간 ({start+1}~{end}번째 줄) ---")
    for i in range(start, end):
        marker = " <<<" if i == lineno - 1 else ""
        print(f"{i+1:7}: {lines[i]}{marker}")
