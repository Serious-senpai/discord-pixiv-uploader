from __future__ import annotations

import asyncio
import json
import os
import re
import shlex

import aiohttp

import pixiv


URL_PATTERN = re.compile(r"https://www\.pixiv\.net/(en/)?artworks/(\d+)/?.*")
try:
    TOKEN = os.environ["TOKEN"]
except KeyError:
    TOKEN = input("Enter bot token>")


async def main() -> None:
    current_channel = None
    async with aiohttp.ClientSession(headers={"accept-language": "en-US,en;q=0.9"}) as session:
        while True:
            text_cmd = await asyncio.to_thread(input, "command>")
            try:
                command, *arguments = shlex.split(text_cmd)
            except ValueError:
                print("Invalid command")
            else:
                command = command.lower()

                if command == "help":
                    print("Available commands:\n" + "-" * 20)
                    commands = ["help", "quit", "set <channel ID>", "send <Pixiv URL>"]
                    commands.sort()
                    print("\n".join(commands))

                elif command == "quit":
                    return

                elif command == "set":
                    try:
                        current_channel = arguments[0]
                    except IndexError:
                        print("Missing argument")
                        continue

                    print(f"Set target channel ID to {current_channel}")

                elif command == "send":
                    if current_channel is None:
                        print("Please set current channel first!")
                        continue

                    try:
                        url = arguments[0]
                    except IndexError:
                        print("Missing argument")
                        continue

                    match = URL_PATTERN.fullmatch(url)
                    if match is None:
                        print(f"Invalid URL: {url}")

                    else:
                        artwork_id = int(match.group(2))
                        artwork = await pixiv.PixivArtwork.get(artwork_id, session=session)
                        if artwork is None:
                            print("Cannot find such artwork!")

                        else:
                            image_url = await artwork.get_image_url()
                            try:
                                async with session.get(image_url, headers={"referer": "https://www.pixiv.net/"}) as response:
                                    response.raise_for_status()
                                    data = await response.read()

                            except aiohttp.ClientError:
                                print(f"Cannot fetch image from {image_url}!")
                            else:
                                embed = artwork.create_embed()

                                # Create message
                                form_data = aiohttp.FormData(quote_fields=False)
                                form_data.add_field(
                                    name="payload_json",
                                    value=json.dumps(
                                        {
                                            "embeds": [embed.to_dict()],
                                            "attachments": [{
                                                "id": 0,
                                                "filename": "image.png",
                                            }],
                                        },
                                        ensure_ascii=True,
                                    ),
                                    content_type="application/json",
                                )
                                form_data.add_field(
                                    name="files[0]",
                                    value=data,
                                    content_type="image/png",
                                )

                                # Create header
                                headers = {
                                    "Authorization": f"Bot {TOKEN}",
                                }

                                async with session.post(
                                    f"https://discord.com/api/v10/channels/{current_channel}/messages",
                                    data=form_data,
                                    headers=headers,
                                ) as response:
                                    print(f"HTTP status {response.status}")

                else:
                    print(f"Unknown command: {command}")


asyncio.run(main())
