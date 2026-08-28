#!/usr/bin/env python3
"""
fetch_merchants.py - 전국 온누리상품권 가맹점 현황 수집 (소상공인시장진흥공단)

이 데이터셋은 "표준데이터셋"이 아니라 "파일데이터"라 www.data.go.kr/download/standard.json
우회법을 못 쓴다. 대신 실제 다운로드 버튼(fn_fileDataDown)이 호출하는 최종 다운로드
엔드포인트(/cmm/cmm/fileDownload.do?atchFileId=...)를 브라우저 네트워크탭에서 직접
캡처해 사용한다. atchFileId는 데이터셋이 개정되면 바뀔 수 있으므로, 매번
data.go.kr 상세페이지에서 최신 atchFileId를 갱신해야 할 수 있다
(2026-08-28 기준: FILE_000000003235520).

사용법:
  python scripts/fetch_merchants.py
"""
import sys, csv, json
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

ATCH_FILE_ID = "FILE_000000003235520"
DOWNLOAD_URL = f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={ATCH_FILE_ID}&fileDetailSn=1"
RAW_CSV = Path(__file__).parent.parent / "_rawdata" / "merchants_raw.csv"


def main():
    print("=== 전국 온누리상품권 가맹점 현황 다운로드 ===")
    resp = requests.get(DOWNLOAD_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    resp.raise_for_status()
    if "csv" not in (resp.headers.get("Content-Disposition") or "").lower():
        raise SystemExit(
            "다운로드 응답이 CSV가 아닙니다 - atchFileId가 만료되었을 수 있습니다. "
            "data.go.kr/data/3060079/fileData.do 에서 다운로드 버튼 네트워크 요청을 다시 캡처하세요."
        )

    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    RAW_CSV.write_bytes(resp.content)
    print(f"다운로드 완료: {RAW_CSV} ({len(resp.content):,} bytes)")

    with open(RAW_CSV, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if RAW_CSV.with_suffix(".prevcount").exists():
        prev = int(RAW_CSV.with_suffix(".prevcount").read_text())
        if len(rows) < prev * 0.5:
            raise SystemExit(
                f"수집 건수({len(rows)}건)가 이전 실행({prev}건)의 절반 미만입니다. "
                "오류로 판단하여 중단합니다."
            )
    RAW_CSV.with_suffix(".prevcount").write_text(str(len(rows)))

    print(f"총 {len(rows):,}개 가맹점 확인")


if __name__ == "__main__":
    main()
