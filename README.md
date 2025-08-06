# Discord Weekly Report Bot

This repository contains a Python script for a Discord bot that checks a designated
channel each day for new messages posted between **18:00 and 24:00** (KST).
If any channel members have not submitted a message during this window, the
bot notifies them both in the channel and via direct message.

## Features

- **Automated checks** — The bot runs daily at 00:05 (KST) and scans the
  report channel for messages sent during the previous evening.
- **Non‑reporter notifications** — Members who have not posted a report are
  mentioned in the report channel and optionally receive a direct message
  reminder.
- **One‑shot mode** — The script can be invoked with `--once` to perform a
  single check and exit, making it easy to run via GitHub Actions or other
  schedulers.
- **Persistent mode** — When run normally, the bot stays online and uses a
  scheduled task loop to perform the daily check.

## Usage

1. Install dependencies (preferably in a virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your Discord bot token and the
   channel ID to monitor:

   ```bash
   cp .env.example .env
   # Edit .env and set DISCORD_TOKEN and REPORT_CHANNEL_ID
   ```

3. Run the bot:

   - **Persistent mode** (runs continuously and schedules daily checks):

     ```bash
     python bot.py
     ```

   - **One‑shot mode** (performs the check once and exits):

     ```bash
     python bot.py --once
     ```

## GitHub Actions

The repository includes a sample GitHub Actions workflow under
`.github/workflows/report_check.yml`. This workflow runs the bot once per day at
00:05 KST and is suitable if you prefer to schedule the check via Actions
rather than running a long‑lived process. To use it, save your bot token and
channel ID as repository secrets named `DISCORD_TOKEN` and `REPORT_CHANNEL_ID`.

## License

This project is provided under the MIT License. See `LICENSE` for details.# dailyReportCheckBot
