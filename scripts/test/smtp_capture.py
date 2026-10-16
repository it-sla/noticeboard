"""Local SMTP sink for e2e tests: accepts everything, appends one JSON line per message.

Usage: python smtp_capture.py <port> <output.jsonl>   (binds 127.0.0.1 only)
"""

import json
import sys
import time
from pathlib import Path
from email import message_from_bytes, policy

from aiosmtpd.controller import Controller


class Sink:
    def __init__(self, path: str):
        self.path = path

    async def handle_DATA(self, server, session, envelope):
        msg = message_from_bytes(envelope.content, policy=policy.default)
        body = msg.get_body(("plain",))
        rec = {
            "to": envelope.rcpt_tos,
            "from": envelope.mail_from,
            "subject": str(msg["Subject"]),
            "text": body.get_content() if body else "",
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return "250 OK"


if __name__ == "__main__":
    port, out = int(sys.argv[1]), sys.argv[2]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    open(out, "w").close()
    Controller(Sink(out), hostname="127.0.0.1", port=port).start()
    print(f"SMTP capture listening on 127.0.0.1:{port}", flush=True)
    while True:
        time.sleep(3600)
