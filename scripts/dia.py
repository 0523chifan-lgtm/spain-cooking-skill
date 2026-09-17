#!/usr/bin/env python3
"""查詢 Dia 線上超市的商品、價格、折扣與商品圖（免登入的公開端點）。

用法：
  python3 dia.py search <關鍵字西文> [--limit N]
  python3 dia.py list <關鍵字1> <關鍵字2> ...   # 一次查多項，做採買清單用

跟 Mercadona 的差別：
  - Dia 會回傳 **折扣資訊**（discount_percentage、原價 strikethrough_price），
    Mercadona 的端點沒有。想找特價就查這邊。
  - Dia 自有品牌（Selección de Dia）通常比 Hacendado 再便宜一點，
    但生鮮選擇少很多，蔬果和魚類建議還是 Mercadona。

回傳欄位：
  name        貨架上的西文品名
  price       售價 (EUR)
  unit_price  每公斤/每公升單價，比價用這個
  discount    折扣百分比，0 表示沒有特價
  was         原價（有折扣時才有意義）
  image       商品實拍圖 URL，採買清單一定要帶
"""
import json
import subprocess
import sys

BASE = "https://www.dia.es/api/v1/search-back/search/reduced"
IMG_BASE = "https://www.dia.es"


def _curl(url):
    out = subprocess.run(
        ["curl", "-s", "-m", "20", url, "-H", "Accept: application/json"],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def search(query, limit=8):
    q = query.replace(" ", "%20")
    data = _curl(f"{BASE}?q={q}&page=0")
    out = []
    for it in data.get("search_items", [])[:limit]:
        pr = it.get("prices", {}) or {}
        img = it.get("image") or ""
        out.append({
            "name": it.get("display_name"),
            "price": pr.get("price"),
            "unit_price": f'{pr.get("price_per_unit")} EUR/{pr.get("measure_unit")}',
            "discount": pr.get("discount_percentage", 0),
            "was": pr.get("strikethrough_price"),
            "image": (IMG_BASE + img) if img else None,
        })
    return out


def batch(queries, limit=3):
    """一次查多個關鍵字。做採買清單用這個，別一項一項查。"""
    return {q: search(q, limit=limit) for q in queries}


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    limit = 8
    if "--limit" in args:
        i = args.index("--limit")
        limit = int(args[i + 1])
        del args[i:i + 2]

    if cmd == "search" and len(args) >= 2:
        result = search(" ".join(args[1:]), limit=limit)
    elif cmd == "list" and len(args) >= 2:
        result = batch(args[1:], limit=min(limit, 3))
    else:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
