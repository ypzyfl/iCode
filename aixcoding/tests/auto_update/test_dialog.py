# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Dialog tests: three answers on a normal release, one on a force upgrade.

Follows the upstream dialog-test shape (``test_session_title_dialog.py``):
push the dialog after entering ``run_test`` and query the dialog instance.

Design: aixcoding/docs/batches/auto-update/design.md §3.3
"""

from __future__ import annotations

from textual.app import App

from chrys.app.aixcoding.update.dialog import CONFIRM, LATER, SKIP, UpdateConfirmDialog
from chrys.service.aixcoding.update.client import AppUpdate


class _Harness(App[None]):
    """A bare app the dialog can be pushed onto."""

    CSS = "Screen { align: center middle; }"


def _update(*, force: bool = False) -> AppUpdate:
    return AppUpdate(version="0.36.0", download_url="http://mirror/x.zip", force_upgrade=force)


async def test_normal_release_offers_three_answers() -> None:
    app = _Harness()
    async with app.run_test() as pilot:
        answers: list[str] = []
        dialog = UpdateConfirmDialog(_update(), answers.append)
        app.push_screen(dialog)
        await pilot.pause()

        for button in ("#update-now", "#update-later", "#update-skip"):
            assert len(dialog.query(button)) == 1, f"{button} must exist on a normal release"

        await pilot.click("#update-later")
        assert answers == [LATER]


async def test_confirm_and_skip_buttons_answer() -> None:
    for button, expected in (("#update-now", CONFIRM), ("#update-skip", SKIP)):
        app = _Harness()
        async with app.run_test() as pilot:
            answers: list[str] = []
            dialog = UpdateConfirmDialog(_update(), answers.append)
            app.push_screen(dialog)
            await pilot.pause()

            await pilot.click(button)
            assert answers == [expected]


async def test_arrow_keys_switch_button_focus() -> None:
    """Left/right move the focus across the three buttons, wrapping (confirm.py house pattern)."""
    app = _Harness()
    async with app.run_test() as pilot:
        dialog = UpdateConfirmDialog(_update(), lambda _answer: None)
        app.push_screen(dialog)
        await pilot.pause()

        assert dialog.query_one("#update-now").has_focus, "the dialog opens focused on the primary action"

        await pilot.press("right")
        await pilot.pause()
        assert dialog.query_one("#update-later").has_focus, "right moves to the second button"

        await pilot.press("right")
        await pilot.pause()
        assert dialog.query_one("#update-skip").has_focus

        await pilot.press("right")
        await pilot.pause()
        assert dialog.query_one("#update-now").has_focus, "right wraps back to the first button"

        await pilot.press("left")
        await pilot.pause()
        assert dialog.query_one("#update-skip").has_focus, "left moves back"


async def test_focused_button_carries_a_visible_inline_highlight() -> None:
    """Revision 12: the focus highlight is inline — DEFAULT_CSS cannot beat chrys.tcss.

    Every button rests dark; the focused one alone carries the primary-variant
    fill, so the highlight visibly moves with the focus.
    """
    from pathlib import Path
    from typing import ClassVar

    from textual.color import Color

    import chrys.app.tui
    from chrys.app.tui.theme import TuiVariableDefaultsMixin

    tui_dir = Path(chrys.app.tui.__file__).parent

    class _ThemedHarness(TuiVariableDefaultsMixin, App[None]):
        """A bare app with the real stylesheet and theme variables (the
        ``tui-button-*`` variables exist only through the mixin)."""

        CSS_PATH: ClassVar = [tui_dir / "chrys.tcss", tui_dir / "screens" / "themes" / "editor.tcss"]

    app = _ThemedHarness()
    async with app.run_test() as pilot:
        dialog = UpdateConfirmDialog(_update(), lambda _answer: None)
        app.push_screen(dialog)
        await pilot.pause()

        fill = Color.parse(app.get_css_variables()["tui-button-primary-background"])
        now = dialog.query_one("#update-now")
        later = dialog.query_one("#update-later")

        assert now.has_focus
        assert now.styles.background == fill, "the focused button carries the primary-variant fill inline"
        assert later.styles.background != fill

        await pilot.press("tab")
        await pilot.pause()
        assert later.has_focus
        assert later.styles.background == fill, "the highlight follows the focus"
        assert now.styles.background != fill, "the blurred button rests dark like the others"


async def test_escape_counts_as_later_on_normal_release() -> None:
    app = _Harness()
    async with app.run_test() as pilot:
        answers: list[str] = []
        dialog = UpdateConfirmDialog(_update(), answers.append)
        app.push_screen(dialog)
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert answers == [LATER]


async def test_force_upgrade_is_single_option_and_holds_shut() -> None:
    app = _Harness()
    async with app.run_test() as pilot:
        answers: list[str] = []
        dialog = UpdateConfirmDialog(_update(force=True), answers.append)
        app.push_screen(dialog)
        await pilot.pause()

        assert len(dialog.query("#update-now")) == 1, "update-now stays on a force upgrade"
        assert not len(dialog.query("#update-later")) and not len(dialog.query("#update-skip")), (
            "no way out but updating"
        )
        assert dialog._dismiss_on_backdrop is False, "a force upgrade cannot be backdrop-dismissed"

        await pilot.press("escape")
        await pilot.pause()
        assert answers == [], "escape must not answer a force upgrade"
        assert app.screen is dialog, "the force dialog must stay on top"

        await pilot.click("#update-now")
        assert answers == [CONFIRM]


async def test_every_dismissal_path_delivers_exactly_one_answer() -> None:
    """A repeated dismissal (the base class defers a second one) still answers once."""
    app = _Harness()
    async with app.run_test() as pilot:
        answers: list[str] = []
        dialog = UpdateConfirmDialog(_update(), answers.append)
        app.push_screen(dialog)
        await pilot.pause()

        dialog.dismiss(SKIP)
        dialog.dismiss(LATER)  # already closing — must not deliver twice
        await pilot.pause()

        assert answers == [SKIP]
