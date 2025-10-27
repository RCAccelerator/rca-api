# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    def __init__(self, token: str, channels: list[str] | None = None):
        self.client = WebClient(token=token)
        self.channels = channels or []

    def search_messages(self, query: str, count: int = 20) -> list[dict]:
        all_messages: dict[str, dict] = {}

        for channel in self.channels:
            if not channel:
                continue

            # remove '#' from channel name if present
            channel_name = channel.strip().lstrip("#")
            search_query = f"{query} in:#{channel_name}"

            try:
                result = self.client.search_messages(query=search_query, count=count)
            except SlackApiError as e:
                logging.error(f"Error searching slack in channel {channel}: {e}")
                continue

            if result["ok"]:
                for match in result["messages"]["matches"]:
                    permalink = match.get("permalink")
                    if permalink and permalink not in all_messages:
                        all_messages[permalink] = {
                            "text": match.get("text"),
                            "user": match.get("user"),
                            "permalink": permalink,
                            "channel": match.get("channel", {}).get("name"),
                        }
        return list(all_messages.values())
