# Google Server-Side Setup Guide

This guide walks you through setting up Google OAuth 2.0 credentials and configuring your Google Cloud Project for the Email Security Tool.

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com)
- Administrator access to configure OAuth consent screen (for production)

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com)
2. Click on the project dropdown at the top of the page
3. Click "New Project"
4. Enter a project name (e.g., "Email Security Tool")
5. Select your organization (if applicable)
6. Click "Create"

## Step 2: Enable Required APIs

1. In your Google Cloud Project, navigate to **APIs & Services > Library**
2. Search for and enable the following APIs:
   - **Gmail API** - For accessing Gmail emails
   - **Google+ API** (or People API) - For user profile information
   - **Admin SDK API** - For Google Workspace admin functions (if needed)

## Step 3: Configure OAuth Consent Screen

### For Development/Testing

1. Navigate to **APIs & Services > OAuth consent screen**
2. Select **External** user type (unless you're in a Google Workspace organization)
3. Click **Create**
4. Fill in the required information:
   - **App name**: Email Security Tool
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click **Save and Continue**
6. On the Scopes page, click **Add or Remove Scopes**
7. Add the following scopes:
   ```
   https://www.googleapis.com/auth/userinfo.email
   https://www.googleapis.com/auth/userinfo.profile
   https://www.googleapis.com/auth/gmail.readonly
   ```
8. Click **Save and Continue**
9. Add test users (your email addresses for testing)
10. Click **Save and Continue**

### For Production

- You'll need to submit your app for verification
- This process can take several days to weeks
- Ensure your privacy policy and terms of service are accessible

## Step 4: Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client IDs**
3. Select **Web application** as the application type
4. Enter a name (e.g., "Email Security Tool Web Client")
5. Add **Authorized redirect URIs**:
   - For local development: `http://localhost:8000/auth/callback/google`
   - For production: `https://yourdomain.com/auth/callback/google`
6. Click **Create**
7. Copy the **Client ID** and **Client Secret** - you'll need these for environment variables

## Step 5: Environment Configuration

Add the following environment variables to your application:

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret-here"
GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/auth/callback/google"

# Google OAuth Scopes (comma-separated)
GOOGLE_OAUTH_SCOPES="https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/gmail.readonly"

# Base URL for your application
BASE_URL="http://localhost:8000"
```

### For Docker/Production

Create a `.env` file in your project root or set these in your deployment environment.

## Step 6: Test the Configuration

1. Start your application:

   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Test the OAuth flow:
   - Register a new user: `POST http://localhost:8000/register`
   - Login to get a JWT token: `POST http://localhost:8000/token`
   - Initiate Google OAuth: `POST http://localhost:8000/email-configuration/google` (with Authorization header)
   - Follow the returned authorization URL
   - Complete the OAuth consent flow

## Security Considerations

### State Parameter

- The application uses JWT tokens as state parameters for CSRF protection
- State tokens expire after 30 minutes
- Each OAuth flow is tied to a specific authenticated user

### Token Storage

- Access tokens and refresh tokens are encrypted before database storage
- Uses Fernet symmetric encryption with your `SECRET_KEY`
- Tokens are automatically refreshed when expired

### Scopes

- **userinfo.email**: Required for user identification
- **userinfo.profile**: For additional user information
- **gmail.readonly**: For reading Gmail messages (adjust as needed)

## Troubleshooting

### Common Issues

1. **"Redirect URI mismatch"**
   - Ensure the redirect URI in Google Console exactly matches `GOOGLE_OAUTH_REDIRECT_URI`
   - Check for trailing slashes and protocol (http vs https)

2. **"Access blocked: This app's request is invalid"**
   - Verify OAuth consent screen is properly configured
   - Check that required scopes are added
   - Ensure the client ID is correct

3. **"Error 403: access_denied"**
   - User needs to be added as a test user (for unverified apps)
   - Check OAuth consent screen configuration

4. **Token refresh failures**
   - Ensure `access_type=offline` is set (already configured)
   - Verify `prompt=consent` forces refresh token issuance

### Debug Mode

Enable debug logging to troubleshoot OAuth issues:

```python
import logging
logging.getLogger('httpx').setLevel(logging.DEBUG)
```

## Production Deployment

### Domain Configuration

1. Update redirect URIs to use your production domain
2. Update `BASE_URL` environment variable
3. Use HTTPS for all OAuth endpoints

### App Verification

For production use with external users:

1. Complete Google's app verification process
2. Provide privacy policy and terms of service
3. Explain why each scope is needed
4. May require domain verification

### Rate Limits

- Google APIs have usage quotas and rate limits
- Monitor usage in Google Cloud Console
- Implement proper error handling for rate limit responses

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Google Cloud Console](https://console.cloud.google.com)
