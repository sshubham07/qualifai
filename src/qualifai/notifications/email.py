"""Transactional email (SMTP; Mailpit locally). Links carry no secrets when accounts are used."""

from email.message import EmailMessage

import aiosmtplib  # swap for an email API later if needed

from qualifai.config.settings import get_settings


async def send(to: str, subject: str, body: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.mail_from, to, subject
    msg.set_content(body)
    await aiosmtplib.send(msg, hostname=s.smtp_host, port=s.smtp_port)


async def send_kit_ready(to: str, link: str, expires_on: str) -> None:
    await send(
        to,
        "Your QualifAI interview is ready",
        f"Your interview is ready. Start here: {link}\nIt expires on {expires_on}.",
    )


async def send_report_ready(to: str, link: str) -> None:
    await send(to, "Your QualifAI report is ready", f"View your report: {link}")
