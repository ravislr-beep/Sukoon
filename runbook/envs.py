"""Per-environment naming used in every table, diagram and values file."""

ENVS = [
    # name, code, service group
    ("DEV", "dev", "NP1"),
    ("SIT", "sit", "NP1"),
    ("UAT", "uat", "NP1"),
    ("PERF", "perf", "NP2"),
    ("PREPROD", "ppd", "NP2"),
    ("PROD", "prd", "PRD"),
]
NAMES = [e[0] for e in ENVS]
CODES = [e[1] for e in ENVS]

GROUPS = {
    "NP1": ("Shared group NP1 (functional)", "DEV, SIT, UAT", "cc-np1", "os-np1"),
    "NP2": ("Shared group NP2 (production-like)", "PERF, PREPROD", "cc-np2", "os-np2"),
    "PRD": ("Production (dedicated)", "PROD", "cc-prd", "os-prd"),
}


def per_env(fn):
    return [fn(name, code, grp) for name, code, grp in ENVS]


def prefix(code):
    return f"pega-{code}-"


def pattern(code):
    return f"pega-{code}-{{stream.name}}"


def deployment_id(code):
    return f"pega26-{code}"


def cluster(grp):
    return GROUPS[grp][2]


def search(grp):
    return GROUPS[grp][3]
