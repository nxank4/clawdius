import asyncio
from src.core.llm import Brain

async def main():
    brain = Brain()
    print("🧠 Clawdius is thinking...")
    response = await brain.think("Hello! Are you ready to work?")
    print(f"🤖 Clawdius says: {response}")

if __name__ == "__main__":
    asyncio.run(main())