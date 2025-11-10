from requests import request
from bs4 import BeautifulSoup

SITE_URL = "https://www.ztoe.com.ua/unhooking-search.php"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def parse():
    html = request(url=SITE_URL, method="GET", timeout=5, headers=headers).text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.find_all("table")[3].select("tr")[6].select("td")[3:]

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