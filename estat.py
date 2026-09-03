import os
import requests
from dotenv import load_dotenv
from database import save_economic_data

load_dotenv()

ESTAT_APP_ID = os.getenv("ESTAT_APP_ID")
STATS_DATA_ID = "0003427113"


def get_cpi():

    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

    params = {
        "appId": ESTAT_APP_ID,
        "statsDataId": STATS_DATA_ID,

        # 前年同月比
        "cdTab": "3",

        # 総合
        "cdCat01": "0001",

        # 全国
        "cdArea": "00000",

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
    print("===== CPI 全国・総合・前年同月比 =====")

    count = 0

    for value in values:

        if (
            value.get("@tab") == "3"
            and value.get("@cat01") == "0001"
            and value.get("@area") == "00000"
        ):

            time = value.get("@time")
            number = value.get("$")

            year = time[:4]
            month = time[-2:]

            # 年平均は除外
            if month == "00":
                continue

            date = f"{year}-{month}"

            print(
                "日付:", date,
                "| 前年同月比:", number, "%"
            )

            save_economic_data(
                source="e-Stat",
                indicator="CPI_総合_前年同月比",
                date=date,
                value=float(number),
                unit="%"
            )

            count += 1

    print()
    print("保存件数:", count)


if __name__ == "__main__":
    get_cpi()