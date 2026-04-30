from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..config import settings

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_report(job_id: str, context: dict) -> str:
    template = env.get_template("report.html.j2")
    html = template.render(**context)
    out = settings.reports_dir / f"{job_id}.html"
    out.write_text(html, encoding="utf-8")
    return str(out)
