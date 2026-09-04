import subprocess
import sys


def run_step(command):
    print()
    print("=" * 60)
    print("実行:", " ".join(command))
    print("=" * 60)

    result = subprocess.run(command)

    if result.returncode != 0:
        print()
        print("エラーが発生しました。")
        print("停止した処理:", " ".join(command))
        sys.exit(result.returncode)


def main():
    print()
    print("===== 日本経済監視AI 開始 =====")

    steps = [
        ["py", "estat.py"],
        ["py", "gdp.py"],
        ["py", "unemployment.py"],
        ["py", "real_wage.py"],
        ["py", "consumption.py"],
        ["py", "boj.py"],
        ["py", "risk.py"],
        ["py", "ai_report.py"],
        ["py", "risk_spike_alert.py"],
    ]

    for step in steps:
        run_step(step)

    print()
    print("===== 日本経済監視AI 完了 =====")


if __name__ == "__main__":
    main()