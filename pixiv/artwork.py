from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING

import aiohttp
import discord
from discord.utils import escape_markdown as escape

from .tags import PixivArtworkTag
from .user import PartialUser


__all__ = ("PixivArtwork",)


class PixivArtwork:
    """Represents a Pixiv artwork without image URL"""

    __slots__ = (
        "id",
        "title",
        "author",
        "nsfw",
        "created_at",
        "tags",
        "width",
        "height",
        "pages_count",
        "image_urls",
    )
    if TYPE_CHECKING:
        id: int
        title: str
        author: PartialUser
        nsfw: bool
        created_at: datetime
        tags: Union[List[str], List[PixivArtworkTag]]
        width: int
        height: int
        pages_count: int
        image_urls: Dict[str, str]

    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = int(data["id"])
        self.title = data["title"]
        self.author = PartialUser(data["userId"], data["userName"])
        self.nsfw = bool(data["xRestrict"])
        self.created_at = datetime.fromisoformat(data["createDate"])

        if isinstance(data["tags"], dict):
            tags = data["tags"]["tags"]
            self.tags = [PixivArtworkTag(d) for d in tags]
        else:
            self.tags = data["tags"]

        self.width = data["width"]
        self.height = data["height"]
        self.pages_count = data["pageCount"]
        self.image_urls = data["urls"]

    @property
    def url(self) -> str:
        return f"https://www.pixiv.net/en/artworks/{self.id}"

    async def get_image_url(self) -> str:
        url = self.image_urls["regular"]
        if url is not None:
            return url

        print(f"Cannot fetch image URL for artwork {self.id}, please enter it manually.")
        return await asyncio.to_thread(input, "image URL>")

    def create_embed(self, *, attachment_name: str = "image.png") -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            url=self.url,
            color=0x2ECC71,
            timestamp=self.created_at,
        )

        embed.set_image(url=f"attachment://{attachment_name}")

        if self.tags:
            embed.add_field(
                name="Tags",
                value=", ".join(f"[{str(tag)}]({tag.url})" for tag in self.tags),
                inline=False,
            )

        embed.add_field(
            name="Artwork ID",
            value=self.id,
        )
        embed.add_field(
            name="Author",
            value=f"[{escape(self.author.name)}]({self.author.url})",
        )
        embed.add_field(
            name="Size",
            value=f"{self.width} x {self.height}",
        )
        embed.add_field(
            name="Pages count",
            value=self.pages_count,
        )
        embed.add_field(
            name="Artwork link",
            value=self.url,
            inline=False,
        )

        return embed

    def __repr__(self) -> str:
        return f"<PixivArtwork title={self.title} id={self.id} author={self.author}>"

    @classmethod
    async def get(cls: Type[PixivArtwork], artwork_id: int, *, session: aiohttp.ClientSession) -> Optional[PixivArtwork]:
        """This function is a coroutine

        Get a ``PixivArtwork`` from an ID

        Parameters
        -----
        artwork_id: ``int``
            The artwork ID
        session: ``aiohttp.ClientSession``
            The session to perform the request

        Returns
        -----
        Optional[``PixivArtwork``]
            The retrieved artwork, or ``None`` if not found
        """
        with contextlib.suppress(aiohttp.ClientError, asyncio.TimeoutError):
            async with session.get(f"https://www.pixiv.net/ajax/illust/{artwork_id}") as response:
                if response.status != 200:
                    return

                data = await response.json(encoding="utf-8")
                if data["error"]:
                    return

                return cls(data["body"])
