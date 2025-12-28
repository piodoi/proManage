"""
Hidroelectrica API client for fetching bills.
Based on: https://github.com/cnecrea/hidroelectrica/blob/main/custom_components/hidroelectrica/api.py
"""

import logging
import requests
import base64
import json
import urllib3
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# API Constants
API_BASE_URL = "https://hidroelectrica-svc.smartcmobile.com"
API_URL_GET_ID = f"{API_BASE_URL}/Service.asmx/GetId"
API_URL_VALIDATE_LOGIN = f"{API_BASE_URL}/Service.asmx/ValidateUserLogin"
API_URL_GET_USER_SETTING = f"{API_BASE_URL}/Service.asmx/GetUserSetting"
API_URL_GET_BILL = f"{API_BASE_URL}/Service.asmx/GetBill"
API_URL_GET_BILL_HISTORY = f"{API_BASE_URL}/Service.asmx/GetBillingHistoryList"


@dataclass
class HidroelectricaBill:
    """Represents a bill from Hidroelectrica"""
    utility_account_number: str
    account_number: str
    bill_number: Optional[str]
    amount: float
    due_date: Optional[datetime]
    issue_date: Optional[datetime]
    period_from: Optional[datetime]
    period_to: Optional[datetime]
    iban: Optional[str] = None
    address: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class HidroelectricaAccount:
    """Represents a utility account from Hidroelectrica"""
    account_number: str
    utility_account_number: str
    address: Optional[str]
    is_default: bool


class HidroelectricaAPI:
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

        self._user_id = None
        self._session_token = None
        self._auth_header = None
        self._token_id = None
        self._key = None
        self._utility_accounts: List[HidroelectricaAccount] = []

        # Requests session
        self._session = requests.Session()
        self._session.verify = False

    def login_if_needed(self) -> None:
        """Login only if _session_token is None."""
        if self._session_token:
            logger.debug("Already have session_token, skipping login")
            return
        self.login()

    def login(self) -> None:
        """
        Authentication sequence:
          1. API_URL_GET_ID (key + token_id)
          2. API_URL_VALIDATE_LOGIN (username/password)
          3. get_user_setting => accounts
        """
        logger.info(f"[Hidroelectrica] Starting login for user '{self._username}'")

        # 1. GetId
        resp_get_id = self._post_request(
            API_URL_GET_ID,
            payload={},
            headers={
                "SourceType": "0",
                "Content-Type": "application/json",
                "Host": "hidroelectrica-svc.smartcmobile.com",
                "User-Agent": "okhttp/4.9.0",
            },
            description="GetId"
        )
        self._key = resp_get_id["result"]["Data"]["key"]
        self._token_id = resp_get_id["result"]["Data"]["tokenId"]

        logger.debug(f"Got key={self._key[:10]}..., token_id={self._token_id}")

        # 2. Validate Login
        auth = base64.b64encode(f"{self._key}:{self._token_id}".encode()).decode()
        login_headers = {
            "SourceType": "0",
            "Content-Type": "application/json",
            "Host": "hidroelectrica-svc.smartcmobile.com",
            "User-Agent": "okhttp/4.9.0",
            "Authorization": f"Basic {auth}"
        }
        login_payload = {
            "deviceType": "MobileApp",
            "OperatingSystem": "Android",
            "UpdatedDate": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            "Deviceid": "",
            "SessionCode": "",
            "LanguageCode": "RO",
            "password": self._password,
            "UserId": self._username,
            "TFADeviceid": "",
            "OSVersion": 14,
            "TimeOffSet": "120",
            "LUpdHideShow": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            "Browser": "NA"
        }
        resp_login = self._post_request(
            API_URL_VALIDATE_LOGIN,
            payload=login_payload,
            headers=login_headers,
            description="ValidateUserLogin"
        )

        # Extract user data from Table
        table_data = resp_login["result"]["Data"].get("Table", [])
        if not table_data:
            raise Exception("Error: Missing 'Table' or empty in ValidateUserLogin")

        first_user_entry = table_data[0]
        self._user_id = first_user_entry["UserID"]
        self._session_token = first_user_entry["SessionToken"]

        logger.debug(f"UserID={self._user_id}, SessionToken={self._session_token[:20]}...")

        encoded_auth = base64.b64encode(f"{self._user_id}:{self._session_token}".encode()).decode()
        self._auth_header = {
            "SourceType": "1",
            "Content-Type": "application/json",
            "Host": "hidroelectrica-svc.smartcmobile.com",
            "User-Agent": "okhttp/4.9.0",
            "Authorization": f"Basic {encoded_auth}"
        }

        # 3. Get user accounts
        self._get_utility_accounts()

        logger.info(
            f"[Hidroelectrica] Login completed for '{self._username}'. Found {len(self._utility_accounts)} account(s)"
        )

    def _get_utility_accounts(self):
        """Call GetUserSetting, populate self._utility_accounts"""
        payload = {"UserID": self._user_id}
        resp = self._post_request(
            API_URL_GET_USER_SETTING,
            payload=payload,
            headers=self._auth_header,
            description="GetUserSetting"
        )

        data = resp["result"]["Data"]
        accounts = []
        if "Table1" in data and data["Table1"]:
            accounts.extend(data["Table1"])
        if "Table2" in data and data["Table2"]:
            for entry in data["Table2"]:
                if entry not in accounts:
                    accounts.append(entry)

        self._utility_accounts = []
        for acc in accounts:
            if acc.get("UtilityAccountNumber"):
                self._utility_accounts.append(
                    HidroelectricaAccount(
                        account_number=acc.get("AccountNumber", ""),
                        utility_account_number=acc.get("UtilityAccountNumber", ""),
                        address=acc.get("Address"),
                        is_default=acc.get("IsDefaultAccount", False),
                    )
                )

    def get_utility_accounts(self) -> List[HidroelectricaAccount]:
        """Return list of utility accounts"""
        return self._utility_accounts

    def get_current_bill(self, utility_account_number: str, account_number: str) -> Optional[HidroelectricaBill]:
        """
        Get current bill for an account.
        Returns HidroelectricaBill or None if no bill found.
        """
        payload = {
            "LanguageCode": "RO",
            "UserID": self._user_id,
            "IsBillPDF": "0",
            "UtilityAccountNumber": utility_account_number,
            "AccountNumber": account_number
        }
        try:
            resp = self._post_request(
                API_URL_GET_BILL,
                payload=payload,
                headers=self._auth_header,
                description="GetBill"
            )

            data = resp["result"]["Data"]
            if not data or not data.get("Table"):
                return None

            bill_data = data["Table"][0]  # First row contains bill data

            # Parse dates
            due_date = None
            issue_date = None
            period_from = None
            period_to = None

            if bill_data.get("DueDate"):
                try:
                    due_date = datetime.strptime(bill_data["DueDate"], "%Y-%m-%dT%H:%M:%S")
                except:
                    try:
                        due_date = datetime.strptime(bill_data["DueDate"], "%Y-%m-%d")
                    except:
                        pass

            if bill_data.get("IssueDate"):
                try:
                    issue_date = datetime.strptime(bill_data["IssueDate"], "%Y-%m-%dT%H:%M:%S")
                except:
                    try:
                        issue_date = datetime.strptime(bill_data["IssueDate"], "%Y-%m-%d")
                    except:
                        pass

            if bill_data.get("PeriodFrom"):
                try:
                    period_from = datetime.strptime(bill_data["PeriodFrom"], "%Y-%m-%dT%H:%M:%S")
                except:
                    try:
                        period_from = datetime.strptime(bill_data["PeriodFrom"], "%Y-%m-%d")
                    except:
                        pass

            if bill_data.get("PeriodTo"):
                try:
                    period_to = datetime.strptime(bill_data["PeriodTo"], "%Y-%m-%dT%H:%M:%S")
                except:
                    try:
                        period_to = datetime.strptime(bill_data["PeriodTo"], "%Y-%m-%d")
                    except:
                        pass

            # Extract amount
            amount = 0.0
            if bill_data.get("TotalAmount"):
                try:
                    amount = float(bill_data["TotalAmount"])
                except:
                    pass

            return HidroelectricaBill(
                utility_account_number=utility_account_number,
                account_number=account_number,
                bill_number=bill_data.get("BillNumber"),
                amount=amount,
                due_date=due_date,
                issue_date=issue_date,
                period_from=period_from,
                period_to=period_to,
                iban=bill_data.get("IBAN"),
                address=bill_data.get("Address"),
                raw_data=bill_data
            )
        except Exception as e:
            logger.error(f"Error getting bill for account {utility_account_number}: {e}")
            return None

    def get_all_bills(self) -> List[HidroelectricaBill]:
        """
        Get current bills for all accounts.
        Returns list of HidroelectricaBill objects.
        """
        bills = []
        for account in self._utility_accounts:
            bill = self.get_current_bill(account.utility_account_number, account.account_number)
            if bill:
                bills.append(bill)
        return bills

    def _post_request(self, url, payload, headers, description="Request"):
        """
        Internal method to make POST request and return decoded JSON.
        If we get 401, try re-authentication once and retry.
        """
        logger.debug(f"=== POST request to {url} ({description}) ===")

        # First attempt
        response = self._session.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 401:
            logger.warning(f"Got 401 at {description}, trying re-authentication...")
            # Invalidate current token
            self._session_token = None
            # Re-login
            self.login_if_needed()

            # Retry
            response = self._session.post(url, json=payload, headers=self._auth_header, timeout=10)

        if response.status_code != 200:
            raise Exception(f"Error at {description}: {response.status_code}, {response.text}")

        return response.json()

    def close(self):
        """Close requests session"""
        self._session.close()
        logger.debug("Hidroelectrica session closed")

