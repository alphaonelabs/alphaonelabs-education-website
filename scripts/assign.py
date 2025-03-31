import re
import sys

def process_command(comment, assignees):
    assign_match = re.search(r'/assign\s+(@\S+)', comment)
    unassign_match = re.search(r'/unassign\s+(@\S+)', comment)
    
    if assign_match:
        user = assign_match.group(1)
        if user not in assignees:
            assignees.append(user)
            print(f"Assigned {user} to the issue.")
        else:
            print(f"{user} is already assigned.")
    
    if unassign_match:
        user = unassign_match.group(1)
        if user in assignees:
            assignees.remove(user)
            print(f"Unassigned {user} from the issue.")
        else:
            print(f"{user} is not assigned to the issue.")

if __name__ == "__main__":
    comment = sys.argv[1] if len(sys.argv) > 1 else ""
    assignees = []  # Replace this with actual issue assignees fetching logic
    process_command(comment, assignees)
