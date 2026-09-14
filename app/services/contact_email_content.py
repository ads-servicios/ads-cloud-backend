from dataclasses import dataclass


@dataclass(frozen=True)
class InlineImage:
    cid: str
    content: bytes
    subtype: str = "png"


@dataclass(frozen=True)
class OutboundEmail:
    to: str
    subject: str
    body_text: str | None = None
    body_html: str | None = None
    reply_to: str | None = None
    inline_images: tuple[InlineImage, ...] = ()


@dataclass(frozen=True)
class ContactEmailContent:
    subject: str
    body: str
