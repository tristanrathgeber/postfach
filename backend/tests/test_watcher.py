from postfach.watcher import AccountWatcher, LiveState


class FakeIdleClient:
    """Simuliert imapclient-IDLE: Liste von idle_check-Antworten pro Aufruf."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def select_folder(self, name, readonly=False):
        self.calls.append(("select", name))

    def idle(self):
        self.calls.append(("idle",))

    def idle_check(self, timeout=None):
        self.calls.append(("idle_check", timeout))
        return self.responses.pop(0) if self.responses else []

    def idle_done(self):
        self.calls.append(("idle_done",))


def test_live_state_versions_bump_per_account():
    state = LiveState()
    assert state.snapshot() == {}
    state.bump("gmx")
    state.bump("gmx")
    state.bump("anderes")
    snap = state.snapshot()
    assert snap["gmx"] == 2
    assert snap["anderes"] == 1


def test_watcher_detects_exists_event_and_bumps():
    state = LiveState()
    client = FakeIdleClient([[(3, b"EXISTS")], [], [(4, b"EXISTS"), (1, b"RECENT")]])
    watcher = AccountWatcher("gmx", state, on_new_mail=None)
    assert watcher.poll_once(client) is True  # EXISTS → neue Mail
    assert watcher.poll_once(client) is False  # nichts
    assert watcher.poll_once(client) is True
    assert state.snapshot()["gmx"] == 2


def test_watcher_calls_new_mail_hook():
    calls = []
    state = LiveState()
    watcher = AccountWatcher("gmx", state, on_new_mail=lambda account: calls.append(account))
    watcher.poll_once(FakeIdleClient([[(9, b"EXISTS")]]))
    assert calls == ["gmx"]


def test_watcher_hook_errors_do_not_break_polling():
    state = LiveState()

    def broken_hook(account):
        raise RuntimeError("Index kaputt")

    watcher = AccountWatcher("gmx", state, on_new_mail=broken_hook)
    assert watcher.poll_once(FakeIdleClient([[(9, b"EXISTS")]])) is True
    assert state.snapshot()["gmx"] == 1  # Version bumpt trotzdem
