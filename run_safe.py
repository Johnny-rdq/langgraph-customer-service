import os
import sys
import subprocess


def main():
    # 💥 降维打击：在 Python 甚至还没加载主程序前，强行将底层内核锁死在 UTF-8
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"

    print("====== 🛡️ 已开启全局 UTF-8 绝对防御模式 ======")
    print("正在拉起主程序，彻底免疫 Emoji 乱码和崩溃...")

    # 用独立子进程拉起你的主程序，子进程会完美继承 UTF-8 基因，无视 PyCharm 和 Windows 限制
    subprocess.run([sys.executable, "app/main.py"])


if __name__ == "__main__":
    main()