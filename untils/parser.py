from requests import request
from bs4 import BeautifulSoup

SITE_URL = "https://www.ztoe.com.ua/unhooking-search.php"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def parse(queue: int, legacy = True):
    if legacy:
        queue = max(0, min(queue, 1))
    else:
        queue = to_index(queue)

    html = request(url=SITE_URL, method="GET", timeout=15, headers=headers).text
    soup = BeautifulSoup(html, "html.parser")
    if legacy:
        text = soup.find_all("table")[3].select("tr")[6+queue].select("td")[2:]
    else:
        text = soup.find_all("table")[3].select("tr")[2+queue].select("td")[2:]

    status = []
    colors = []

    for i in text:
        t = str(i)
        color = t.split(";")[5].split(">", maxsplit=1)[0].replace('"', "").split(sep=":", maxsplit=1)[1]
        color = color.split()[0]
        colors.append(color)

    for c in colors:
        if c == "#ffffff":
            status.append(0)
        else:
            status.append(1)

    return status

def to_index(n: int) -> int:
    x = n // 10
    y = n % 10
    return (x - 1) * 2 + y