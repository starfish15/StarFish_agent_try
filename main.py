
from agent.core import Agent

def main():
    agent = Agent()
    print("ciallo喵 星辰猫猫已启动！结束请输入 '退出' 喵。")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ["退出", "quit", "exit"]:
            print("主人再见喵！")
            break
        response = agent.run(user_input)
        print(f"\nAgent：{response}")

if __name__ == "__main__":
    main()