import os
import requests
from dotenv import load_dotenv
from database import save_economic_data

load_dotenv()

ESTAT_APP_ID = os.getenv("ESTAT_APP_ID")

STATS_DATA_ID = "0003005865"


def get_unemployment():

    url = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

    params = {
        "appId": ESTAT_APP_ID,
        "statsDataId": STATS_DATA_ID,

        "cdTab": "02",
        "cdCat01": "000",
        "cdCat02": "08",
        "cdCat03": "0",
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
    print("===== 完全失業率 =====")

    count = 0

    for value in values:

        time = value.get("@time")
        number = value.get("$")

        if not time or number in (None, ""):
            continue

        try:
            number = float(number)
        except ValueError:
            print(
                "スキップ:", time,
                "| 数値ではないデータ:", number
            )
            continue

        year = time[:4]
        month = time[6:8]

        date = f"{year}-{month}"

        print(
            "日付:", date,
            "| 完全失業率:", number, "%"
        )

        save_economic_data(
            source="e-Stat",
            indicator="完全失業率",
            date=date,
            value=number,
            unit="%"
        )

        count += 1

    print()
    print("保存件数:", count)


if __name__ == "__main__":
    get_unemployment()