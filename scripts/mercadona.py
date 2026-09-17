#!/usr/bin/env python3
"""查詢 Mercadona 線上超市的商品、價格與商品圖（免登入的公開 API，底層用 curl）。

用法：
  python3 mercadona.py search <關鍵字西文> [--limit N] [--warehouse CODE]
  python3 mercadona.py list <關鍵字1> <關鍵字2> ...   # 一次查多項，做採買清單用
  python3 mercadona.py categories
  python3 mercadona.py category <category_id>

每筆結果含 `image`（商品實拍圖 URL），做採買清單時一定要帶上——
使用者是靠包裝照在貨架上找貨的。

倉庫代碼（warehouse）：Mercadona 多數商品全國定價，各倉價差很小，
預設 4315 已足夠當參考價，**不要為了找「正確倉庫」卡住流程**。
（郵遞區號自動對應倉庫的 API 已失效：POST /api/postal-codes/actions/change-pc/
 會回 warehouse_changed:false。要精確只能人工從 tienda.mercadona.es 的
 網路請求裡撈 products_prod_XXXX_es 的 XXXX。）
"""
import json
import subprocess
import sys

ALGOLIA_APP = "7UZJKL1DJ0"
ALGOLIA_KEY = "9d8f2e39e90df472b4f2e559a116fe17"
DEFAULT_WAREHOUSE = "4315"


def _curl(url, headers=None, data=None):
    cmd = ["curl", "-s", "-m", "20", url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["-X", "POST", "-d", data]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def search(query, limit=8, warehouse=DEFAULT_WAREHOUSE):
    url = f"https://{ALGOLIA_APP.lower()}-dsn.algolia.net/1/indexes/products_prod_{warehouse}_es/query"
    body = json.dumps({"query": query, "hitsPerPage": limit})
    data = _curl(url, headers={
        "x-algolia-application-id": ALGOLIA_APP,
        "x-algolia-api-key": ALGOLIA_KEY,
        "Content-Type": "application/json",
    }, data=body)
    out = []
    for h in data.get("hits", []):
        p = h.get("price_instructions", {})
        out.append({
            "name": h.get("display_name"),
            "packaging": h.get("packaging"),
            "price": p.get("unit_price"),          # 每件價格 (EUR)
            "size": f'{p.get("unit_size")}{p.get("size_format", "")}',
            "ref_price": f'{p.get("reference_price")} EUR/{p.get("reference_format")}',
            "image": h.get("thumbnail"),            # 商品實拍圖，採買清單一定要帶
            "url": h.get("share_url"),
        })
    return out


def batch(queries, limit=3, warehouse=DEFAULT_WAREHOUSE):
    """一次查多個關鍵字，回傳 {關鍵字: [結果...]}。做採買清單用這個，別一項一項查。"""
    return {q: search(q, limit=limit, warehouse=warehouse) for q in queries}


def categories():
    data = _curl("https://tienda.mercadona.es/api/categories/",
                 headers={"Accept": "application/json"})
    return [
        {"id": c["id"], "name": c["name"],
         "sub": [{"id": s["id"], "name": s["name"]} for s in c["categories"]]}
        for c in data["results"]
    ]


def category(cat_id):
    data = _curl(f"https://tienda.mercadona.es/api/categories/{cat_id}/",
                 headers={"Accept": "application/json"})
    out = []
    for sub in data.get("categories", []):
        for pr in sub.get("products", []):
            p = pr.get("price_instructions", {})
            out.append({
                "name": pr.get("display_name"),
                "price": p.get("unit_price"),
                "size": f'{p.get("unit_size")}{p.get("size_format", "")}',
                "ref_price": f'{p.get("reference_price")} EUR/{p.get("reference_format")}',
                "image": pr.get("thumbnail"),
            })
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    warehouse = DEFAULT_WAREHOUSE
    if "--warehouse" in args:
        i = args.index("--warehouse")
        warehouse = args[i + 1]
        del args[i:i + 2]
    limit = 8
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i:i + 2]

    if cmd == "search" and len(args) >= 2:
        result = search(" ".join(args[1:]), limit=limit, warehouse=warehouse)
    elif cmd == "list" and len(args) >= 2:
        result = batch(args[1:], limit=min(limit, 3), warehouse=warehouse)
    elif cmd == "categories":
        result = categories()
    elif cmd == "category" and len(args) >= 2:
        result = category(args[1])
    else:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
