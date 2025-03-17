#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

import requests


def main():
    print("Initiating process...")

    # Get GitHub token from environment variable
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    # Set up GitHub API headers
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

    # Get GitHub context from environment variables or event file
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")

    # Default values for repository
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    owner, repo = repository.split("/") if "/" in repository else ("", "")

    # Initialize issue and comment data
    issue = None
    comment = None

    # Load event data if available
    if event_path and os.path.exists(event_path):
        with open(event_path, "r") as f:
            event_data = json.load(f)
            if "issue" in event_data:
                issue = event_data["issue"]
            if "comment" in event_data:
                comment = event_data["comment"]

    print(f"Handling event: {event_name} in repository {repository}")

    # Keywords for assignment and unassignment
    assign_keywords = [
        "i am interested in contributing",
        "i am interested in doing this",
        "i can try fixing this",
        "work on this",
        "be assigned this",
        "assign me this",
        "assign it to me",
        "assign this to me",
        "assign to me",
        "/assign",
    ]
    unassign_keywords = ["/unassign"]

    # Process issue comments
    if event_name == "issue_comment" and issue and comment:
        print("Processing comment...")
        comment_body = comment.get("body", "").lower()

        # Check for unassign request
        is_unassign = any(keyword in comment_body for keyword in unassign_keywords)

        if is_unassign:
            user_login = comment.get("user", {}).get("login", "")
            issue_number = issue.get("number")
            print(f"Removing assignment of issue #{issue_number} from {user_login}")

            try:
                # Get issue details
                issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
                issue_response = requests.get(issue_url, headers=headers)
                issue_data = issue_response.json()

                # Check if issue has "assigned" label
                has_assigned_label = any(label.get("name") == "assigned" for label in issue_data.get("labels", []))

                if has_assigned_label:
                    # Remove assignee
                    assignees_url = f"{issue_url}/assignees"
                    requests.delete(assignees_url, headers=headers, json={"assignees": [user_login]})

                    # Remove "assigned" label
                    try:
                        label_url = f"{issue_url}/labels/assigned"
                        requests.delete(label_url, headers=headers)
                    except Exception:
                        print("Label missing or already deleted.")

                    # Check for existing unassign comments
                    comments_url = f"{issue_url}/comments"
                    comments_response = requests.get(comments_url, headers=headers)
                    comments_data = comments_response.json()

                    has_unassign_comment = any(
                        "You have been unassigned. This task is now available for others." in c.get("body", "")
                        for c in comments_data
                    )

                    if not has_unassign_comment:
                        # Add unassign comment
                        unassign_msg = (
                            "You have been unassigned. This task is now available for others. "
                            "Type /assign if you'd like to take it again."
                        )
                        requests.post(comments_url, headers=headers, json={"body": unassign_msg})
                else:
                    print(f"Issue #{issue_number} lacks 'assigned' label, skipping.")
            except Exception as e:
                print(f"Failed to unassign issue #{issue_number}: {str(e)}")

        # Check for assign request
        is_assign = any(keyword in comment_body for keyword in assign_keywords)

        if is_assign:
            user_login = comment.get("user", {}).get("login", "")
            issue_number = issue.get("number")
            print(f"Assigning issue #{issue_number} to {user_login}")

            try:
                # Get user's open issues
                issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                params = {"state": "open", "assignee": user_login}
                issues_response = requests.get(issues_url, headers=headers, params=params)
                assigned_issues = issues_response.json()

                # Filter issues without open PRs
                issues_without_prs = []
                for assigned_issue in assigned_issues:
                    if assigned_issue.get("number") == issue_number:
                        continue

                    # Search for PRs referencing this issue
                    search_url = "https://api.github.com/search/issues"
                    search_query = f"type:pr state:open repo:{owner}/{repo} " f"{assigned_issue.get('number')} in:body"
                    search_params = {"q": search_query}
                    search_response = requests.get(search_url, headers=headers, params=search_params)
                    search_data = search_response.json()

                    if search_data.get("total_count", 0) == 0:
                        print(f"Issue #{assigned_issue.get('number')} lacks an open PR")
                        issues_without_prs.append(assigned_issue.get("number"))

                if issues_without_prs:
                    # User has uncompleted issues
                    issues_list = ", #".join(str(num) for num in issues_without_prs)
                    comment_body = (
                        f"You can't take this task yet. You still have uncompleted issues: "
                        f"#{issues_list}. Please complete them before requesting another."
                    )
                    requests.post(f"{issue_url}/comments", headers=headers, json={"body": comment_body})
                    return

                # Assign the issue
                assignees_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/assignees"
                requests.post(assignees_url, headers=headers, json={"assignees": [user_login]})

                # Add "assigned" label
                labels_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/labels"
                requests.post(labels_url, headers=headers, json={"labels": ["assigned"]})

                # Add assignment comment
                assignment_msg = (
                    f"Hey @{user_login}! You're assigned to [{owner}/{repo} issue #{issue_number}]"
                    f"(https://github.com/{owner}/{repo}/issues/{issue_number}). "
                    f"Please finish your PR within 1 day."
                )
                requests.post(
                    f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=headers,
                    json={"body": assignment_msg},
                )
            except Exception as e:
                print(f"Failed to assign issue #{issue_number}: {str(e)}")

    # Review inactive assignments
    print("Reviewing inactive assignments...")
    current_time = datetime.now()

    try:
        # Get repository events
        events_url = f"https://api.github.com/repos/{owner}/{repo}/issues/events"
        events_response = requests.get(events_url, headers=headers, params={"per_page": 100})
        events = events_response.json()

        # Filter for assignment events
        assigned_events = [e for e in events if e.get("event") == "assigned"]

        for event in assigned_events:
            issue_url = event.get("issue", {}).get("url")
            if not issue_url:
                continue

            # Get issue details
            issue_response = requests.get(issue_url, headers=headers)
            issue_data = issue_response.json()

            if issue_data.get("assignee") and issue_data.get("state") == "open":
                # Calculate days since last update
                updated_at = datetime.strptime(issue_data.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ")
                days_since_update = (current_time - updated_at).total_seconds() / (86400)  # seconds in a day

                if days_since_update > 1:
                    issue_number = issue_data.get("number")
                    print(f"Revoking assignment of issue #{issue_number} due to 1 day of inactivity")

                    # Check if issue has "assigned" label
                    has_assigned_label = any(label.get("name") == "assigned" for label in issue_data.get("labels", []))

                    if has_assigned_label:
                        # Remove assignee
                        assignee_login = issue_data.get("assignee", {}).get("login")
                        assignees_url = f"{issue_url}/assignees"
                        requests.delete(assignees_url, headers=headers, json={"assignees": [assignee_login]})

                        # Remove "assigned" label
                        label_url = f"{issue_url}/labels/assigned"
                        requests.delete(label_url, headers=headers)

                        # Add unassign comment
                        comments_url = f"{issue_url}/comments"
                        requests.post(
                            comments_url,
                            headers=headers,
                            json={"body": "⏳ Task unassigned due to inactivity. Available for reassignment."},
                        )
                    else:
                        print(f"Issue #{issue_number} lacks 'assigned' label, skipping.")
    except Exception as e:
        print(f"Failed to process inactive assignments: {str(e)}")


if __name__ == "__main__":
    main()
