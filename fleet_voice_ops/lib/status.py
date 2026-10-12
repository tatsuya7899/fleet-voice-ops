"""停滞の3値化(SPEC-initial.md §停滞の定義)。"""
from __future__ import annotations

ACTIVE_THRESHOLD_S = 600  # 10分

STATUS_ACTIVE = "active"
STATUS_STALLED_SUSPECT = "stalled_suspect"
STATUS_DEAD = "dead"


def classify(pid_alive: bool, elapsed_s: int) -> str:
    """生死(PID)×最終活動からの経過秒で3値化する。

    - dead: PID不在
    - active: PID生存 かつ elapsed_s が閾値(600秒)以内
    - stalled_suspect: PID生存 かつ elapsed_s が閾値超過
    """
    if not pid_alive:
        return STATUS_DEAD
    if elapsed_s <= ACTIVE_THRESHOLD_S:
        return STATUS_ACTIVE
    return STATUS_STALLED_SUSPECT
