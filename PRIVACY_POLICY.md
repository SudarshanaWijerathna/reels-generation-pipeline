# Privacy Policy for Reels Generation & Publishing Pipeline

**Effective Date:** August 3, 2026

## 1. Overview
This Privacy Policy describes how the **Reels Generation & Publishing Pipeline** ("we", "us", or "our") handles data when integrating with Meta APIs (Facebook Graph API and Instagram Graph API). We are committed to respecting your privacy and protecting any information processed through our application.

## 2. Information We Collect and Process
When you authorize and interact with our application via Meta APIs, we may process the following limited technical data:
- **Meta Page / Account Identification:** Facebook Page IDs and Instagram Business Account IDs required to target content publishing.
- **API Access Tokens:** Short-lived and long-lived OAuth access tokens granted by users to perform authorized automated actions.
- **Media Content Metadata:** Captions, video titles, and media files generated or scheduled for publication.

**We DO NOT collect, store, or sell any personal user data, personal profiles, friends lists, or private messages.**

## 3. How We Use Information
The collected technical information is strictly used for the following operational purposes:
- Authenticating requests to the Meta Graph API.
- Automatically uploading and publishing video reels to your authorized Facebook Pages and Instagram accounts.
- Checking post status and logging publishing execution history locally.

## 4. Data Sharing and Third Parties
- **No Data Selling or Sharing:** We do not sell, rent, trade, or share any access tokens, account details, or media data with third parties.
- **Third-Party Services:** All API requests are transmitted directly and securely to official Meta / Facebook API endpoints (`graph.facebook.com`).

## 5. Security and Data Retention
- API tokens and credentials are stored securely in encrypted environment variables or secrets managers.
- Access tokens are retained only as long as necessary to maintain authorized API connectivity.
- Local publish logs contain only public post IDs and timestamp metadata.

## 6. User Control & Data Deletion / Revocation
You retain full control over your connected Meta accounts:
- **Revoking Permissions:** You can revoke access at any time by visiting your [Facebook Business Integrations Settings](https://www.facebook.com/settings?tab=business_tools).
- **Data Deletion:** Upon revoking access or requesting deletion, all locally stored access tokens associated with your account are immediately deleted.

## 7. Contact Us
If you have any questions or concerns regarding this Privacy Policy, please contact the repository administrator via GitHub issues at [https://github.com/SudarshanaWijerathna/reels-generation-pipeline](https://github.com/SudarshanaWijerathna/reels-generation-pipeline).
