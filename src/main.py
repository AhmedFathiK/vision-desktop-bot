from bot import NotepadBot

if __name__ == "__main__":
    try:
        bot = NotepadBot()
        bot.start()
    except Exception as e:
        print(f"[FATAL ERROR] Bot crashed: {e}")
    finally:
        print("Bot execution finished.")