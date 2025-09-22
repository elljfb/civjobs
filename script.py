from playwright.sync_api import sync_playwright
import re
from dateutil.parser import parse
from datetime import datetime
from supabase import create_client, Client
import os

# Supabase configuration - replace with your actual URL and key, or use environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# List of known UK regions to filter out
REGIONS = [
    "East Midlands (England)", "East of England", "London (region)", "North East England",
    "North West England", "Scotland", "South East England", "South West England",
    "Wales", "West Midlands (England)", "Yorkshire and the Humber"
]

# List of UK counties to filter out
COUNTIES = [
    "aberdeen", "aberdeenshire", "anglesey", "angus", "antrim", "argyll", "armagh", "avon", "ayrshire", "banffshire",
    "bedfordshire", "berkshire", "berwickshire", "brecknockshire", "bristol", "buckinghamshire", "bute", "caernarfonshire",
    "caithness", "cambridgeshire", "cambridgeshire and isle of ely", "cardiganshire", "carmarthenshire", "cheshire",
    "clackmannanshire", "cleveland", "clwyd", "cornwall", "cromartyshire", "cumberland", "cumbria", "denbighshire",
    "derbyshire", "devon", "dorset", "down", "dumfriesshire", "dunbartonshire", "dundee", "durham", "dyfed",
    "east lothian", "east suffolk", "east sussex", "edinburgh", "essex", "fermanagh", "fife", "flintshire", "glamorgan",
    "glasgow", "gloucestershire", "greater london", "greater manchester", "gwent", "gwynedd", "hampshire",
    "hereford and worcester", "herefordshire", "hertfordshire", "humberside", "huntingdon and peterborough",
    "huntingdonshire", "inverness-shire", "isle of ely", "isle of wight", "kent", "kincardineshire", "kinross-shire",
    "kirkcudbrightshire", "lanarkshire", "lancashire", "leicestershire", "lincolnshire", "london", "londonderry",
    "merionethshire", "mid glamorgan", "middlesex", "midlothian", "monmouthshire", "montgomeryshire", "moray",
    "nairnshire", "norfolk", "northamptonshire", "northumberland", "north yorkshire", "nottinghamshire", "orkney",
    "oxfordshire", "peeblesshire", "pembrokeshire", "perthshire", "powys", "radnorshire", "renfrewshire",
    "ross and cromarty", "ross-shire", "roxburghshire", "rutland", "selkirkshire", "shetland", "shropshire", "somerset",
    "south glamorgan", "staffordshire", "stirlingshire", "suffolk", "surrey", "sussex", "sutherland", "tyne and wear",
    "tyrone", "warwickshire", "west glamorgan", "west lothian", "west midlands", "westmorland", "west sussex",
    "west yorkshire", "wigtownshire", "wiltshire", "worcestershire", "yorkshire"
]
COUNTIES_SET = {c.lower() for c in COUNTIES}

# Bad keywords to skip, refined to be less aggressive (e.g., removed 'north', 'south')
BAD_KEYWORDS = [
    "building", "house", "barracks", "hmnb", "nps", "hq", "port", "barrack", "centre", "court", "magistrates",
    "prison", "office", "park", "unit", "crown", "combined", "justice", "civic", "technology", "business",
    "naval", "base", "hm", "nms", "moj", "jso", "walter", "tull", "flr", "st ", "rd ", "ave ", "dr ", "ln ",
    "sq ", "cir ", "blvd ", "magistrates court", "combined court", "justice ctr", "arun civic", "melbourne hse",
    "clemitson house", "carraway house", "leeland house", "pankhurst house ap", "bennet house", "sheriff's court",
    "new chase court", "little keep gate", "westwey house", "tylers avenue", "oakland court", "camden house",
    "mitre house", "ralphs centre", "forum house", "college house", "galleon house", "new road", "town quay house",
    "st clements house", "abbey gardens", "revelstoke house", "wynn jones centre", "units 9 and 10 talisman business",
    "macmillan house", "easton court", "milton keynes magistrates court", "whitehall", "semaphore tower", "victory building", 
    "naval base", "faslane port", "clansman building"
]
BAD_KEYWORDS_SET = {kw.lower() for kw in BAD_KEYWORDS}

# UK postcode regex pattern (approximate)
POSTCODE_REGEX = r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$'

def parse_locations(location_str: str) -> list:
    if not location_str or location_str == "N/A":
        return []

    # Replace separators and remove unwanted phrases/characters
    location_str = location_str.replace(" : ", ", ").replace(";", ", ")
    location_str = re.sub(r'see the job advert for full location information', '', location_str, flags=re.IGNORECASE)
    location_str = location_str.replace("(", "").replace(")", "")

    # Split by comma and strip
    parts = [p.strip() for p in location_str.split(",") if p.strip()]

    filtered_locations = set()
    for p in parts:
        # Strip leading/trailing non-alphanumeric characters (e.g., "*london.")
        cleaned_p = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', p).strip()

        # Skip if part is empty after cleaning
        if not cleaned_p:
            continue

        # Skip if it's a postcode
        if re.match(POSTCODE_REGEX, cleaned_p, re.IGNORECASE):
            continue
        
        # Skip if it's a known region
        if cleaned_p in REGIONS:
            continue
            
        # Skip if it's a county (case-insensitive)
        if cleaned_p.lower() in COUNTIES_SET:
            continue
            
        # Skip if contains digits (e.g., addresses like "23 Stephenson Street")
        if re.search(r'\d', cleaned_p):
            continue
            
        # Skip if any word in the location is a bad keyword.
        # This is safer than a substring search.
        part_words = {word.lower() for word in cleaned_p.split()}
        if not part_words.isdisjoint(BAD_KEYWORDS_SET):
            continue

        # If all checks pass, add the title-cased version to our set
        filtered_locations.add(cleaned_p.title())

    return sorted(list(filtered_locations))

def main():
    # Clear the tables before inserting new data
    supabase.table("job_locations").delete().neq("id", 0).execute()  # Clear job_locations
    supabase.table("job_listings").delete().neq("id", 0).execute()  # Clear job_listings
    print("Cleared job_listings and job_locations tables")

    # Load the saved URL
    with open("sid_url.txt", "r") as f:
        saved_url = f.read().strip()

    # Prepare list to store cleaned job data
    job_data = []
    locations_list = []

    with sync_playwright() as p:
        # Use the saved storage state
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="storage_state.json")
        page = context.new_page()

        print(f"Navigating to saved session URL: {saved_url}")
        page.goto(saved_url)

        # Click the search button and wait for navigation
        print("Clicking the 'Search for jobs' button")
        page.click('input#submitSearch')
        page.wait_for_load_state('networkidle')  # Wait for page to fully load after clicking

        while True:
            # Wait for job results to load
            page.wait_for_selector("li.search-results-job-box", timeout=30000)
            jobs = page.query_selector_all("li.search-results-job-box")
            print(f"Found {len(jobs)} jobs on current page")

            # Scrape jobs on current page
            for job in jobs:
                # Extract required fields
                title_elem = job.query_selector("h3.search-results-job-box-title a")
                department_elem = job.query_selector("div.search-results-job-box-department")
                location_elem = job.query_selector("div.search-results-job-box-location")
                salary_elem = job.query_selector("div.search-results-job-box-salary")
                closing_date_elem = job.query_selector("div.search-results-job-box-closingdate")

                # Get text content and URL, handling cases where elements might be missing
                title = title_elem.inner_text().strip() if title_elem else "N/A"
                job_url = title_elem.get_attribute("href") if title_elem else "N/A"
                department = department_elem.inner_text().strip() if department_elem else "N/A"
                location = location_elem.inner_text().strip() if location_elem else "N/A"
                salary = salary_elem.inner_text().replace("Salary : ", "").strip() if salary_elem else "N/A"
                closing_date = closing_date_elem.inner_text().replace("Closes : ", "").strip() if closing_date_elem else "N/A"

                # Parse and clean closing date
                closing_dt = None
                if closing_date != "N/A":
                    try:
                        closing_dt = parse(closing_date, fuzzy=True)
                        if closing_dt < datetime.now():
                            print(f"Skipping expired job: {title} (closes {closing_date})")
                            continue
                    except Exception as e:
                        print(f"Could not parse closing date for {title}: {e}")

                # Clean locations into a list
                cleaned_locations = parse_locations(location)

                # Skip job if no valid locations after cleaning
                if not cleaned_locations:
                    print(f"Skipping job with no valid locations: {title}")
                    continue

                # Add cleaned data to job_data
                job_data.append({
                    "title": title,
                    "department": department,
                    "salary": salary,
                    "closing_date": closing_dt.isoformat() if closing_dt else None,
                    "url": job_url
                })

                locations_list.append(cleaned_locations)
                print(f"Scraped and cleaned job: {title} | URL: {job_url} | Locations: {cleaned_locations}")

            # Check for "Next" link
            next_link = page.query_selector('a[title="Go to next search results page"]')
            if not next_link:
                print("No more pages to scrape")
                break

            # Click "Next" link and wait for page to load
            print("Navigating to next page")
            next_link.click()
            page.wait_for_load_state('networkidle')  # Wait for next page to fully load

        browser.close()

    # Insert cleaned jobs into Supabase
    if job_data:
        response = supabase.table("job_listings").insert(job_data).execute()
        inserted_jobs = response.data  # List of inserted jobs with their IDs

        # Prepare inserts for job_locations table
        location_inserts = []
        for idx, inserted_job in enumerate(inserted_jobs):
            job_id = inserted_job["id"]
            for loc in locations_list[idx]:
                if loc:
                    location_inserts.append({
                        "job_id": job_id,
                        "location": loc
                    })

        if location_inserts:
            supabase.table("job_locations").insert(location_inserts).execute()

        print(f"Inserted {len(job_data)} jobs into Supabase")

if __name__ == "__main__":
    main()