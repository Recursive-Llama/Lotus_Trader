# Telegram Signal Notifications Setup Guide

This guide will help you set up Telegram notifications for your Lotus Trader buy/sell signals.

## 🎯 What You'll Get

Your private Telegram group will receive beautifully formatted notifications like:

**Buy Signal:**
```
🟢 LOTUS BUY SIGNAL 🟢

Token: PEPE (link to token page)
Amount: 0.1000 ETH
Entry Price: $0.00000123
Allocation: 2.5% of portfolio
Transaction: View on Explorer (link to transaction)
Time: 14:30 UTC
Source: Tweet (link to source tweet)

🚀 Position opened successfully!
```

**Sell Signal:**
```
🔴 LOTUS SELL SIGNAL 🔴

Token: PEPE (link to token page)
Amount Sold: 1,000,000 tokens
Sell Price: $0.00000246
Transaction: View on Explorer (link to transaction)
Profit: 📈 +100.0%
P&L: 💰 +$123.45
Total Position P&L: +$123.45
Time: 15:45 UTC
Source: Tweet (link to source tweet)

🎉 MASSIVE WIN! 🎉
```

## 📋 Prerequisites

1. **Telegram Bot Token**: You need to create a Telegram bot
2. **Private Group**: A Telegram group where you're the owner
3. **Environment Variables**: Set up your bot credentials

## 🤖 Step 1: Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Start a chat with BotFather
3. Send `/newbot` command
4. Choose a name for your bot (e.g., "Lotus Trader Signals")
5. Choose a username (e.g., "lotus_trader_signals_bot")
6. **Save the bot token** - you'll need this for `TELEGRAM_BOT_TOKEN`

## 👥 Step 2: Create a Private Group

1. Create a new Telegram group
2. Add your bot to the group as an administrator
3. Give the bot permission to send messages
4. **Get the group ID**:
   - Add `@userinfobot` to your group
   - It will show the group ID (looks like `-1001234567890`)
   - Remove `@userinfobot` after getting the ID
   - Use this ID for `TELEGRAM_CHANNEL_ID`

## ⚙️ Step 3: Configure Environment Variables

Add these to your `.env` file:

```bash
# Telegram Signal Notifications
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHANNEL_ID=-1001234567890  # Your group ID
```

**Alternative**: You can also use `@your_group_username` if your group has a username.

## 🧪 Step 4: Test the Setup

Run the test script to verify everything works:

```bash
python test_telegram_signals.py
```

This will:
1. Test the connection to your Telegram channel
2. Send sample buy/sell notifications
3. Show you exactly what the messages will look like

## 🚀 Step 5: Enable in Production

The system is already integrated! Once you set the environment variables, your trading system will automatically send notifications for:

- ✅ **Buy signals** - When positions are opened
- ✅ **Sell signals** - When positions are closed (with profit tracking)
- ✅ **Transaction links** - Direct links to blockchain explorers
- ✅ **Source tweets** - Links back to the original tweet that triggered the trade
- ✅ **Profit tracking** - Real-time P&L information

## 🔧 Configuration Options

The system uses your existing Telegram infrastructure:
- **API ID**: `21826741` (your existing ID)
- **API Hash**: Your existing hash
- **Session File**: `src/config/telegram_session.txt` (your existing session)

## 📱 Message Features

### Buy Signals Include:
- Token name and contract link
- Amount spent in native currency (ETH, BNB, SOL)
- Entry price per token
- Portfolio allocation percentage
- Transaction hash with explorer link
- Source tweet link (when available)
- Timestamp

### Sell Signals Include:
- Token name and contract link
- Amount of tokens sold
- Sell price per token
- Transaction hash with explorer link
- **Profit percentage** for this sell
- **P&L in USD** for this sell
- **Total position P&L**
- Source tweet link (when available)
- Timestamp
- **Celebration emojis** based on profit level

## 🎨 Message Formatting

Messages use rich Markdown formatting with:
- **Bold text** for important information
- 🔗 **Clickable links** to transactions and tokens
- 📊 **Emojis** for visual appeal
- 📈 **Profit indicators** with appropriate celebrations

## 🔒 Security Notes

- Your bot token is sensitive - keep it secure
- The bot only sends messages, it doesn't read them
- All notifications are sent to your private group only
- No trading data is stored in Telegram

## 🐛 Troubleshooting

### "Failed to connect to Telegram channel"
- Check your bot token is correct
- Ensure the bot is added to your group as admin
- Verify the group ID is correct (starts with `-100`)

### "Bot not sending messages"
- Make sure the bot has "Send Messages" permission
- Check that the bot is still in the group
- Verify environment variables are loaded

### "Messages not formatted correctly"
- This is normal - Telegram may not support all Markdown features
- The important information will still be visible

## 📞 Support

If you encounter issues:
1. Run the test script first: `python test_telegram_signals.py`
2. Check the logs for error messages
3. Verify your bot permissions in the Telegram group
4. Ensure environment variables are properly set

## 🎉 You're All Set!

Once configured, your Lotus Trader will automatically send beautiful, informative notifications to your private Telegram group for every trade. This gives you real-time visibility into your trading activity with all the context you need!

---

**Happy Trading! 🚀**
