from datetime import datetime
from typing import Dict, List, Tuple

import aiohttp
import bugsnag


BASE_URL = "https://michiganelections.io/api"


async def get_status(
    first_name: str, last_name: str, birth_date: str, zip_code: int
) -> Dict:
    if "-" not in birth_date:
        dt = datetime.strptime(birth_date, "%m/%d/%Y")
        birth_date = dt.date().isoformat()

    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/registrations/?first_name={first_name}&last_name={last_name}&birth_date={birth_date}&zip_code={zip_code}"
        async with session.get(url) as response:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                data = {}

    if "registered" not in data:
        bugsnag.notify(
            ValueError(f"No registration status: {url}"),
            context="get_status",
            meta_data={
                "registration": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": birth_date,
                    "zip_code": zip_code,
                }
            },
        )
        data = {"registered": False}

    return data


async def get_elections() -> List:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/elections/?active=true"
        async with session.get(url) as response:
            data = await response.json()

    return list(reversed(data["results"]))


async def get_election(election_id: int) -> Dict:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/elections/{election_id}/"
        async with session.get(url) as response:
            data = await response.json()

    return data


async def get_ballot(
    election_id: int, precinct_id: int, party: str = ""
) -> Tuple[Dict, List, List]:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/ballots/?election_id={election_id}&precinct_id={precinct_id}&active_election=null"
        async with session.get(url) as response:
            data = await response.json()
            try:
                ballot = data["results"][0]
            except LookupError:
                ballot = None

        if ballot is None:
            bugsnag.notify(
                LookupError(f"No ballot: {url}"),
                context="get_ballot",
                meta_data={
                    "ballot": {"election_id": election_id, "precinct_id": precinct_id}
                },
            )

    positions = await get_positions(election_id, precinct_id, party)
    proposals = await get_proposals(election_id, precinct_id)

    return ballot, positions, proposals


async def get_positions(election_id: int, precinct_id: int, party: str = "") -> List:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/positions/?election_id={election_id}&precinct_id={precinct_id}&active_election=null&limit=1000"
        if party:
            url += f"&section={party}"
        async with session.get(url) as response:
            positions = await response.json()

    return positions["results"]


async def get_proposals(election_id: int, precinct_id: int) -> List:
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/proposals/?election_id={election_id}&precinct_id={precinct_id}&active_election=null&limit=1000"
        async with session.get(url) as response:
            proposals = await response.json()

    return sorted(proposals["results"], key=lambda d: d["name"])
