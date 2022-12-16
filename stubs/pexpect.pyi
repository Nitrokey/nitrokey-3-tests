# Copyright (C) 2022 Nitrokey GmbH
# SPDX-License-Identifier: CC0-1.0

class spawn:
    def __init__(self, cmd: str, args: list[str] = [], timeout: int = 30) -> None:
        pass

    def expect(self, s: str) -> None:
        pass

    def sendline(self, s: str) -> None:
        pass
