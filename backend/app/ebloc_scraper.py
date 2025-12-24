import httpx
from bs4 import BeautifulSoup
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EblocBill:
    month: str
    amount: float
    due_date: Optional[datetime]
    details_url: Optional[str]
    iban: Optional[str] = None
    bill_number: Optional[str] = None


@dataclass
class EblocProperty:
    page_id: str
    name: str
    url: str


class EblocScraper:
    BASE_URL = "https://www.e-bloc.ro"
    LOGIN_URL = f"{BASE_URL}/index.php"

    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
        self.logged_in = False
        self.available_properties: list[EblocProperty] = []

    async def login(self, username: str, password: str) -> bool:
        try:
            login_page = await self.client.get(self.LOGIN_URL)
            soup = BeautifulSoup(login_page.text, "html.parser")
            form = soup.find("form")
            form_data = {}
            if form:
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        form_data[name] = inp.get("value", "")
            form_data["user"] = username
            form_data["pass"] = password
            if "email" in form_data:
                form_data["email"] = username
            if "password" in form_data:
                form_data["password"] = password
            response = await self.client.post(self.LOGIN_URL, data=form_data)
            self.logged_in = response.status_code == 200 and "index.php" in str(response.url)
            if self.logged_in:
                await self._parse_property_selector(response.text)
            return self.logged_in
        except Exception:
            return False

    async def _parse_property_selector(self, html: str) -> None:
        soup = BeautifulSoup(html, "html.parser")
        self.available_properties = []
        select = soup.find("select") or soup.find("select", {"id": "property"})
        if select:
            for option in select.find_all("option"):
                value = option.get("value", "")
                name = option.get_text(strip=True)
                if value and name:
                    url = f"{self.LOGIN_URL}?page={value}&t={int(datetime.now().timestamp())}"
                    self.available_properties.append(EblocProperty(page_id=value, name=name, url=url))
        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            if "page=" in href:
                import re
                match = re.search(r'page=(\d+)', href)
                if match:
                    page_id = match.group(1)
                    name = link.get_text(strip=True) or f"Property {page_id}"
                    if not any(p.page_id == page_id for p in self.available_properties):
                        url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
                        self.available_properties.append(EblocProperty(page_id=page_id, name=name, url=url))

    async def get_available_properties(self) -> list[EblocProperty]:
        return self.available_properties

    async def select_property(self, page_id: str) -> bool:
        try:
            url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    async def get_bills(self, page_id: Optional[str] = None) -> list[EblocBill]:
        if not self.logged_in:
            return []
        try:
            if page_id:
                url = f"{self.LOGIN_URL}?page={page_id}&t={int(datetime.now().timestamp())}"
            else:
                url = self.LOGIN_URL
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            bills = []
            bill_rows = soup.find_all("tr", class_="bill-row") or soup.find_all(
                "div", class_="bill-item"
            )
            for row in bill_rows:
                month_el = row.find(class_="month") or row.find("td", {"data-label": "Luna"})
                amount_el = row.find(class_="amount") or row.find("td", {"data-label": "Suma"})
                due_el = row.find(class_="due-date") or row.find("td", {"data-label": "Scadenta"})
                link_el = row.find("a", href=True)
                month = month_el.get_text(strip=True) if month_el else "Unknown"
                amount_text = amount_el.get_text(strip=True) if amount_el else "0"
                amount = float(
                    amount_text.replace("lei", "").replace("RON", "").replace(",", ".").strip()
                    or "0"
                )
                due_text = due_el.get_text(strip=True) if due_el else None
                due_date = None
                if due_text:
                    try:
                        due_date = datetime.strptime(due_text, "%d.%m.%Y")
                    except ValueError:
                        pass
                details_url = link_el.get("href") if link_el else None
                if details_url and not details_url.startswith("http"):
                    details_url = f"{self.BASE_URL}{details_url}"
                bills.append(
                    EblocBill(
                        month=month,
                        amount=amount,
                        due_date=due_date,
                        details_url=details_url,
                    )
                )
            return bills
        except Exception:
            return []

    async def get_bill_details(self, details_url: str) -> Optional[EblocBill]:
        if not self.logged_in or not details_url:
            return None
        try:
            response = await self.client.get(details_url)
            soup = BeautifulSoup(response.text, "html.parser")
            iban_el = soup.find(string=lambda t: t and "IBAN" in t if t else False)
            iban = None
            if iban_el:
                parent = iban_el.find_parent()
                if parent:
                    iban_text = parent.get_text()
                    import re

                    iban_match = re.search(r"[A-Z]{2}\d{2}[A-Z0-9]{4,30}", iban_text)
                    iban = iban_match.group(0) if iban_match else None
            bill_num_el = soup.find(string=lambda t: t and "Nr." in t if t else False)
            bill_number = None
            if bill_num_el:
                parent = bill_num_el.find_parent()
                if parent:
                    bill_number = parent.get_text(strip=True)
            return EblocBill(
                month="",
                amount=0,
                due_date=None,
                details_url=details_url,
                iban=iban,
                bill_number=bill_number,
            )
        except Exception:
            return None

    async def close(self):
        await self.client.aclose()
