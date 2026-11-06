#!/usr/bin/env python3
"""Lấy danh sách faucet theo từng coin từ FaucetPay và ghi ra stats.json cho app.

Chạy trong GitHub Actions trước khi build. Nếu FaucetPay chặn thì giữ nguyên file cũ.
"""
import datetime
import json
import sys
import time
import urllib.request

URL = "https://faucetpay.io/app-api/faucet-list/get-faucet-list"
COINS = [
    "btc", "eth", "usdt", "xrp", "bnb", "sol", "usdc", "trx", "doge", "ada", "bch", "xmr",
    "xlm", "ton", "ltc", "zec", "dash", "pol", "pepe", "trump", "dgb", "fey", "flt",
]
PER_COIN = 40
OUT = "data/stats.json"
UA = (
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Mobile Safari/537.36"
)


def call(coin, page):
    body = json.dumps(
        {"category_id": "1", "coin": coin, "page": page, "faas_only": False}
    ).encode()
    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": UA,
            "Accept": "application/json",
            "Origin": "https://faucetpay.io",
            "Referer": "https://faucetpay.io/earn/faucets",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    faucets = {}
    by_coin = {}
    errors = 0
    for coin in COINS:
        ids = []
        page = 1
        while len(ids) < PER_COIN:
            try:
                j = call(coin, page)
            except Exception as e:  # noqa: BLE001
                print(f"LOI {coin} trang {page}: {e}", file=sys.stderr)
                errors += 1
                break
            items = j.get("list") or []
            stop = False
            for it in items:
                usd = float(it.get("week_amount_paid_usd") or 0)
                if usd <= 0:
                    stop = True  # danh sách đã xếp giảm dần, từ đây trở đi không có tiền trả
                    break
                fid = str(it["id"])
                f = faucets.setdefault(
                    fid,
                    {
                        "name": it.get("faucet_name"),
                        "url": it.get("faucet_url"),
                        "health": it.get("health", 0),
                        "ratings": float(it.get("ratings") or 0),
                        "users_paid": it.get("total_users_paid", 0),
                        "usd": {},
                    },
                )
                f["usd"][coin] = round(usd, 2)
                f["users_paid"] = max(f["users_paid"], it.get("total_users_paid", 0))
                ids.append(fid)
                if len(ids) >= PER_COIN:
                    break
            if stop or not items or page >= int(j.get("total_pages") or 1):
                break
            page += 1
            time.sleep(0.4)
        by_coin[coin] = ids
        print(f"{coin}: {len(ids)} faucet")
        time.sleep(0.4)

    if not faucets:
        print("Không lấy được dữ liệu nào, giữ nguyên file cũ.")
        return 0

    out = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "faucets": faucets,
        "by_coin": by_coin,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"Đã ghi {OUT}: {len(faucets)} faucet, {errors} lỗi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
