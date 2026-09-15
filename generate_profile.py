import os
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
USERNAME = os.getenv("USER_NAME", "keshmaSalgado")
TOKEN = os.getenv("ACCESS_TOKEN")

# ASCII settings
CHARS = "@%#*+=-:. "

def ascii_portrait(path, width=48):
    image = Image.open(path).convert("L")
    w, h = image.size

    # Keep the face/upper body and correct terminal-character aspect ratio.
    image = image.crop((0, 0, w, int(h * 0.94)))
    height = max(1, int(image.height / image.width * width * 0.43))
    image = image.resize((width, height))

    lines = []
    for y in range(image.height):
        row = []
        for x in range(image.width):
            p = image.getpixel((x, y))
            row.append(CHARS[p * (len(CHARS) - 1) // 255])
        lines.append("".join(row).rstrip())
    return lines

def github(query, variables):
    if not TOKEN:
        raise RuntimeError("Set ACCESS_TOKEN before running the generator.")
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

def get_github_data():
    query = """
    query($login:String!) {
      user(login:$login) {
        name
        login
        createdAt
        followers { totalCount }
        repositories(ownerAffiliations:OWNER, first:100) {
          totalCount
          nodes { stargazerCount }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                weekday
              }
            }
          }
        }
      }
    }
    """
    user = github(query, {"login": USERNAME})["user"]
    repos = user["repositories"]["nodes"]
    calendar = user["contributionsCollection"]["contributionCalendar"]

    return {
        "name": user["name"] or USERNAME,
        "login": user["login"],
        "created": user["createdAt"][:10],
        "repos": user["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": user["followers"]["totalCount"],
        "contributions": calendar["totalContributions"],
        "weeks": calendar["weeks"],
    }

def esc(value):
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def streaks(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda x: x["date"])

    longest = current = 0
    for d in days:
        if d["contributionCount"] > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    trailing = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            trailing += 1
        else:
            break
    return trailing, longest

def heatmap(weeks, dark):
    colors = (
        ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
        if dark else
        ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
    )
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    maximum = max(counts or [0])

    def level(n):
        if n == 0 or maximum == 0:
            return 0
        ratio = n / maximum
        return 1 if ratio <= .25 else 2 if ratio <= .5 else 3 if ratio <= .75 else 4

    parts = []
    last_month = None
    delay = 0.0

    for wi, week in enumerate(weeks):
        x = 610 + wi * 9
        if week["contributionDays"]:
            month = int(week["contributionDays"][0]["date"][5:7])
            if month != last_month:
                parts.append(
                    f'<text x="{x}" y="388" class="month">{["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][month-1]}</text>'
                )
                last_month = month

        for day in week["contributionDays"]:
            y = 397 + day["weekday"] * 9
            n = day["contributionCount"]
            title = f'{n} contribution{"s" if n != 1 else ""} on {day["date"]}'
            parts.append(
                f'<rect x="{x}" y="{y}" width="7" height="7" rx="1.5" fill="{colors[level(n)]}" opacity="0">'
                f'<title>{esc(title)}</title>'
                f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" dur=".25s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" from="0,-3" to="0,0" begin="{delay:.3f}s" dur=".25s" fill="freeze"/>'
                f'</rect>'
            )
        delay += .012

    parts += [
        '<text x="610" y="468" class="dow">Mon</text>',
        '<text x="610" y="486" class="dow">Wed</text>',
        '<text x="610" y="504" class="dow">Fri</text>',
    ]
    return "\n".join(parts)

def build_svg(data, portrait, dark):
    bg = "#0d1117" if dark else "#ffffff"
    panel = "#161b22" if dark else "#f6f8fa"
    text = "#e6edf3" if dark else "#24292f"
    muted = "#8b949e" if dark else "#57606a"
    border = "#30363d" if dark else "#d0d7de"
    accent = "#58a6ff" if dark else "#0969da"
    green = "#3fb950" if dark else "#1a7f37"
    amber = "#d29922" if dark else "#9a6700"

    current, longest = streaks(data["weeks"])

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">',
        f'<rect width="1200" height="760" rx="20" fill="{bg}"/>',
        f'<rect x="14" y="14" width="1172" height="732" rx="16" fill="{bg}" stroke="{border}"/>',

        f'<text x="42" y="50" font-family="monospace" font-size="18" fill="{green}">{esc(USERNAME)}@github:~$</text>',
        f'<text x="1155" y="50" text-anchor="end" font-family="monospace" font-size="17" fill="{muted}">&lt; /software-engineer &gt;</text>',
        f'<line x1="42" y1="70" x2="1158" y2="70" stroke="{border}"/>',

        # Left terminal portrait
        f'<rect x="35" y="90" width="515" height="600" rx="12" fill="{panel}" stroke="{border}"/>',
        f'<text x="55" y="120" font-family="monospace" font-size="14" fill="{muted}">keshmaSalgado@github:~$ cat profile.txt</text>',
    ]

    y = 145
    for line in portrait:
        svg.append(
            f'<text x="65" y="{y}" font-family="monospace" font-size="11" fill="{text}" xml:space="preserve">{esc(line)}</text>'
        )
        y += 11

    svg += [
        f'<line x1="65" y1="600" x2="520" y2="600" stroke="{border}"/>',
        f'<text x="65" y="628" font-family="monospace" font-size="13" fill="{accent}">"Build ideas. Learn always. Make an impact."</text>',
        f'<text x="65" y="660" font-family="monospace" font-size="13" fill="{green}">keshmaSalgado@github:~$ _</text>',

        # Right profile
        f'<text x="590" y="112" font-family="monospace" font-size="28" font-weight="bold" fill="{text}">{esc(data["name"])}</text>',
        f'<text x="590" y="140" font-family="monospace" font-size="17" fill="{accent}">Software Engineer &amp; Problem Solver</text>',
        f'<line x1="590" y1="160" x2="1158" y2="160" stroke="{accent}"/>',

        f'<text x="590" y="188" font-family="monospace" font-size="13" fill="{accent}">OS</text>',
        f'<text x="735" y="188" font-family="monospace" font-size="13" fill="{text}">Windows / Linux</text>',
        f'<text x="590" y="214" font-family="monospace" font-size="13" fill="{accent}">Location</text>',
        f'<text x="735" y="214" font-family="monospace" font-size="13" fill="{text}">Colombo, Sri Lanka</text>',
        f'<text x="590" y="240" font-family="monospace" font-size="13" fill="{accent}">Education</text>',
        f'<text x="735" y="240" font-family="monospace" font-size="13" fill="{text}">Software Engineering</text>',
        f'<text x="590" y="266" font-family="monospace" font-size="13" fill="{accent}">Focus</text>',
        f'<text x="735" y="266" font-family="monospace" font-size="13" fill="{text}">Full Stack | AI | Cloud</text>',
        f'<text x="590" y="292" font-family="monospace" font-size="13" fill="{accent}">Currently</text>',
        f'<text x="735" y="292" font-family="monospace" font-size="13" fill="{text}">Building projects &amp; learning</text>',

        f'<line x1="590" y1="315" x2="1158" y2="315" stroke="{border}"/>',
        f'<text x="590" y="345" font-family="monospace" font-size="20" font-weight="bold" fill="{accent}">Tech Stack</text>',
        f'<text x="590" y="370" font-family="monospace" font-size="12" fill="{accent}">Languages</text>',
        f'<text x="720" y="370" font-family="monospace" font-size="12" fill="{text}">JavaScript • TypeScript • Python • Java • Go • Dart</text>',
        f'<text x="590" y="393" font-family="monospace" font-size="12" fill="{accent}">Frontend</text>',
        f'<text x="720" y="393" font-family="monospace" font-size="12" fill="{text}">React • Next.js • Flutter • Tailwind • Three.js</text>',
        f'<text x="590" y="416" font-family="monospace" font-size="12" fill="{accent}">Backend</text>',
        f'<text x="720" y="416" font-family="monospace" font-size="12" fill="{text}">Node.js • Express • Django • FastAPI</text>',
        f'<text x="590" y="439" font-family="monospace" font-size="12" fill="{accent}">Database</text>',
        f'<text x="720" y="439" font-family="monospace" font-size="12" fill="{text}">MongoDB • MySQL • PostgreSQL • SQLite</text>',
        f'<text x="590" y="462" font-family="monospace" font-size="12" fill="{accent}">Tools</text>',
        f'<text x="720" y="462" font-family="monospace" font-size="12" fill="{text}">AWS • Git • GitHub • Docker • Figma • Blender</text>',

        f'<line x1="590" y1="480" x2="1158" y2="480" stroke="{border}"/>',
        f'<text x="590" y="510" font-family="monospace" font-size="20" font-weight="bold" fill="{accent}">GitHub Activity</text>',
    ]

    # Heatmap
    svg.append(heatmap(data["weeks"], dark))
    svg += [
        f'<text x="590" y="540" font-family="monospace" font-size="11" fill="{muted}">{data["contributions"]:,} contributions in the last year</text>',
        f'<text x="590" y="562" font-family="monospace" font-size="11" fill="{muted}">Current streak: {current} days  •  Longest streak: {longest} days</text>',

        f'<rect x="590" y="580" width="130" height="72" rx="8" fill="{panel}" stroke="{border}"/>',
        f'<rect x="735" y="580" width="130" height="72" rx="8" fill="{panel}" stroke="{border}"/>',
        f'<rect x="880" y="580" width="130" height="72" rx="8" fill="{panel}" stroke="{border}"/>',
        f'<rect x="1025" y="580" width="130" height="72" rx="8" fill="{panel}" stroke="{border}"/>',

        f'<text x="655" y="612" text-anchor="middle" font-family="monospace" font-size="21" font-weight="bold" fill="{accent}">{data["repos"]}</text>',
        f'<text x="800" y="612" text-anchor="middle" font-family="monospace" font-size="21" font-weight="bold" fill="{accent}">{data["stars"]}</text>',
        f'<text x="945" y="612" text-anchor="middle" font-family="monospace" font-size="21" font-weight="bold" fill="{accent}">{data["followers"]}</text>',
        f'<text x="1090" y="612" text-anchor="middle" font-family="monospace" font-size="21" font-weight="bold" fill="{amber}">{data["contributions"]}</text>',

        f'<text x="655" y="636" text-anchor="middle" font-family="monospace" font-size="10" fill="{muted}">Repositories</text>',
        f'<text x="800" y="636" text-anchor="middle" font-family="monospace" font-size="10" fill="{muted}">Stars</text>',
        f'<text x="945" y="636" text-anchor="middle" font-family="monospace" font-size="10" fill="{muted}">Followers</text>',
        f'<text x="1090" y="636" text-anchor="middle" font-family="monospace" font-size="10" fill="{muted}">Contributions</text>',

        f'<text x="590" y="682" font-family="monospace" font-size="12" fill="{green}">keshmaSalgado@github:~$ ./contact.sh</text>',
        f'<text x="590" y="704" font-family="monospace" font-size="11" fill="{muted}">GitHub: github.com/keshmaSalgado  •  LinkedIn: YOUR_LINK  •  Email: YOUR_EMAIL</text>',
        '</svg>'
    ]
    return "\n".join(svg)

def main():
    image = ASSETS / "profile.png"
    if not image.exists():
        raise FileNotFoundError("Put your image at assets/profile.png")

    portrait = ascii_portrait(image)
    data = get_github_data()

    for mode in (True, False):
        filename = ASSETS / ("profile_dark.svg" if mode else "profile_light.svg")
        filename.write_text(build_svg(data, portrait, mode), encoding="utf-8")

    print("Generated assets/profile_dark.svg and assets/profile_light.svg")

if __name__ == "__main__":
    main()
