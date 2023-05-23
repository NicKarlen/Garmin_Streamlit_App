"""
    https://pypi.org/project/garminconnect/ 

    Actually works API connection package
"""

import json
import logging
from datetime import datetime, timedelta
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

def display_json(api_call, output):
    """Format API output for better readability."""

    dashed = "-"*20
    header = f"{dashed} {api_call} {dashed}"
    footer = "-"*len(header)

    print(header)
    print(json.dumps(output, indent=4))
    print(footer)

def init_api_without_session(email, password):
    """Initialize Garmin API with your credentials."""
    try:
        api = Garmin(email, password)
        api.login()

    except Exception as e: 
        logging.error('Failed to login - Error: '+ str(e))

    return api

def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:
        ## Try to load the previous session
        with open("session.json") as f:
            saved_session = json.load(f)
            logging.info("Login to Garmin Connect using session loaded from 'session.json'")
            # Use the loaded session for initializing the API (without need for credentials)
            api = Garmin(session_data=saved_session)
            # Login using the
            api.login()

    except (FileNotFoundError, GarminConnectAuthenticationError):
        # Login to Garmin Connect portal with credentials since session is invalid or not present.
        logging.info(
            "Session file not present or turned invalid, login with your Garmin Connect credentials.\n"
            "NOTE: Credentials will not be stored, the session cookies will be stored in 'session.json' for future use."
        )
        try:
            api = Garmin(email, password)
            api.login()
            # Save session dictionary to json file for future use
            with open("session.json", "w", encoding="utf-8") as f:
                json.dump(api.session_data, f, ensure_ascii=False, indent=4)

        except Exception as e: 
            logging.error('Failed to login - Error: '+ str(e))

    return api

def garmin_api_get_all_activities_of_type(activitytype: str = "", email: str="", password: str = "", startdate = "2023-02-01"):
    logging.info("Function: 'garmin_api_get_all_activities_of_type' executed")
    # login with email & password or session
    api = init_api_without_session(email, password)
    # Get today's date
    today = datetime.today()
    # Calculate tomorrow's date
    tomorrow = today + timedelta(days=1)
    # Format tomorrow's date as YYYY-MM-DD
    tomorrow_formatted = tomorrow.strftime('%Y-%m-%d')
    print("API--REQUEST------------------!!")
    return api.get_activities_by_date(startdate=startdate, enddate=tomorrow_formatted, activitytype=activitytype)

if __name__ == "__main__":

    print(garmin_api_get_all_activities_of_type(activitytype="cycling", email="??", password="??"))

    # start = 0
    # limit = 2
    # display_json(f"api.get_activities({start}, {limit})", api.get_activities(start, limit)) 

    # first_activity_id = 11127864111
    # display_json(f"api.get_activity_splits({first_activity_id})", api.get_activity_splits(first_activity_id))
