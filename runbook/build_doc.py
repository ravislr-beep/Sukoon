"""Build the runbook DOCX and PDF. Page numbers for the contents and lists come from a rendered PDF of the previous pass."""
import re
import subprocess
import sys
from pathlib import Path

from docx_lib import Builder
from refs import REFS
import content_a as A
import content_b as B
import content_c as C
import content_d as D
import content_e as E

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
NAME = "Pega_26_AKS_Kafka_Search_Runbook"
META = {"version": "1.0", "status": "Issued for customer review and approval", "date": "1 October 2026"}
TITLE = "Pega Platform 26.1.1 on Azure AKS: Externalized Kafka and Search Runbook"
SHORT = "Pega 26.1.1 on Azure AKS | Kafka and Search Runbook | v1.0"
TOC_LEVELS = 2

SECTIONS = [
    A.s1_exec, A.s2_scope, A.s3_evidence, A.s4_arch, A.s5_decisions, A.s6_aks,
    B.s7_kafka, B.s8_search, B.s9_secrets,
    C.s10_upgrade, C.s11_kafka_migration, C.s12_search_migration,
    D.s13_deploy, D.s14_cutover, D.s15_rollback, D.s16_testing, D.s17_troubleshooting,
    D.s18_ops, D.s19_dr, D.s20_raci, D.s21_risks, D.s22_open, D.s23_reconcile,
]


def build(labels, pages, entries, figures, tables):
    b = Builder(TITLE, SHORT, REFS, known_labels=labels)
    A.cover(b, META)
    A.document_control(b, META)
    b.toc(entries, pages)
    b.static_list("List of figures", figures, pages)
    b.static_list("List of tables", tables, pages)
    for s in SECTIONS:
        s(b)
    E.appendices(b)
    return b


def render(docx):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(docx)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = docx.with_suffix(".pdf")
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    return pdf, [re.sub(r"\s+", " ", t) for t in text.split("\f")]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def find_pages(page_texts, items):
    start = 0
    for i, t in enumerate(page_texts[:25]):
        if re.search(r"\.{8,}", t):
            start = i + 1
    found = {}
    for item in items:
        key = norm(item)[:60]
        for i in range(start, len(page_texts)):
            if key in page_texts[i]:
                found[item] = i + 1
                break
    return found


def main():
    OUT.mkdir(exist_ok=True)
    docx = OUT / f"{NAME}.docx"
    probe = build({}, {}, [], [], [])
    labels = probe.labels
    entries = [(lvl, lab) for lvl, lab in probe.headings if lvl <= TOC_LEVELS]
    figures, tables = probe.figures, probe.tables
    items = [lab for _, lab in entries] + figures + tables
    pages = {}
    for attempt in range(4):
        b = build(labels, pages, entries, figures, tables)
        b.save(docx)
        pdf, texts = render(docx)
        new_pages = find_pages(texts, items)
        missing = [i for i in items if i not in new_pages]
        if new_pages == pages and not missing:
            break
        pages = new_pages
    print(f"pages={len(texts)} headings={len(b.headings)} figures={b.fig_no} tables={b.tab_no} passes={attempt + 1}")
    if missing:
        print("NOT FOUND:", *missing, sep="\n  ")
    uncited = sorted(set(REFS) - b.cited, key=lambda k: int(k[1:]))
    if uncited:
        print("Uncited references:", ", ".join(uncited))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
