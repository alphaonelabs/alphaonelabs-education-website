#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests


def main():
    print("Initiating process...")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Manage GitHub issue assignments")
    parser.add_argument("--no-unassign", action="store_true", help="Skip unassigning inactive issues")
    args = parser.parse_args()

    # Get GitHub
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    print("GitHub token acquired.")

    # Set up GitHub API headers
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    print("GitHub API headers set up.")

    # Get GitHub context from environment variables or event file
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    print(f"Event name: {event_name}")

    # Default values for repository
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    owner, repo = repository.split("/") if "/" in repository else ("", "")
    print(f"Repository: {repository}, Owner: {owner}, Repo: {repo}")

    # Initialize issue and comment data
    issue = None
    comment = None

    # Load event data if available
    if event_path and os.path.exists(event_path):
        print(f"Loading event data from: {event_path}")
        with open(event_path, "r") as f:
            event_data = json.load(f)
            if "issue" in event_data:
                issue = event_data["issue"]
                print(f"Issue detected: #{issue.get('number')}")
            if "comment" in event_data:
                comment = event_data["comment"]
                print(f"Comment detected from user: {comment.get('user', {}).get('login', '')}")

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
            print(f"Unassign request detected. Removing assignment of issue #{issue_number} from {user_login}")

            try:
                # Get issue details
                issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
                print(f"Fetching issue details from {issue_url}")
                issue_response = requests.get(issue_url, headers=headers)
                print(f"Issue details response status: {issue_response.status_code}")
                issue_data = issue_response.json()
                print("Issue details fetched.")

                # Check if issue has "assigned" label
                has_assigned_label = any(label.get("name") == "assigned" for label in issue_data.get("labels", []))
                print(f"'assigned' label present: {has_assigned_label}")

                if has_assigned_label:
                    # Remove assignee
                    assignees_url = f"{issue_url}/assignees"
                    print(f"Removing assignee {user_login} via {assignees_url}")
                    requests.delete(assignees_url, headers=headers, json={"assignees": [user_login]})
                    print("Assignee removed.")

                    # Remove "assigned" label
                    try:
                        label_url = f"{issue_url}/labels/assigned"
                        print(f"Removing 'assigned' label via {label_url}")
                        requests.delete(label_url, headers=headers)
                        print("'assigned' label removed.")
                    except Exception:
                        print("Label missing or already deleted.")

                    # Check for existing unassign comments
                    comments_url = f"{issue_url}/comments"
                    print(f"Fetching comments from {comments_url}")
                    comments_response = requests.get(comments_url, headers=headers)
                    comments_data = comments_response.json()
                    print("Comments fetched.")

                    has_unassign_comment = any(
                        "You have been unassigned. This task is now available for others." in c.get("body", "")
                        for c in comments_data
                    )
                    print(f"Unassign comment already exists: {has_unassign_comment}")

                    if not has_unassign_comment:
                        # Add unassign comment
                        unassign_msg = (
                            "You have been unassigned. This task is now available for others. "
                            "Type /assign if you'd like to take it again."
                        )
                        print("Posting unassign comment.")
                        requests.post(comments_url, headers=headers, json={"body": unassign_msg})
                        print("Unassign comment posted.")
                else:
                    print(f"Issue #{issue_number} lacks 'assigned' label, skipping unassignment.")
            except Exception as e:
                print(f"Failed to unassign issue #{issue_number}: {str(e)}")

        # Check for assign request
        is_assign = any(keyword in comment_body for keyword in assign_keywords)
        if is_assign:
            user_login = comment.get("user", {}).get("login", "")
            issue_number = issue.get("number")
            print(f"Assign request detected. Assigning issue #{issue_number} to {user_login}")

            try:
                # Define issue_url at the beginning of this block
                issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"

                # Get issue details to check if already assigned
                print(f"Fetching issue details from {issue_url}")
                issue_response = requests.get(issue_url, headers=headers)
                print(f"Issue details response status: {issue_response.status_code}")
                issue_data = issue_response.json()

                # Check if issue already has an assignee (implementing single assignee rule)
                current_assignee = issue_data.get("assignee")
                if current_assignee:
                    current_assignee_login = current_assignee.get("login")
                    print(f"Issue #{issue_number} already assigned to {current_assignee_login}")

                    # Don't allow a second person to be assigned
                    if current_assignee_login != user_login:
                        comment_body = (
                            f"@{user_login} This issue is already assigned to @{current_assignee_login}. "
                            f"Please wait until it becomes available or choose a different issue."
                        )
                        print(f"Rejecting assignment request from {user_login}")
                        requests.post(f"{issue_url}/comments", headers=headers, json={"body": comment_body})
                        return
                    else:
                        print(f"User {user_login} is already assigned to this issue. No action needed.")
                        return

                # Get user's open issues
                issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                params = {"state": "open", "assignee": user_login}
                print(f"Fetching open issues for user {user_login} from {issues_url} with params {params}")
                issues_response = requests.get(issues_url, headers=headers, params=params)
                print(f"Response status for open issues: {issues_response.status_code}")
                assigned_issues = issues_response.json()
                print(f"User {user_login} has {len(assigned_issues)} open assigned issues.")

                # Filter issues without open PRs
                issues_without_prs = []
                for assigned_issue in assigned_issues:
                    if assigned_issue.get("number") == issue_number:
                        continue

                    print(f"Checking for open PRs referencing issue #{assigned_issue.get('number')}")
                    # Search for PRs referencing this issue
                    search_url = "https://api.github.com/search/issues"
                    search_query = f"type:pr state:open repo:{owner}/{repo} {assigned_issue.get('number')} in:body"
                    search_params = {"q": search_query}
                    print(f"Searching PRs with query: {search_query}")
                    search_response = requests.get(search_url, headers=headers, params=search_params)
                    print(f"Search response status: {search_response.status_code}")
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
                    print(f"User {user_login} blocked due to uncompleted issues: {issues_list}")
                    requests.post(f"{issue_url}/comments", headers=headers, json={"body": comment_body})
                    return

                # Assign the issue
                assignees_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/assignees"
                print(f"Assigning issue via {assignees_url}")
                assign_response = requests.post(assignees_url, headers=headers, json={"assignees": [user_login]})
                if assign_response.status_code >= 400:
                    print(f"Error assigning issue: {assign_response.status_code} - {assign_response.text}")
                    return
                else:
                    print(f"Issue #{issue_number} assigned to {user_login}")

                # Add "assigned" label
                labels_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/labels"
                print(f"Adding 'assigned' label via {labels_url}")
                label_response = requests.post(labels_url, headers=headers, json={"labels": ["assigned"]})
                if label_response.status_code >= 400:
                    print(f"Error adding label: {label_response.status_code} - {label_response.text}")
                else:
                    print(f"'assigned' label added to issue #{issue_number}")

                # Add assignment comment
                assignment_msg = (
                    f"Hey @{user_login}! You're now assigned to this issue. " f"Please finish your PR within 1 day."
                )
                print("Posting assignment comment.")
                comment_response = requests.post(
                    f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=headers,
                    json={"body": assignment_msg},
                )
                if comment_response.status_code >= 400:
                    print(f"Error posting comment: {comment_response.status_code} - {comment_response.text}")
                else:
                    print("Assignment comment posted successfully.")
            except Exception as e:
                print(f"Failed to assign issue #{issue_number}: {str(e)}")

    # Review inactive assignments
    if not args.no_unassign:
        print("Reviewing inactive assignments...")
        current_time = datetime.now(timezone.utc)  # Use UTC for consistent timestamp comparison

        try:
            # Get all open issues directly
            issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            params = {"state": "open", "labels": "assigned", "per_page": 100}
            print(f"Fetching open assigned issues from {issues_url}")

            all_assigned_issues = []
            page = 1

            while True:
                params["page"] = page
                issues_response = requests.get(issues_url, headers=headers, params=params)
                print(f"Issues response status: {issues_response.status_code} for page {page}")

                if issues_response.status_code != 200:
                    print(f"Error fetching issues: {issues_response.status_code} - {issues_response.text}")
                    break

                issues_page = issues_response.json()
                if not issues_page:
                    break  # No more issues

                all_assigned_issues.extend(issues_page)
                page += 1

                # GitHub API best practice - check if we've reached the last page
                if "Link" not in issues_response.headers or 'rel="next"' not in issues_response.headers["Link"]:
                    break

            print(f"Found {len(all_assigned_issues)} open issues with 'assigned' label")

            for issue_data in all_assigned_issues:
                if issue_data.get("assignee"):
                    # Calculate time since last update in UTC
                    updated_at = datetime.strptime(issue_data.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ")
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                    days_since_update = (current_time - updated_at).total_seconds() / 86400  # seconds in a day
                    issue_number = issue_data.get("number")
                    print(f"Issue #{issue_number} last updated {days_since_update:.2f} days ago.")

                    if days_since_update > 1:  # More than 24 hours of inactivity
                        print(f"Revoking assignment of issue #{issue_number} due to 1 day of inactivity")

                        issue_url = issue_data.get("url")

                        # Get assignee login
                        assignee_login = issue_data.get("assignee", {}).get("login")
                        if not assignee_login:
                            print(f"Issue #{issue_number} has no assignee, skipping.")
                            continue

                        # Remove assignee
                        assignees_url = f"{issue_url}/assignees"
                        print(f"Removing assignee {assignee_login} via {assignees_url}")
                        unassign_response = requests.delete(
                            assignees_url, headers=headers, json={"assignees": [assignee_login]}
                        )

                        if unassign_response.status_code >= 400:
                            print(
                                f"Error removing assignee: "
                                f"{unassign_response.status_code} - {unassign_response.text}"
                            )
                            continue
                        else:
                            print(f"Assignee {assignee_login} removed from issue #{issue_number}")

                        # Remove "assigned" label
                        label_url = f"{issue_url}/labels/assigned"
                        print(f"Removing 'assigned' label via {label_url}")
                        label_response = requests.delete(label_url, headers=headers)

                        # 404 is ok if label doesn't exist
                        if label_response.status_code >= 400 and label_response.status_code != 404:
                            print(f"Error removing label: " f"{label_response.status_code} - {label_response.text}")
                        else:
                            print(f"'assigned' label removed from issue #{issue_number}")

                        # Add unassign comment
                        comments_url = f"{issue_url}/comments"
                        unassign_msg = (
                            f"⏳ Task unassigned from @{assignee_login} due to inactivity "
                            f"(no updates within 24 hours). Available for reassignment."
                        )
                        print(f"Posting unassign comment to {comments_url}")
                        comment_response = requests.post(
                            comments_url,
                            headers=headers,
                            json={"body": unassign_msg},
                        )

                        if comment_response.status_code >= 400:
                            print(f"Error posting comment: {comment_response.status_code} - {comment_response.text}")
                        else:
                            print(f"Unassign comment posted to issue #{issue_number}")
                else:
                    print(f"Issue #{issue_data.get('number')} has 'assigned' label but no assignee. Removing label.")
                    # Remove "assigned" label if issue somehow has no assignee
                    label_url = f"{issue_data.get('url')}/labels/assigned"
                    requests.delete(label_url, headers=headers)
        except Exception as e:
            print(f"Failed to process inactive assignments: {str(e)}")
    else:
        print("Skipping inactive assignment check due to --no-unassign flag")


if __name__ == "__main__":
    main()
