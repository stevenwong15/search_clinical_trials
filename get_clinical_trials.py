import requests
import pandas as pd

# to update:
# - decide how to incrementally add studies (e.g. by first_post_date or last_update_date)
def get_clinical_trials(location = "United States", min_date = "MIN", max_date = "MAX"):

    print(f"getting clinical trials in {location} first posted from {min_date} to {max_date}")
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.locn": location,
        "filter.advanced": f"AREA[StudyFirstPostDate]RANGE[{min_date}, {max_date}]",
        # "filter.ids": "NCT06313437", # test case
        "countTotal": "true",
        "pageSize": 100
        }

    studies = []

    while True:
        data = requests.get(url = base_url, params = params).json()

        if data.get("totalCount"): 
            total_count = data.get("totalCount")

        studies.extend(data["studies"])
        print(f"progress: {round(len(studies)/total_count*100)}% out of {total_count}")

        if data.get("nextPageToken"):
            params["pageToken"] = data.get("nextPageToken")
        else:
            print("progress: finished")
            break
    
    return studies

studies = get_clinical_trials(location = "United States", min_date = "01/01/2024", max_date = "04/30/2025")

# to update:
# - add center location, probably under eligibility
# - add arm, intervention and outcomes, under treatment
studies_df = pd.DataFrame([{
    # what is the status of the study? 
    "nct_id": study["protocolSection"]["identificationModule"].get("nctId", ""),
    "status": study["protocolSection"]["statusModule"].get("overallStatus", ""),
    "start_date": study["protocolSection"]["statusModule"].get("startDateStruct", {}).get("date", ""),
    "completion_date": study["protocolSection"]["statusModule"].get("completionDateStruct", {}).get("date", ""),
    "first_post_date": study["protocolSection"]["statusModule"].get("studyFirstPostDateStruct", {}).get("date", ""),
    "last_update_date": study["protocolSection"]["statusModule"].get("lastUpdatePostDateStruct", {}).get("date", ""),
    # who's running the study?
    "contact": list(
        set([contact["name"] for contact in study["protocolSection"]["contactsLocationsModule"].get("centralContacts", {})]) |
        set([pi["name"] for pi in study["protocolSection"]["contactsLocationsModule"].get("overallOfficials", {})])
        ),
    "sponsor": study["protocolSection"]["sponsorCollaboratorsModule"].get("leadSponsor", {}).get("name", ""),
    "collaborators": [collab["name"] for collab in study["protocolSection"]["sponsorCollaboratorsModule"].get("collaborators", "")],
    # what is the study about?
    "brief_title": study["protocolSection"]["identificationModule"].get("briefTitle", ""),
    "official_title": study["protocolSection"]["identificationModule"].get("officialTitle", ""),
    "purpose": study["protocolSection"]["descriptionModule"].get("briefSummary", ""),
    "description": study["protocolSection"]["descriptionModule"].get("detailedDescription", ""),
    "conditions_treated": study["protocolSection"]["conditionsModule"].get("conditions", ""),
    # how is the study conducted? 
    "type": study["protocolSection"]["designModule"].get("studyType", ""),
    "phase": study["protocolSection"]["designModule"].get("phases", ""),
    # who is eligibility?
    "criteria_overall": study["protocolSection"]["eligibilityModule"].get("eligibilityCriteria", ""),
    "criteria_sex": study["protocolSection"]["eligibilityModule"].get("sex", ""),
    "criteria_age": study["protocolSection"]["eligibilityModule"].get("stdAges", "")
    } for study in studies])

studies_df["keywords"] = studies_df.apply(lambda x: f"""
# Title:\n\n{x["official_title"]}\n
# Purpose:\n\n{x["purpose"]}\n
# Description:\n\n{x["description"]}
""", axis = 1)
studies_df["start_date"] = [date + "-01" if len(date) == 7 else date for date in studies_df["start_date"]]
studies_df["completion_date"] = [date + "-01" if len(date) == 7 else date for date in studies_df["completion_date"]]
studies_df["first_post_date"] = [date + "-01" if len(date) == 7 else date for date in studies_df["first_post_date"]]
studies_df["last_update_date"] = [date + "-01" if len(date) == 7 else date for date in studies_df["last_update_date"]]

studies_df.to_csv("studies_20240101_20250430.csv")
print("wrote to studies_20240101_20250430.csv")
