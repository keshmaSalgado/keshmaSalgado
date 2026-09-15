import base64
from io import BytesIO
import os
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"

USERNAME = os.getenv("USER_NAME", "keshmaSalgado")
DISPLAY_NAME = os.getenv("DISPLAY_NAME", "Keshma Salgado")
TOKEN = os.getenv("ACCESS_TOKEN")

EMAIL = os.getenv("PROFILE_EMAIL", "keshmasalgado@gmail.com")
LINKEDIN = os.getenv("PROFILE_LINKEDIN", "linkedin.com/in/keshmasalgado")
DISCORD = os.getenv("PROFILE_DISCORD", "keshmaSalgado")

FONT = "JetBrains Mono, Consolas, Liberation Mono, monospace"
def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def portrait_data_uri(path):
    image = Image.open(path).convert("RGB")
    w, h = image.size

    # Use the real portrait as the main visual; the blue monochrome treatment
    # keeps the terminal mood without making the face hard to read.
    crop = (
        int(w * 0.19),
        int(h * 0.02),
        int(w * 0.95),
        int(h * 0.92),
    )
    image = image.crop(crop)
    image = ImageOps.fit(image, (520, 760), method=Image.Resampling.LANCZOS, centering=(0.52, 0.44))

    mono = ImageOps.grayscale(image)
    mono = ImageOps.autocontrast(mono, cutoff=1)
    mono = ImageEnhance.Contrast(mono).enhance(1.18)
    mono = ImageEnhance.Sharpness(mono).enhance(1.2)

    tinted = ImageOps.colorize(mono, black="#03101d", white="#b8dcff", mid="#3379ad")

    overlay = Image.new("RGB", tinted.size, "#03101d")
    tinted = Image.blend(overlay, tinted, 0.88)

    buffer = BytesIO()
    tinted.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def github(query, variables):
    if not TOKEN:
        raise RuntimeError("Set ACCESS_TOKEN before running the generator.")

    import requests

    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fallback_data():
    return {
        "name": DISPLAY_NAME,
        "login": USERNAME,
        "repos": 95,
        "commits": 2118,
        "stars": 342,
        "followers": 196,
    }


def get_github_data():
    if not TOKEN:
        return fallback_data()

    query = """
    query($login:String!) {
      user(login:$login) {
        name
        login
        followers { totalCount }
        repositories(ownerAffiliations:OWNER, first:100, orderBy:{field:STARGAZERS, direction:DESC}) {
          totalCount
          nodes { stargazerCount }
        }
        contributionsCollection {
          totalCommitContributions
        }
      }
    }
    """

    try:
        user = github(query, {"login": USERNAME})["user"]
        repos = user["repositories"]["nodes"]
        commits = user["contributionsCollection"]["totalCommitContributions"]

        return {
            "name": user["name"] or DISPLAY_NAME,
            "login": user["login"],
            "repos": user["repositories"]["totalCount"],
            "commits": commits,
            "stars": sum(repo["stargazerCount"] for repo in repos),
            "followers": user["followers"]["totalCount"],
        }
    except Exception as exc:
        print(f"GitHub API unavailable ({exc}); using profile preview data instead.")
        return fallback_data()


def text(x, y, value, size=16, fill="#dbeafe", weight="400", anchor="start", opacity=1):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'opacity="{opacity}">{esc(value)}</text>'
    )


def line(x1, y1, x2, y2, stroke="#2f77ad", width=1.5, dash=None, opacity=1):
    dash_part = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"{dash_part}/>'
    )


def rounded_rect(x, y, w, h, fill="#071423", stroke="#2f77ad", rx=8, opacity=1):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" opacity="{opacity}"/>'
    )


def pill(x, y, label, mark, color, width=None):
    label_width = len(label) * 8
    total = width or max(76, label_width + 44)
    parts = [
        rounded_rect(x, y - 20, total, 26, fill="#071a2b", stroke="#244b70", rx=6, opacity=0.96),
        f'<rect x="{x + 7}" y="{y - 16}" width="18" height="18" rx="4" fill="{color}"/>',
        text(x + 16, y - 2, mark, size=9, fill="#03101d", weight="800", anchor="middle"),
        text(x + 33, y - 2, label, size=13, fill="#e8f3ff"),
    ]
    return "\n".join(parts), total


def badge_row(items, x, y, gap=10):
    parts = []
    cursor = x
    for label, mark, color, width in items:
        badge, actual_width = pill(cursor, y, label, mark, color, width)
        parts.append(badge)
        cursor += actual_width + gap
    return "\n".join(parts)


def info_row(y, tag, label, value, extra=None):
    parts = [
        rounded_rect(600, y - 21, 28, 28, fill="#092033", stroke="#265b87", rx=6),
        text(614, y - 3, tag, size=10, fill="#58c7ff", weight="800", anchor="middle"),
        text(640, y - 2, f"{label}:", size=17, fill="#46b3ff", weight="700"),
        text(780, y - 2, value, size=17, fill="#f4f8ff"),
    ]
    if extra:
        for idx, item in enumerate(extra):
            parts.append(text(780, y + 27 + idx * 27, item, size=17, fill="#f4f8ff"))
    return "\n".join(parts)


def stat_card(x, y, value, label, mark, color):
    return "\n".join(
        [
            rounded_rect(x, y, 146, 82, fill="#071827", stroke="#2b638f", rx=7),
            rounded_rect(x + 18, y + 18, 22, 22, fill="#071827", stroke=color, rx=4),
            text(x + 29, y + 34, mark, size=13, fill=color, weight="800", anchor="middle"),
            text(x + 73, y + 49, f"{value:,}", size=22, fill="#e8f3ff", weight="800", anchor="middle"),
            text(x + 73, y + 71, label, size=13, fill="#c5d8ef", anchor="middle"),
        ]
    )


def build_svg(data, portrait_uri):
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1220" height="1280" viewBox="0 0 1220 1280">',
        "<defs>",
        '<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">',
        '<circle cx="2" cy="2" r="1" fill="#174363" opacity="0.28"/>',
        "</pattern>",
        '<radialGradient id="glow" cx="50%" cy="35%" r="70%">',
        '<stop offset="0%" stop-color="#10385a" stop-opacity="0.72"/>',
        '<stop offset="60%" stop-color="#04111f" stop-opacity="0.92"/>',
        '<stop offset="100%" stop-color="#010812" stop-opacity="1"/>',
        "</radialGradient>",
        "</defs>",
        '<rect width="1220" height="1280" fill="#010812"/>',
        '<rect width="1220" height="1280" fill="url(#glow)"/>',
        '<rect width="1220" height="1280" fill="url(#dots)"/>',
        rounded_rect(12, 10, 1196, 1260, fill="#03101d", stroke="#2e78ac", rx=8),
        text(40, 50, f"{USERNAME}@github:~", size=21, fill="#37f57a", weight="800"),
        '<rect x="313" y="32" width="11" height="24" fill="#dbeafe" opacity="0.95"/>',
        text(1175, 47, "< Software Engineer />", size=17, fill="#c7dfff", anchor="end"),
        "<clipPath id=\"portraitClip\">",
        '<rect x="35" y="78" width="532" height="790" rx="8"/>',
        "</clipPath>",
        '<image href="' + portrait_uri + '" x="35" y="78" width="532" height="790" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)" opacity="0.92"/>',
        '<rect x="35" y="78" width="532" height="790" rx="8" fill="url(#dots)" opacity="0.45"/>',
        '<rect x="35" y="78" width="532" height="790" rx="8" fill="none" stroke="#2f77ad" opacity="0.65"/>',
        '<rect x="35" y="78" width="532" height="790" rx="8" fill="#010812" opacity="0.10"/>',
        line(60, 828, 542, 828, stroke="#58c7ff", width=1, dash="5 7", opacity=0.7),
    ]

    parts.extend(
        [
            text(300, 884, '"Build ideas. Learn always.', size=18, fill="#b7d8ff", anchor="middle"),
            text(300, 912, 'Make an impact."', size=18, fill="#b7d8ff", anchor="middle"),
            line(279, 935, 321, 935, stroke="#58c7ff", width=2),
            rounded_rect(35, 965, 532, 284, fill="#061323", stroke="#2f77ad", rx=7),
            text(58, 1007, f"{USERNAME}@github:~$ cat about_me.txt", size=18, fill="#37f57a", weight="800"),
            text(65, 1049, "> Passionate about technology", size=17, fill="#e8f3ff"),
            text(65, 1082, "> Love building real-world projects", size=17, fill="#e8f3ff"),
            text(65, 1115, "> Always learning something new", size=17, fill="#e8f3ff"),
            text(65, 1148, "> Interested in AI, 3D, and creative tech", size=17, fill="#e8f3ff"),
            text(65, 1181, "> Open to collaboration and opportunities", size=17, fill="#e8f3ff"),
            text(58, 1219, f"{USERNAME}@github:~$ _", size=18, fill="#37f57a", weight="800"),
            text(600, 101, data["name"], size=34, fill="#f4f8ff", weight="800"),
            line(887, 65, 887, 106, stroke="#58c7ff", width=2.2),
            text(600, 132, "Software Engineer & Problem Solver", size=21, fill="#46b3ff"),
            line(600, 163, 1176, 163, stroke="#46b3ff", width=1.8, dash="6 5"),
            info_row(200, "OS", "OS", "Windows 10"),
            info_row(234, "PIN", "Location", "Colombo, Sri Lanka"),
            info_row(
                268,
                "EDU",
                "Education",
                "BSc (Hons) Software Engineering",
                ["Cardiff Metropolitan University", "(2025 - 2028)"],
            ),
            info_row(354, "GO", "Focus", "Full Stack Development | AI | Cloud"),
            info_row(388, "RUN", "Currently", "Building projects, learning & improving"),
            info_row(422, "FX", "Fun Fact", "Turning ideas into reality"),
            line(600, 454, 1176, 454, stroke="#46b3ff", width=1.8, dash="6 5"),
            text(600, 498, "Tech Stack", size=25, fill="#46b3ff", weight="800"),
            text(600, 536, "Languages", size=16, fill="#46b3ff", weight="800"),
            text(733, 536, ":", size=16, fill="#46b3ff", weight="800"),
            badge_row(
                [
                    ("JavaScript", "JS", "#f7df1e", 112),
                    ("TypeScript", "TS", "#3178c6", 120),
                    ("Python", "PY", "#ffd43b", 96),
                ],
                764,
                536,
            ),
            badge_row(
                [
                    ("Java", "JV", "#e76f00", 78),
                    ("Go", "GO", "#00add8", 68),
                    ("Dart", "DT", "#00b4ab", 78),
                ],
                764,
                570,
            ),
            text(600, 614, "Frontend", size=16, fill="#46b3ff", weight="800"),
            text(733, 614, ":", size=16, fill="#46b3ff", weight="800"),
            badge_row(
                [
                    ("React", "RX", "#61dafb", 88),
                    ("Next.js", "N", "#ffffff", 92),
                    ("Flutter", "FL", "#54c5f8", 96),
                ],
                764,
                614,
            ),
            badge_row(
                [
                    ("HTML5", "H5", "#e34f26", 86),
                    ("CSS3", "C3", "#1572b6", 76),
                    ("Tailwind CSS", "TW", "#38bdf8", 136),
                    ("Three.js", "3D", "#ffffff", 98),
                ],
                764,
                648,
            ),
            text(600, 692, "Backend", size=16, fill="#46b3ff", weight="800"),
            text(733, 692, ":", size=16, fill="#46b3ff", weight="800"),
            badge_row(
                [
                    ("Node.js", "ND", "#5fa04e", 96),
                    ("Express.js", "EX", "#ffffff", 114),
                    ("Django", "DJ", "#44b78b", 92),
                    ("FastAPI", "FA", "#009688", 98),
                ],
                764,
                692,
            ),
            text(600, 736, "Databases", size=16, fill="#46b3ff", weight="800"),
            text(733, 736, ":", size=16, fill="#46b3ff", weight="800"),
            badge_row(
                [
                    ("MongoDB", "MG", "#47a248", 102),
                    ("MySQL", "MY", "#4479a1", 86),
                    ("PostgreSQL", "PG", "#4169e1", 122),
                    ("SQLite", "SQ", "#74b9d6", 88),
                ],
                764,
                736,
            ),
            text(600, 780, "Cloud & Tools", size=16, fill="#46b3ff", weight="800"),
            text(733, 780, ":", size=16, fill="#46b3ff", weight="800"),
            badge_row(
                [
                    ("AWS", "AW", "#ff9900", 74),
                    ("Vercel", "VC", "#ffffff", 90),
                    ("Render", "RN", "#6d43ff", 90),
                    ("Git", "GT", "#f05032", 72),
                    ("GitHub", "GH", "#ffffff", 84),
                ],
                764,
                780,
            ),
            text(600, 824, "Others", size=16, fill="#46b3ff", weight="800"),
            text(733, 824, ":", size=16, fill="#46b3ff", weight="800"),
            badge_row(
                [
                    ("VS Code", "VS", "#007acc", 96),
                    ("Figma", "FG", "#a259ff", 86),
                    ("Postman", "PM", "#ff6c37", 104),
                    ("Docker", "DK", "#2496ed", 94),
                ],
                764,
                824,
            ),
            badge_row(
                [
                    ("Linux", "LX", "#f4ca16", 86),
                    ("Blender", "BL", "#f5792a", 100),
                    ("React Three Fiber", "R3", "#61dafb", 172),
                ],
                764,
                858,
            ),
            line(600, 905, 1176, 905, stroke="#46b3ff", width=1.8, dash="6 5"),
            text(600, 934, "Contact Me", size=25, fill="#46b3ff", weight="800"),
            info_row(970, "EM", "Email", EMAIL),
            info_row(1004, "IN", "LinkedIn", LINKEDIN),
            info_row(1038, "GH", "GitHub", f"github.com/{USERNAME}"),
            info_row(1072, "DC", "Discord", DISCORD),
            info_row(1106, "PF", "Portfolio", "Coming Soon..."),
            line(600, 1128, 1176, 1128, stroke="#46b3ff", width=1.8, dash="6 5"),
            text(600, 1160, "GitHub Stats", size=25, fill="#46b3ff", weight="800"),
            stat_card(600, 1177, data["repos"], "Repositories", "R", "#37f57a"),
            stat_card(754, 1177, data["commits"], "Commits", "C", "#58c7ff"),
            stat_card(908, 1177, data["stars"], "Stars", "S", "#ffbd59"),
            stat_card(1062, 1177, data["followers"], "Followers", "F", "#c084fc"),
            text(894, 1263, '"Consistency turns ideas into results."', size=14, fill="#c7dfff", anchor="middle"),
        ]
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    image = ASSETS / "profile.png"
    if not image.exists():
        raise FileNotFoundError("Put your image at assets/profile.png")

    portrait = portrait_data_uri(image)
    data = get_github_data()
    svg = build_svg(data, portrait)

    for filename in ("profile_dark.svg", "profile_light.svg"):
        (ASSETS / filename).write_text(svg, encoding="utf-8")

    print("Generated assets/profile_dark.svg and assets/profile_light.svg")
    if not TOKEN:
        print("No ACCESS_TOKEN was set; using profile preview data instead of live GitHub stats.")


if __name__ == "__main__":
    main()
