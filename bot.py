"""
Discord Weekly Report Bot

This script runs a Discord bot that checks a specific channel each day for
messages posted between 18:00 and midnight (KST). If any channel members
have not submitted their report during this window, the bot will notify
them both in the channel and via direct message. The script can run in
two modes:

1. **Persistent mode** – When executed normally, the bot stays online and
   schedules a daily check at 00:05 KST using a `tasks.loop`. This mode is
   ideal when hosting the bot on a server or VPS.

2. **One‑shot mode** – When invoked with the `--once` flag, the bot
   connects, performs a single check immediately, sends notifications, and
   exits. This mode works well with GitHub Actions or other schedulers
   where long‑running processes are undesirable.

Configuration values such as the Discord token and the report channel ID
should be stored in a `.env` file or environment variables. See the
provided `.env.example` for details.
"""

import os
import asyncio
import logging
from datetime import datetime, time, timedelta

import discord
import pytz
from discord.ext import commands, tasks
from dotenv import load_dotenv


# Load environment variables from a .env file if present
load_dotenv()

# Read configuration from environment
TOKEN = os.getenv("DISCORD_TOKEN")
REPORT_CHANNEL_ID = os.getenv("REPORT_CHANNEL_ID")
if REPORT_CHANNEL_ID is None:
    raise RuntimeError(
        "REPORT_CHANNEL_ID is not set. Please provide a channel ID in your .env file or environment."
    )
REPORT_CHANNEL_ID = int(REPORT_CHANNEL_ID)

# Optional: Limit eligibility to a hard‑coded list of user IDs
TARGET_MEMBER_IDS = {
    int(uid.strip())
    for uid in os.getenv("TARGET_MEMBER_IDS", "").split(",")
    if uid.strip().isdigit()
}
if TARGET_MEMBER_IDS:
    logger = logging.getLogger("weekly_report_bot")
    logger.info("Filtering eligible members to IDs: %s", TARGET_MEMBER_IDS)

# Define the timezone for all time calculations (KST: UTC+9)
KST = pytz.timezone("Asia/Seoul")

# Configure Discord intents
# intents = commands.Intents(
#     guilds=True,
#     members=True,
#     messages=True,
#     message_content=True,
# )

intents = discord.Intents.default()      # ✅ 이게 맞음
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)
logger = logging.getLogger("weekly_report_bot")
logging.basicConfig(level=logging.INFO)


@bot.event
async def on_ready() -> None:
    """Called when the bot is connected and ready."""
    logger.info("Bot online: %s", bot.user)
    if not check_reports_loop.is_running():
        check_reports_loop.start()


def _today_range() -> tuple[datetime, datetime]:
    """Return the start and end datetimes for today's report window (18:00–23:59 KST).

    If the current time is after midnight and before 06:00 KST, we look back
    at the previous day's window to allow for late checks just after midnight.
    """
    now = datetime.now(KST)
    start = now.replace(hour=18, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    # If we're in the early morning hours, adjust to yesterday's window
    if now.hour < 6:
        start -= timedelta(days=1)
        end -= timedelta(days=1)
    return start, end


@tasks.loop(time=time(hour=0, minute=5, tzinfo=KST))
async def check_reports_loop() -> None:
    """Check the report channel for messages in the report window and notify non-reporters."""
    start, end = _today_range()
    await check_reports(start, end)


async def check_reports(custom_start: datetime | None = None, custom_end: datetime | None = None) -> None:
    """Check the report channel for messages in the given report window and notify non-reporters.

    If no custom_start and custom_end are provided, defaults to today's window.
    """
    if custom_start is None or custom_end is None:
        custom_start, custom_end = _today_range()

    # 이 부분 변경
    # channel = bot.get_channel(REPORT_CHANNEL_ID)
    try:
        channel = await bot.fetch_channel(REPORT_CHANNEL_ID)
    except discord.NotFound:
        logger.error("Channel ID %s not found or inaccessible", REPORT_CHANNEL_ID)
        return
    except discord.Forbidden:
        logger.error("Missing permissions to access channel ID %s", REPORT_CHANNEL_ID)
        return
    except discord.HTTPException as e:
        logger.error("Failed to fetch channel ID %s: %s", REPORT_CHANNEL_ID, e)
        return


    start, end = custom_start, custom_end
    logger.info(
        "Checking reports between %s and %s for channel %s",
        start.isoformat(),
        end.isoformat(),
        REPORT_CHANNEL_ID,
    )
    # Collect user IDs of those who sent messages during the window
    try:
        reporters = {
            message.author.id
            async for message in channel.history(after=start, before=end, limit=None)
        }
    except discord.Forbidden:
        logger.error("Missing permissions to read message history in channel ID %s", REPORT_CHANNEL_ID)
        return
    except discord.HTTPException as e:
        logger.error("Failed to read message history in channel ID %s: %s", REPORT_CHANNEL_ID, e)
        return

    # Ensure guild and bot.user are properly connected
    if channel.guild is None:
        logger.error("Channel ID %s does not belong to a guild", REPORT_CHANNEL_ID)
        return
    if bot.user is None:
        logger.error("Bot user is not available")
        return

    def _can_read(channel: discord.abc.GuildChannel, member: discord.Member) -> bool:
        """Safely check if member can read the channel, falling back to False on errors."""
        try:
            return channel.permissions_for(member).read_messages
        except AttributeError:
            # In rare cases member or default role is incomplete in cache
            return False

    # --- Build the list of members who can see this channel (exclude bots) ---
    eligible_members: list[discord.Member] = []
    try:
        # Always fetch from the HTTP endpoint to avoid cache issues
        async for member in channel.guild.fetch_members(limit=None):
            if not member.bot and _can_read(channel, member):
                eligible_members.append(member)
    except discord.Forbidden:
        logger.error(
            "Missing permissions to fetch members in guild ID %s", channel.guild.id
        )
        return
    except discord.HTTPException as e:
        logger.error(
            "Failed to fetch members in guild ID %s: %s", channel.guild.id, e
        )
        return

    # If a target ID list is provided, filter to those IDs only
    if TARGET_MEMBER_IDS:
        eligible_members = [m for m in eligible_members if m.id in TARGET_MEMBER_IDS]

    logger.info(
        "Eligible member count in channel %s: %d", channel.id, len(eligible_members)
    )

    # Debug: print the fetched eligible members (display_name and ID)
    print(
        "Eligible members:",
        [f"{m.display_name} ({m.id})" for m in eligible_members],
    )
    # Non‑reporters = eligible members who did not post during the window
    non_reporters = [m for m in eligible_members if m.id not in reporters]

    # If everyone reported, send a confirmation and exit
    if not non_reporters:
        await channel.send(
            "✅ 오늘(어제 18시~자정) 주간보고 미제출자는 없습니다!"
        )
        return

    # Create mention strings for each non-reporter
    mention_list = " ".join(member.mention for member in non_reporters)

    await channel.send(
        f"⏰ 아직 주간보고를 작성하지 않은 분들입니다!\n{mention_list}"
    )

    # Optionally send a direct message to each non-reporter
    for member in non_reporters:
        try:
            await member.send(
                "오늘 18:00~24:00 사이 주간보고가 확인되지 않았습니다. 잊지 말고 작성해주세요!"
            )
        except discord.Forbidden as exc:
            logger.warning("Could not DM %s: Forbidden - %s", member, exc)
        except discord.HTTPException as exc:
            logger.warning("Could not DM %s: HTTPException - %s", member, exc)
        except Exception as exc:  # catch generic exceptions to avoid blocking loop
            logger.warning("Could not DM %s: %s", member, exc)


@bot.command()
@commands.has_permissions(administrator=True)
async def check(ctx: commands.Context) -> None:
    """Manually trigger the report check. Only accessible to administrators."""
    await check_reports()


def main() -> None:
    """Entry point to run the bot. Supports the --once flag for single-run mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Discord weekly report bot")
    parser.add_argument(
        "--once", action="store_true", help="Run the check once and exit"
    )
    parser.add_argument(
        "--window-start",
        type=str,
        help="Custom report window start time in ISO format (e.g. 2024-06-01T18:00:00+09:00)",
    )
    parser.add_argument(
        "--window-end",
        type=str,
        help="Custom report window end time in ISO format (e.g. 2024-06-01T23:59:59+09:00)",
    )
    args = parser.parse_args()

    if args.once:
        # Parse custom window times if provided
        custom_start = None
        custom_end = None
        if args.window_start:
            custom_start = datetime.fromisoformat(args.window_start)
        if args.window_end:
            custom_end = datetime.fromisoformat(args.window_end)

        # In one‑shot mode, run the report check after a successful connection
        async def one_shot() -> None:
            # Define a one‑time on_ready listener
            async def _run_once_ready() -> None:
                await check_reports(custom_start, custom_end)
                await bot.close()

            bot.add_listener(_run_once_ready, "on_ready")
            # start() handles both login + connect. It returns once the bot is closed.
            await bot.start(TOKEN, reconnect=False)

        asyncio.run(one_shot())
    else:
        # In persistent mode, start the bot and keep it running
        bot.run(TOKEN)


if __name__ == "__main__":
    main()