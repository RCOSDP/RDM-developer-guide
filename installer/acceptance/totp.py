"""RFC 6238 time-based one-time passwords (HMAC-SHA1, 30 s, 6 digits) for the seeded administrator of C6.

RDM-osf.io-dev2027 PR #10 accepts a TOTP code once per time step, so `next_code` never returns the code of a step
it already returned: it waits for the next step instead. The secret is a run secret (`GRDM_ACCEPT_ADMIN_TOTP_SECRET`,
masked in every report); nothing here prints it.
"""
from __future__ import annotations

import hashlib
import hmac
import struct
import time

PERIOD = 30
DIGITS = 6
_last_step: dict[str, int] = {}


def code_at(secret_hex: str, when: float, period: int = PERIOD, digits: int = DIGITS) -> str:
    """The code for the time step containing `when` (RFC 4226 dynamic truncation of HMAC-SHA1)."""
    counter = int(when // period)
    digest = hmac.new(bytes.fromhex(secret_hex), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** digits).zfill(digits)


def next_code(secret_hex: str, clock=time.time, sleep=time.sleep) -> str:
    """A code that was not returned before for this secret; waits (at most one period) for a fresh step."""
    while True:
        now = clock()
        step = int(now // PERIOD)
        if _last_step.get(secret_hex) != step:
            _last_step[secret_hex] = step
            return code_at(secret_hex, now)
        sleep(max(0.2, (step + 1) * PERIOD - now + 0.2))
