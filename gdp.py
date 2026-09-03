import os
import requests
from dotenv import load_dotenv
from database import save_economic_data

load_dotenv()

ESTAT_APP_ID = os.getenv("ESTAT_APP_ID")

STATS_DATA_ID = "0003113612"


def get_gdp():

    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

    params = {
        "appId": ESTAT_APP_ID,
        "statsDataId": STATS_DATA_ID,

        "cdTab": "12",
        "cdCat01": "11",

        "metaGetFlg": "Y",
        "cntGetFlg": "N",
        "explanationGetFlg": "Y",
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    print("HTTPステータス:", response.status_code)

    data = response.json()

    result = data["GET_STATS_DATA"]["RESULT"]

    print("APIステータス:", result["STATUS"])

    if result["STATUS"] != 0:
        print("取得失敗")
        print(result.get("ERROR_MSG"))
        return

    values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]

    print()
    print("===== 実質GDP・前年同期比 =====")

    count = 0

    for value in values:

        if (
            value.get("@tab") == "12"
            and value.get("@cat01") == "11"
        ):

            time = value.get("@time")
            number = value.get("$")

            if not time or number in (None, ""):
                continue

            # 例：
            # 2026000103
            # ↓
            # 2026年1～3月期

            year = time[:4]
            start_month = time[6:8]
            end_month = time[8:10]

            quarter = f"{year}Q"

            if start_month == "01":
                quarter += "1"
            elif start_month == "04":
                quarter += "2"
            elif start_month == "07":
                quarter += "3"
            elif start_month == "10":
                quarter += "4"
            else:
                continue

            date = quarter

            print(
                "期間:", date,
                "| GDP前年同期比:", number, "%"
            )

            save_economic_data(
                source="e-Stat",
                indicator="GDP_実質_前年同期比",
                date=date,
                value=float(number),
                unit="%"
            )

            count += 1

    print()
    print("保存件数:", count)


if __name__ == "__main__":
    get_gdp()