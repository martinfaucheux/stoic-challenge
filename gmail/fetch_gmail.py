"""
Test script to fetch Gmail messages and convert them to Email objects.

This script demonstrates how to:
1. Authenticate with Gmail API
2. Fetch recent emails from inbox
3. Convert them to Email dataclass objects
4. Display email information

Usage:
    python -m gmail.fetch_gmail
"""

from pathlib import Path

from models import Email

from .service import fetch_gmail_messages


def save_email_to_json(email: Email, output_dir: Path):
    """Save email to JSON file using Pydantic serialization"""
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename from email ID and timestamp
    timestamp = email.received_at.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{email.id}.json"
    filepath = output_dir / filename

    # Save using Pydantic's built-in JSON serialization
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(email.model_dump_json(indent=2))

    return filepath


def display_email(email: Email, index: int):
    """Pretty print email information"""
    print(f"\n{'=' * 80}")
    print(f"Email #{index}")
    print(f"{'=' * 80}")
    print(f"ID: {email.id}")
    print(f"Provider: {email.provider}")
    print(f"From: {email.sender}")
    print(f"To: {email.recipient}")
    if email.recipients_cc:
        print(f"CC: {', '.join(email.recipients_cc)}")
    if email.recipients_bcc:
        print(f"BCC: {', '.join(email.recipients_bcc)}")
    print(f"Subject: {email.subject}")
    print(f"Received: {email.received_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Attachments: {len(email.attachments)}")
    if email.attachments:
        for att in email.attachments:
            print(f"  - {att['filename']} ({att['mimeType']}, {att['size']} bytes)")
    print("\nBody Preview (first 200 chars):")
    print("-" * 80)
    body_preview = email.body[:200].replace("\n", " ")
    print(f"{body_preview}...")
    print("-" * 80)


def main():
    """Main function to fetch and display Gmail messages"""
    print("Gmail Email Fetcher")
    print("=" * 80)
    print("\nThis will open a browser window for Gmail authentication.")
    print("Please authorize the application to read your emails.\n")

    # You can customize the query and max results
    query = "in:inbox"  # Fetch inbox messages
    # query = "after:2026/02/01"  # Fetch messages after specific date
    # query = "is:unread"  # Fetch unread messages only
    max_results = 5  # Fetch last 5 emails

    print(f"Fetching {max_results} emails with query: '{query}'")
    print("-" * 80)

    try:
        # Fetch emails
        emails = fetch_gmail_messages(max_results=max_results, query=query)

        if not emails:
            print("\nNo emails found.")
            return

        # Create output directory
        output_dir = Path("fetched_emails")

        # Display and save each email
        saved_files = []
        for i, email in enumerate(emails, 1):
            display_email(email, i)

            # Save email to JSON
            filepath = save_email_to_json(email, output_dir)
            saved_files.append(filepath)
            print(f"💾 Saved to: {filepath}")

        # Summary
        print(f"\n{'=' * 80}")
        print(f"Summary: Successfully fetched {len(emails)} email(s)")
        print(f"Emails saved to: {output_dir.absolute()}")
        print(f"{'=' * 80}")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease follow these steps:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com)")
        print("2. Create a project or select existing one")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download credentials.json to project root")
        print("\nFor detailed instructions, see README.md")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
