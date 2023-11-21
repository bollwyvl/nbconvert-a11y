"""axe accessibility testing on exported nbconvert scripts

* test the accessibility of exported notebooks
* test the accessibility of nbconvert-a11y dialogs
"""

from logging import getLogger
from pathlib import Path

import exceptiongroup
from nbconvert_html5.pytest_axe import inject_axe, run_axe_test
from test_nbconvert_html5 import exporter


from pytest import fixture, mark, param, xfail

from tests.test_smoke import CONFIGURATIONS, NOTEBOOKS, SKIPCI, get_target_html

TPL_NOT_ACCESSIBLE = mark.xfail(reason="template is not accessible")
HERE = Path(__file__).parent
EXPORTS = HERE / "exports"
HTML = EXPORTS / "html"
LOGGER = getLogger(__name__)
AUDIT = EXPORTS / "audit"

# ignore mathjax at the moment. we might be able to turne mathjax to have better
# accessibility. https://github.com/Iota-School/notebooks-for-all/issues/81
MATHJAX = "[id^=MathJax]"
NEEDS_WORK = "state needs work"


config_notebooks_aa = mark.parametrize(
    "config,notebook",
    [
        param(
            (CONFIGURATIONS / (a := "a11y")).with_suffix(".py"),
            (NOTEBOOKS / (b := "lorenz-executed")).with_suffix(".ipynb"),
            id="-".join((b, a)),
        ),
        param(
            (CONFIGURATIONS / (a := "default")).with_suffix(".py"),
            (NOTEBOOKS / (b := "lorenz-executed")).with_suffix(".ipynb"),
            marks=[SKIPCI, TPL_NOT_ACCESSIBLE],
            id="-".join((b, a)),
        ),
    ],
)

config_notebooks_aaa = mark.parametrize(
    "config,notebook",
    [
        param(
            (CONFIGURATIONS / (a := "a11y")).with_suffix(".py"),
            (NOTEBOOKS / (b := "lorenz-executed")).with_suffix(".ipynb"),
            id="-".join(
                (b, a),
            ),
            marks=[TPL_NOT_ACCESSIBLE],
        )
    ],
)


axe_config_aaa = {
    "runOnly": [
        "act",
        "best-practice",
        "experimental",
        "wcag21a",
        "wcag21aa",
        "wcag22aa",
        "wcag2aaa",
    ],
    "allowedOrigins": ["<same_origin>"],
}


@config_notebooks_aa
def test_axe_aa(axe, config, notebook):
    target = get_target_html(config, notebook)
    audit = AUDIT / target.with_suffix(".json").name
    axe(Path.as_uri(target)).dump(audit).raises()


@config_notebooks_aaa
def test_axe_aaa(axe, config, notebook):
    target = get_target_html(config, notebook)
    audit = AUDIT / target.with_suffix(".json").name
    axe(Path.as_uri(target), axe_config=axe_config_aaa).dump(audit).raises()


config_notebooks_dialog = mark.parametrize(
    "config,notebook",
    [
        param(
            (CONFIGURATIONS / (a := "a11y")).with_suffix(".py"),
            (NOTEBOOKS / (b := "lorenz-executed")).with_suffix(".ipynb"),
            id="-".join(
                (b, a),
            ),
        )
    ],
)


@fixture(scope="function")
def axe_page(page):
    def go(url):
        page.goto(url)
        inject_axe(page)
        return page

    return go


@config_notebooks_dialog
@mark.parametrize(
    "dialog",
    [
        "[aria-controls=nb-settings]",
        "[aria-controls=nb-help]",
        "[aria-controls=nb-metadata]",
        "[aria-controls=nb-audit]",
        param("[aria-controls=nb-expanded-dialog]", marks=mark.xfail(reason=NEEDS_WORK)),
        param("[aria-controls=nb-visibility-dialog]", marks=mark.xfail(reason=NEEDS_WORK)),
        param("nada", marks=mark.xfail(reason="no selector")),
    ],
)
def test_dialogs(axe_page, config, notebook, dialog):
    """test the controls in dialogs"""
    # dialogs are not tested in the baseline axe test. they need to be active to test.
    # these tests activate the dialogs to assess their accessibility with the active dialogs.

    page = axe_page(get_target_html(config, notebook).absolute().as_uri())
    page.click(dialog)
    run_axe_test(page).raises()


@config_notebooks_dialog
def test_settings_font_size(axe_page, config, notebook):
    """test that the settings make their expected changes"""
    page = axe_page(get_target_html(config, notebook).absolute().as_uri())
    font_size = lambda: page.evaluate(
        """window.getComputedStyle(document.querySelector("body")).getPropertyValue("font-size")"""
    )
    assert font_size() == "16px"
    page.click("[aria-controls=nb-settings]")
    page.locator("#nb-table-font-size-group").select_option("xx-large")
    assert font_size() == "32px", "font size not changed"