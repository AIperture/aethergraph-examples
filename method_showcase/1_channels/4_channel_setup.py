# Prerequisite: interactive channel setup (e.g., Slack or Telegram)
# See: https://aiperture.github.io/aethergraph-docs/channel-setup/introduction/ for channel setup instructions.
#
# Make sure to set the following environment variables for the channels to work:
# For Slack:
#   AETHERGRAPH_SLACK__ENABLED=true # If not set, Slack channel will be disabled
#   AETHERGRAPH_SLACK__BOT_TOKEN=your-slack-bot-token
#   AETHERGRAPH_SLACK__APP_TOKEN=your-slack-app-level-token
#   AETHERGRAPH_SLACK__SIGNING_SECRET=your-slack-signing-secret
#
# For Telegram:
#   AETHERGRAPH_TELEGRAM__ENABLED=true # If not set, Telegram channel will be disabled
#   AETHERGRAPH_TELEGRAM__BOT_TOKEN=your-telegram-bot-token
#
# No other special env vars needed for webhook or file channels
#
# Channel key formats:
#   Console: console:stdin (default)
#   Slack:   slack:team/{TEAM_ID}:chan/{CHANNEL_ID}
#   Telegram: tg:chat/{CHAT_ID}
#   Webhook: webhook:url/{WEBHOOK_URL}
#   File:    file:{FILE_PATH}


from aethergraph import graph_fn, NodeContext
from aethergraph import start_server
from aethergraph.runtime import (
    set_default_channel,
    set_channel_alias,
)
import os 

# example graph_fn
@graph_fn(name="test_channel_service")
async def test_channel_service(context: NodeContext):
    channel = context.channel() # default channel set in main
    await channel.send_text("Hello from Aethergraph via Slack channel!")

    channel = context.channel("my_slack") # use alias; to be set in main
    await channel.send_text("Hello again via my_slack alias!")

    channel = context.channel("my_telegram") # use alias; to be set in main
    await channel.send_text("Hello via my_telegram alias!")
    return {"status": "message sent"}


if __name__ == "__main__":
    from aethergraph.runner import run_async
    import asyncio

    # typical usage: set up channel service with multiple channels and aliases
    SLACK_TEAM_ID = os.getenv("SLACK_TEAM_ID", "your-slack-team-id")
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "your-slack-channel-id")
    slack_channel_key = f"slack:team/{SLACK_TEAM_ID}:chan/{SLACK_CHANNEL_ID}" # Slack channel key format

    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your-telegram-chat-id")
    telegram_channel_key = f"tg:chat/{TELEGRAM_CHAT_ID}" # Telegram channel key format

    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "your-webhook-url") 
    webhook_channel_key = f"webhook:url/{WEBHOOK_URL}" # Webhook channel key format 

    FILE_PATH = os.getenv("FILE_PATH", "runs/demo_run.log")
    file_channel_key = f"file:{FILE_PATH}" # File channel key format 

    # start url before setting up channels
    url = start_server(port=0)

    set_default_channel(slack_channel_key) # set default channel to Slack
    set_channel_alias("my_slack", slack_channel_key)
    set_channel_alias("my_telegram", telegram_channel_key)
    # you can also set up aliases for other channels if needed

    asyncio.run(run_async(test_channel_service, inputs={}))