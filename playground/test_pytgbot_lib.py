from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')


app = ApplicationBuilder().token("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo").build()

app.add_handler(CommandHandler("hello", hello))

app.run_polling()


# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions-%E2%80%93-Your-first-Bot
# https://docs.python-telegram-bot.org/en/stable/