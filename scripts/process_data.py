#!/usr/bin/env python3
"""
process_data.py - 원본 CSV를 Jekyll 페이지 생성용 JSON으로 가공

입력: _rawdata/merchants_raw.csv
출력:
  _rawdata/markets.json   - 시장/상점가별 그룹(시장 페이지 + 가맹점 개별 페이지 생성용, 가맹점마다 slug 포함)
  search_index.json       - 전체 가맹점 경량 인덱스(루트, 클라이언트 검색용)
  top_markets.json        - 가맹점 많은 시장 TOP 12(루트, 홈페이지용)

사용법:
  python scripts/process_data.py [--limit N]   # --limit은 로컬 미리보기용 샘플 빌드
"""
import csv, json, re, hashlib, sys, argparse
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
RAW_CSV = ROOT / "_rawdata" / "merchants_raw.csv"
MARKETS_OUT = ROOT / "_rawdata" / "markets.json"
SEARCH_INDEX_OUT = ROOT / "search_index.json"
TOP_MARKETS_OUT = ROOT / "top_markets.json"


def make_slug(name: str, salt: str = "") -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", name).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    h = hashlib.md5(f"{name}|{salt}".encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{h}" if slug else h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="로컬 미리보기용: 앞에서 N개 시장만 처리")
    args = ap.parse_args()

    with open(RAW_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    by_market = defaultdict(list)
    skipped_no_market = 0
    for r in rows:
        market = (r.get("소속 시장명(또는 상점가)") or "").strip()
        name = (r.get("가맹점명") or "").strip()
        if not market or not name:
            skipped_no_market += 1
            continue
        by_market[market].append({
            # 필드명 주의: "name"은 Jekyll Page의 내장 속성(출력 파일명)과 충돌한다
            # (wooaedu에서 동일 버그 확인됨, 2026-08-28) - "storeName"으로 명명
            "storeName": name,
            "items": (r.get("취급품목") or "").strip(),
            "paper": (r.get("지류형 가맹 여부") or "").strip() == "Y",
            "digital": (r.get("디지털형 가맹 여부") or "").strip() == "Y",
            "year": (r.get("등록년도") or "").strip(),
        })

    # 시장/상점가 하나에 소재지가 여러 값으로 섞여 들어오는 경우가 있어(오탈자 등)
    # 최빈값을 대표 소재지로 채택
    market_sido = {}
    for r in rows:
        market = (r.get("소속 시장명(또는 상점가)") or "").strip()
        sido = (r.get("소재지") or "").strip()
        if market and sido:
            market_sido.setdefault(market, Counter())[sido] += 1

    markets = []
    for market, merchants in by_market.items():
        sido = market_sido[market].most_common(1)[0][0] if market in market_sido else ""
        market_slug = make_slug(market)
        # 가맹점마다 고유 슬러그 부여 (이름 중복 12,199건 있어 이름만으론 unique 불가 -
        # 시장 슬러그 + 이 시장 내 순번으로 salt)
        for idx, merchant in enumerate(merchants):
            merchant["slug"] = make_slug(merchant["storeName"], f"{market_slug}-{idx}")
            merchant["marketName"] = market
            merchant["marketSlug"] = market_slug
            merchant["sido"] = sido

        markets.append({
            "marketName": market,
            "slug": market_slug,
            "sido": sido,
            "merchantCount": len(merchants),
            "paperCount": sum(1 for m in merchants if m["paper"]),
            "digitalCount": sum(1 for m in merchants if m["digital"]),
            "merchants": merchants,
        })

    markets.sort(key=lambda m: -m["merchantCount"])

    if args.limit:
        markets = markets[:args.limit]
        print(f"[--limit] 상위 {len(markets)}개 시장만 처리 (로컬 미리보기 모드)")

    MARKETS_OUT.parent.mkdir(parents=True, exist_ok=True)
    MARKETS_OUT.write_text(json.dumps(markets, ensure_ascii=False, indent=2), encoding="utf-8")
    total_merchants = sum(m["merchantCount"] for m in markets)
    print(f"시장/상점가 {len(markets)}개 / 가맹점 {total_merchants}개 저장 → {MARKETS_OUT}")
    print(f"  (소속 시장명 없어서 제외: {skipped_no_market}건)")

    sido_counts = Counter(m["sido"] for m in markets)
    print("\n시도별 시장/상점가 수:")
    for sido, cnt in sido_counts.most_common(20):
        print(f"  {sido}: {cnt}개")

    # 전역 검색용 경량 인덱스 (필드 최소화 - 15만 건 규모라 용량 관리 필요)
    # 's'(merchant slug)로 이제 가맹점 자기 자신의 개별 페이지로 바로 연결
    index = []
    for m in markets:
        for merchant in m["merchants"]:
            index.append({
                "n": merchant["storeName"],
                "mk": m["marketName"],
                "s": merchant["slug"],
                "sido": m["sido"],
                "i": merchant["items"],
                "p": merchant["paper"],
                "d": merchant["digital"],
            })
    SEARCH_INDEX_OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = SEARCH_INDEX_OUT.stat().st_size / 1024 / 1024
    print(f"\n전역 검색 인덱스 {len(index)}건 저장 → {SEARCH_INDEX_OUT} ({size_mb:.1f}MB)")

    top_markets = sorted(markets, key=lambda m: -m["merchantCount"])[:12]
    TOP_MARKETS_OUT.write_text(json.dumps([
        {"marketName": m["marketName"], "slug": m["slug"], "sido": m["sido"], "merchantCount": m["merchantCount"]}
        for m in top_markets
    ], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"TOP 12 시장 저장 → {TOP_MARKETS_OUT}")


if __name__ == "__main__":
    main()
