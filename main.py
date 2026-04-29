
from agent.core import Agent

def main():
    agent = Agent()
    print("ciallo喵 天气助手已启动！输入 '退出' 结束。")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ["退出", "quit", "exit"]:
            print("再见！")
            break
        response = agent.run(user_input)
        print(f"\nAgent：{response}")

if __name__ == "__main__":
    main()