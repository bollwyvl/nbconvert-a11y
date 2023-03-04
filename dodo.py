from shutil import move, copyfile
from doit import create_after, task_params
from pathlib import Path
from functools import partial
import warnings

HERE = Path(__file__).parent

DOCS = Path("docs")
UTESTS = Path("user-tests")
TESTS = Path("tests")
EXPORTS = TESTS / "exports"
NBS = EXPORTS / "notebooks"
CONFIGS = EXPORTS / "configs"
HTML = EXPORTS / "html"
AUDITS = EXPORTS / "audits"
REPORTS = EXPORTS / "reports"

def cp(x, y):
    Path.mkdir(y.parent, parents=True, exist_ok=True)
    copyfile(x, y)


@task_params(
    [
        dict(name="notebooks", default=[TESTS / "notebooks/lorenz.ipynb"], type=list),
        dict(name="configurations", default=[TESTS / "configurations/default.py"], type=list),
        dict(name="target", default=EXPORTS, type=str),
    ]
)
def task_copy(notebooks, configurations, target):
    """copy all of the notebooks we use for testing into a single directory that is exported with the documentation."""
    NB = target / "notebooks"
    CONFIGS = target / "configs"
    notebooks = list(map(Path, notebooks))
    configurations = list(map(Path, configurations))
    targets = [NB / x.name for x in notebooks]
    def readme(target, ext, title):
        body = F"""# {title}\n\n"""
        for t in target.glob(F"*.{ext}"):
            body += F"* [{t.name}]({t.relative_to(target)})\n"
        (target / "README.md").write_text(body)

    yield dict(
        name="notebooks",
        clean=True,
        actions=[(cp, (x, NB /x.name )) for x in notebooks],
        targets=targets,
        uptodate=list(map(Path.exists, targets))
    )
    targets = [CONFIGS / x.name for x in configurations]
    yield dict(
        name="configurations",
        clean=True,
        actions=[(cp, (x, CONFIGS / x.name)) for x in configurations],
        targets=[CONFIGS / x.name for x in configurations],
        uptodate=list(map(Path.exists, targets))
    )
    yield dict(
        name="readme-nb",
        actions=[(readme, (NB, "ipynb", "reference notebooks"))],
        file_dep=targets,
        targets=[NB / "README.md"]
    )
    yield dict(
        name="readme-config",
        actions=[(readme, (CONFIGS, "py", "configuration files"))],
        file_dep=targets,
        targets=[CONFIGS / "README.md"]
    )
# @task_params(
#     [
#         dict(name="notebooks", default=[TESTS / "notebooks/lorenz.ipynb"], type=list),
#         dict(name="configuration", default="tests/configurations", type=str),
#         dict(name="target", default="docs/exports", type=str),
#         dict(name="audit", default=True, type=bool),
#     ]
# )
# def task_export(notebooks, configuration, target, audit):
#     target = Path(target)
#     rel = []

#     configs = []

#     for c in Path(configuration).glob("*.py"):
#         for nb in map(Path, notebooks):
#             name = "-".join((nb.stem, c.stem))
#             t = target / (name + ".html")
#             rel.append(t)
#             yield dict(
#                 name=f"export:{name}",
#                 actions=[
#                     f"jupyter nbconvert --config {c} --output {name} --output-dir {target} {nb}"
#                 ],
#                 file_dep=[nb, c],
#                 targets=[t],
#                 clean=True,
#             )
#             configs.append(
#                 dict(config=c, nb=nb, html=t, audit=t.parent / "data" / (t.name + ".json"))
#             )

#     if audit:
#         from nbconvert_html5.audit import main

#         audits = [x["audit"] for x in configs]
#         yield dict(
#             name=f"audit",
#             actions=[partial(main, id=rel, output_dir=Path("docs/exports/data"))],
#             targets=audits,
#             file_dep=[x["html"] for x in configs],
#             clean=True,
#         )

#     INDEX = DOCS / "index.md"

#     def get_violations(targets):
#         import pandas
#         from json import loads

#         return (
#             targets.apply(lambda x: pandas.Series(loads(x.read_text())))
#             .stack()
#             .apply(lambda x: len(x["nodes"]))
#             .unstack()
#             .fillna(0)
#             .sum(1)
#             .to_frame("nodes in violation")
#         )

#     def get_index():
#         body = "# sample converted notebooks\n\n"
#         import pandas

#         df = pandas.DataFrame(configs)

#         # config and nb are relative to the github repo
#         # audit and html are relative to the docs
#         names = df.applymap(lambda x: x.stem)
#         violations = get_violations(df.audit)
#         df = pandas.concat(
#             [
#                 df[["config", "nb"]]
#                 .applymap(str)
#                 .applymap("https://github.com/iota-school/notebooks-for-all/blob/main/".__add__),
#                 df[["audit", "html"]]
#                 .applymap(lambda x: x.relative_to("docs"))
#                 .applymap(str)
#                 .applymap("/notebooks-for-all/".__add__),
#             ]
#         )

#         df = ("[" + names.stack() + "](" + df.stack() + ")").unstack()
#         df = df.set_index("config")[["nb", "html", "audit"]]  # order the columns

#         df = df.assign(violations=violations.values)
#         body += df.to_markdown()

#         INDEX.write_text(body)

#     yield dict(name=f"index", file_dep=audits, targets=[INDEX], actions=[get_index], clean=True)

@create_after("copy")
@task_params(
    [
        dict(name="notebooks_dir", default=NBS, type=str),
        dict(name="configs_dir", default=CONFIGS, type=str),
        dict(name="target", default=HTML, type=str),
    ]
)
def task_convert(notebooks_dir, configs_dir, target):
    """convert notebooks and configurations to their html outputs"""
    target = Path(target)
    def readme(target):
        body = """# html versions\n\n"""
        for t in target.glob("*.html"):
            body += F"* [{t.name}]({t.relative_to(target)})\n"
        (target / "README.md").write_text(body)
    targets = []
    for c in Path(configs_dir).glob("*.py"):
        for nb in Path(notebooks_dir).glob("*.ipynb"):
            name = "-".join((nb.stem, c.stem))
            t = Path(target) / (name + ".html")
            targets.append(t)
            yield dict(
                name=str(name),
                actions=[
                    f"jupyter nbconvert --config {c} --output {name} --output-dir {target} {nb}"
                ],
                file_dep=[nb, c],
                targets=[t],
                clean=True,
                basename="convert"
            )
    yield dict(
        name="readme",
        actions=[(readme, (target,))],
        file_dep=targets,
        targets=[target / "README.md"]
    )
    
@create_after(executed="convert", creates=["audit"])
@task_params(
    [
        dict(name="html_dir", default=HTML, type=str),
        dict(name="target", default=AUDITS, type=str, help="the subdirectory to place audits in")
    ]
)
def task_audit(html_dir, target):
    """audit the files in the html directory"""
    def readme(target):
        body = """# audits\n\n"""
        for t in target.glob("*.json"):
            body += F"* [{t.name}]({t.relative_to(target)})\n"
        (target / "README.md").write_text(body)

    from nbconvert_html5.audit import audit_one
    targets = []
    for x in Path(html_dir).rglob("*.html"):
        targets.append(Path(target) / x.with_suffix(".json").name)
        yield dict(
            name=x.name,
            actions=[
                (audit_one, (x, targets[-1]))
            ],
            file_dep=[x],
            targets=[targets[-1]],
            clean=True,
            basename="audit"
        )
    yield dict(
        name="readme",
        actions=[(readme, (target,))],
        file_dep=targets,
        targets=[target / "README.md"]
    )

@create_after(executed="audit")
def task_report():
    from tests.templates import report
    yield dict(
        name="readme",
        actions=[report.write_experiments],
        clean=True,
        targets=[REPORTS / "experiment.md"]
    )
    yield dict(
        name="nb",
        actions=[report.write_notebooks],
        clean=True,
        targets=[REPORTS / "notebooks.md"]
    )
# @create_after(executed="audit", creates=["docs"])
# @task_params(
#     [
#         dict(name="dir", default="docs/exports", type=str),
#         dict(name="folder", default="audit", type=str, help="the subdirectory to place audits in")
#     ]
# )
# def task_audit(dir, folder="audit"):
#     from nbconvert_html5.audit import audit_one
#     for x in Path(dir).rglob("*.html"):
#         a = x.parent / folder / x.name
#         yield dict(
#             name=str(x.relative_to(dir)),
#             actions=[
#                 (audit_one, (x,))
#             ],
#             file_dep=[x],
#             targets=[a],
#             clean=True,
#             basename="audit"
# )


# @task_params(
#     [
#         dict(name="notebooks", default=[TESTS / "notebooks/lorenz.ipynb"], type=list),
#         dict(name="configurations", default=[TESTS / "notebooks/lorenz.ipynb"], type=list),
#         dict(name="audit", default=True, type=bool),
#     ]
# )
# def task_export(notebooks, audit):
#     """export html versions of notebooks"""
#     rel = []
#     for format in ("html", "html5"):
#         for notebook in map(Path, notebooks):
#             target = notebook.with_suffix(notebook.suffix + f".{format}.html")
#             output = DOCS / target
#             if notebook.suffix in {".html"}:
#                 yield dict(
#                     name=f"html:{format}:{notebook}",
#                     actions=[(fix_html, (notebook, output))],
#                     targets=[output],
#                     file_dep=[notebook],
#                 )
#             else:
#                 cmd = f"jupyter nbconvert --to={format} --output={target.name} --output-dir={output.parent} {notebook}"
#                 yield dict(
#                     name=f"html:{format}:{notebook}",
#                     actions=[cmd],
#                     targets=[output],
#                     file_dep=[notebook],
#                 )
#             rel.append(output)

#         rel_targets = [x.parent / "data" / ("axe-" + x.name + ".json") for x in rel]
#     if audit:
#         from nbconvert_html5.audit import main

#         yield dict(
#             name=f"audit",
#             actions=[partial(main, id=rel)],
#             targets=rel_targets,
#             file_dep=rel,
#         )

#     INDEX = DOCS / "index.md"
#     body = "# sample converted notebooks\n\n"
#     for id in rel:
#         id = id.relative_to("docs")
#         body += "* "
#         body += f"[original](https://github.com/Iota-School/notebooks-for-all/blob/main/{id}) "
#         body += f"[html](/notebooks-for-all/{id}) "
#         body += str(id)
#         body += "\n"
#     yield dict(
#         name=f"export_html:{INDEX}",
#         targets=[INDEX],
#         actions=[(lambda x: INDEX.write_text(x) and None, [body])],
#     )
