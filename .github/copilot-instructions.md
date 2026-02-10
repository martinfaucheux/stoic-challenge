## Introduction

We want to build an **Email Security** tool to flag emails with potential financial fraud attempts (fake president, fake supplier, etc.) that are received by our clients. We focus on clients that are using Google Workspace and Microsoft O365 so users and emails can be retrieved through relevant APIs.

The goal is to code the service retrieving the emails.

## Requirements

- Build the service in Python with FastAPI
- Use PostgreSQL
- Dockerize the service
- Tests

# implementation

## Routes

- `GET /emails(/id)` - Retrieve all emails
  ```json
  [
    {
      "id": 1,
      "sender": "example@example.com",
      "recipient": "recipient@example.com"
    }
  ]
  ```
- `POST /webhook` - Receive email data from Google Workspace and Microsoft O365

# steps

1. clarify what is the email format
2. build a basic email scanner
3. build the API to receive emails and store them in the database
4. add webhook handling
