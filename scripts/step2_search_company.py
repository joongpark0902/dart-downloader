import xml.etree.ElementTree as ET

def search_company(keyword, xml_path="CORPCODE.xml"):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    results = []
    for item in root.findall("list"):
        name = item.findtext("corp_name", "")
        if keyword in name:
            results.append({
                "corp_code": item.findtext("corp_code", ""),
                "corp_name": name,
            })
    return results

def show(keyword):
    results = search_company(keyword)
    print(f"\n검색어: '{keyword}' → {len(results)}건")
    for r in results[:20]:
        print(f"  {r['corp_code']}  {r['corp_name']}")
    if len(results) > 20:
        print(f"  ... 외 {len(results) - 20}건")

show("SK하이닉스")
show("삼성전자")
show("카카오")
