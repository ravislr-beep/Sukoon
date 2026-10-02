"""Draw the target architecture diagram on an explicit grid with Pillow.

Graphviz cannot keep the Azure boundary layout readable for this picture, so
the boxes are placed by coordinates. Run: python3 draw_architecture.py
"""
import math
import pathlib

from PIL import Image, ImageDraw, ImageFont

OUT = pathlib.Path(__file__).parent / "img" / "generated" / "fig_target_architecture.png"
FONT_DIR = "/usr/share/fonts/truetype/liberation/"
S = 2  # supersampling factor for smooth lines

W, H = 2480, 1640
NAVY = (31, 56, 100)
GREY = (89, 89, 89)
LINE = (68, 84, 106)
PEGA = (220, 230, 242)
BACK = (228, 223, 236)
EXT = (226, 239, 218)
AZ = (242, 242, 242)
SEC = (252, 228, 214)
ORANGE = (197, 90, 17)
PURPLE = (112, 48, 160)
GREEN = (84, 130, 53)

img = Image.new("RGB", (W * S, H * S), "white")
d = ImageDraw.Draw(img)


def font(size, bold=False):
    name = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    return ImageFont.truetype(FONT_DIR + name, size * S)


F_BOX = font(19)
F_BOX_B = font(19, True)
F_BND = font(18, True)
F_LBL = font(16)


def sc(*v):
    return [x * S for x in v]


def dashed_rect(x0, y0, x1, y1, color, dash=14, gap=9, width=2):
    for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        length = math.hypot(bx - ax, by - ay)
        n = int(length // (dash + gap)) + 1
        for i in range(n):
            s = i * (dash + gap)
            e = min(s + dash, length)
            if s >= length:
                break
            fx, fy = ax + (bx - ax) * s / length, ay + (by - ay) * s / length
            tx, ty = ax + (bx - ax) * e / length, ay + (by - ay) * e / length
            d.line(sc(fx, fy, tx, ty), fill=color, width=width * S)


def boundary(x0, y0, x1, y1, label, color=GREY, solid=False):
    if solid:
        d.rounded_rectangle(sc(x0, y0, x1, y1), radius=14 * S, outline=color, width=2 * S)
    else:
        dashed_rect(x0, y0, x1, y1, color)
    d.text(sc(x0 + 14, y0 + 8), label, font=F_BND, fill=color)


def box(x0, y0, x1, y1, lines, fill, bold_first=True):
    d.rounded_rectangle(sc(x0, y0, x1, y1), radius=12 * S, fill=fill, outline=LINE, width=2 * S)
    fonts = [F_BOX_B if (i == 0 and bold_first) else F_BOX for i in range(len(lines))]
    heights = [d.textbbox((0, 0), t, font=f)[3] for t, f in zip(lines, fonts)]
    total = sum(heights) + (len(lines) - 1) * 6 * S
    y = ((y0 + y1) * S - total) / 2
    for t, f, h in zip(lines, fonts, heights):
        w = d.textlength(t, font=f)
        d.text((((x0 + x1) * S - w) / 2, y), t, font=f, fill=(0, 0, 0))
        y += h + 6 * S
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def arrow(points, color=LINE, label=None, label_at=0, label_dx=8, label_dy=-24, dashed=False, both=False, label_pos=None):
    pts = [(x * S, y * S) for x, y in points]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if dashed:
            length = math.hypot(bx - ax, by - ay)
            step = 12 * S
            i = 0
            while i * step < length:
                s, e = i * step, min(i * step + 7 * S, length)
                d.line((ax + (bx - ax) * s / length, ay + (by - ay) * s / length,
                        ax + (bx - ax) * e / length, ay + (by - ay) * e / length), fill=color, width=2 * S)
                i += 1
        else:
            d.line((ax, ay, bx, by), fill=color, width=int(2.2 * S))

    def head(p_from, p_to):
        (ax, ay), (bx, by) = p_from, p_to
        ang = math.atan2(by - ay, bx - ax)
        size = 13 * S
        left = (bx - size * math.cos(ang - 0.42), by - size * math.sin(ang - 0.42))
        right = (bx - size * math.cos(ang + 0.42), by - size * math.sin(ang + 0.42))
        d.polygon([(bx, by), left, right], fill=color)

    head(pts[-2], pts[-1])
    if both:
        head(pts[1], pts[0])
    if label:
        if label_pos:
            lx, ly = label_pos
        else:
            lx, ly = points[label_at]
            lx, ly = lx + label_dx, ly + label_dy
        bb = d.textbbox((lx * S, ly * S), label, font=F_LBL)
        d.rectangle((bb[0] - 3 * S, bb[1] - 2 * S, bb[2] + 3 * S, bb[3] + 2 * S), fill="white")
        d.text((lx * S, ly * S), label, font=F_LBL, fill=color)


# Boundaries
boundary(250, 40, 1650, 1600, "Spoke VNet  (Customer subscription, primary Azure region, 3 availability zones)", NAVY)
boundary(560, 90, 1190, 1150, "Private AKS cluster  (system, pega and srs node pools)", NAVY, solid=True)
boundary(585, 135, 1165, 560, "namespace: pega   (Pega Helm chart)")
boundary(585, 600, 1165, 800, "namespace: srs   (backingservices Helm chart)")
boundary(585, 840, 1165, 1120, "namespace: platform-ops")
boundary(1270, 135, 1620, 1120, "Private endpoint subnet")
boundary(285, 1190, 1620, 1570, "Hub services reached from the spoke  (peered hub VNet)")
boundary(1720, 135, 2440, 330, "Confluent Cloud  (Azure, same region)", GREEN)
boundary(1720, 380, 2440, 560, "Azure PaaS: Pega database", GREY)
boundary(1720, 600, 2440, 800, "Managed OpenSearch  (provider to be selected)", GREEN)
boundary(1720, 840, 2440, 1120, "Azure PaaS: secrets and images", GREY)
boundary(1720, 1190, 2440, 1570, "Okta  (SaaS, reached through the firewall)", GREY)

# Boxes
users = box(20, 640, 165, 740, ["Users and", "API clients"], "white")
agw = box(300, 620, 520, 760, ["Application", "Gateway WAF v2", "+ ingress controller"], AZ)
web = box(615, 190, 860, 320, ["Web tier", "nodeType WebUser", "HPA on CPU, PDB"], PEGA)
batch = box(895, 190, 1140, 360, ["Batch tier", "BackgroundProcessing,", "Search, Batch,", "RealTime, Custom1-5"], PEGA)
inst = box(615, 420, 860, 530, ["Installer job", "install / upgrade only"], PEGA)
srs = box(760, 650, 1000, 770, ["Search and Reporting", "Service (3 replicas)", "no ingress"], BACK)
eso = box(615, 900, 860, 1000, ["External Secrets", "Operator"], SEC)
mon = box(895, 900, 1140, 1000, ["Azure Monitor agent", "Container Insights"], AZ)
pek = box(1300, 185, 1590, 285, ["Private endpoints", "Confluent, one per zone"], EXT)
ped = box(1300, 420, 1590, 520, ["Private endpoint", "database"], AZ)
pes = box(1300, 650, 1590, 750, ["Private endpoint", "search service"], EXT)
pev = box(1300, 900, 1590, 1000, ["Private endpoints", "Key Vault, ACR"], AZ)
kafka = box(1830, 180, 2330, 300, ["Kafka cluster", "Enterprise or Dedicated", "RF 3, ACLs on topic prefix"], EXT)
db = box(1830, 425, 2330, 530, ["Upgraded clone of the 8.8", "database (rules and data)"], AZ)
search = box(1830, 645, 2330, 770, ["OpenSearch (SRS matrix version)", "3 cluster-manager +", "3 or more data nodes"], EXT)
kv = box(1760, 900, 2070, 1000, ["Azure Key Vault"], SEC)
acr = box(2110, 900, 2410, 1000, ["Container Registry", "scanned Pega images"], AZ)
fw = box(330, 1260, 640, 1360, ["Azure Firewall", "egress control"], AZ)
dns = box(700, 1260, 1010, 1360, ["Private DNS zones", "linked to spoke VNet"], AZ)
law = box(1070, 1260, 1380, 1360, ["Log Analytics,", "Azure Monitor, SIEM"], AZ)
idp = box(1830, 1260, 2330, 1380, ["Okta custom authorization", "server: token and JWKS", "for Pega to SRS"], SEC)

# Flows
arrow([(165, 690), (300, 690)], label="HTTPS 443", label_pos=(190, 662))
arrow([(520, 660), (540, 660), (540, 255), (615, 255)], label="HTTPS,", label_pos=(470, 500))
_bb = d.textbbox(sc(440, 522), "backend TLS", font=F_LBL)
d.rectangle((_bb[0] - 6, _bb[1] - 4, _bb[2] + 6, _bb[3] + 4), fill="white")
d.text(sc(440, 522), "backend TLS", font=F_LBL, fill=LINE)
arrow([(1140, 230), (1300, 230)], ORANGE, "SASL_SSL 9092", label_pos=(1150, 238))
arrow([(860, 205), (880, 205), (880, 160), (1240, 160), (1240, 205), (1300, 205)], ORANGE)
arrow([(1590, 235), (1830, 235)], ORANGE, "Private Link", label_dx=60)
arrow([(1140, 330), (1220, 330), (1220, 470), (1300, 470)], LINE, "JDBC over TLS", label_pos=(1228, 372))
arrow([(1590, 470), (1830, 470)], LINE)
arrow([(740, 320), (740, 600), (840, 600), (840, 650)], PURPLE, "HTTP(S) + OAuth bearer", label_at=1, label_dx=8, label_dy=-30)
arrow([(1015, 360), (1015, 600), (930, 600), (930, 650)], PURPLE)
arrow([(1000, 700), (1300, 700)], GREEN, "HTTPS, TLS", label_dx=120)
arrow([(1590, 700), (1830, 700)], GREEN, "HTTPS 443", label_dx=60)
arrow([(860, 975), (880, 975), (880, 1070), (1250, 1070), (1250, 950), (1300, 950)], LINE, "workload identity", label_at=2, label_dx=20, label_dy=-28, dashed=True)
arrow([(1590, 950), (1760, 950)], LINE, dashed=True)
arrow([(1590, 975), (1680, 975), (1680, 1040), (2260, 1040), (2260, 1000)], LINE, "image pull", label_at=2, label_dx=-180, label_dy=-26, dashed=True)
arrow([(1015, 1000), (1015, 1180), (1225, 1180), (1225, 1260)], LINE, "logs and metrics", label_at=2, label_dx=10, label_dy=-26, dashed=True)
arrow([(615, 290), (575, 290), (575, 1150), (485, 1150), (485, 1260)], LINE, "egress via firewall", label_at=3, label_dx=-200, label_dy=-30, dashed=True)
arrow([(640, 1310), (680, 1310), (680, 1585), (2080, 1585), (2080, 1380)], LINE, "token request", label_pos=(1700, 1550), dashed=True)

# Legend
lx, ly = 30, 1400
d.text(sc(lx, ly - 34), "Legend", font=F_BND, fill=NAVY)
for i, (c, t) in enumerate([(LINE, "Request / data"), (ORANGE, "Kafka stream"), (PURPLE, "Pega to SRS"), (GREEN, "SRS to search")]):
    y = ly + i * 32
    d.line(sc(lx, y + 10, lx + 50, y + 10), fill=c, width=3 * S)
    d.text(sc(lx + 60, y), t, font=F_LBL, fill=GREY)

img = img.resize((W, H), Image.LANCZOS)
img.save(OUT, dpi=(220, 220))
print("wrote", OUT)
