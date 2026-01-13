# Privacy Policy - Mudrex Paper Trading API

**Last Updated:** January 13, 2026

## Overview

The Mudrex Paper Trading API is a simulation service that allows users to practice cryptocurrency trading with virtual funds. This privacy policy explains how we handle your data when you use this service.

## Data Collection

### What We Collect

- **Session Data**: Temporary session identifiers and trading simulation data
- **Trading Activity**: Simulated trades, positions, and balances (all virtual)
- **API Usage**: Standard server logs for debugging and service improvement

### What We DON'T Collect

- ❌ **No Personal Information**: We do not collect names, emails, addresses, or any personally identifiable information
- ❌ **No Real Financial Data**: This is a simulation - no real money, accounts, or financial information is involved
- ❌ **No Authentication**: No login credentials or authentication tokens are stored
- ❌ **No Persistent Storage**: All session data is stored in memory and cleared when the server restarts

## How We Use Your Data

- **Service Operation**: Session data is used solely to maintain your paper trading simulation state
- **No Sharing**: We do not share, sell, or distribute any data to third parties
- **No Tracking**: We do not track users across sessions or websites

## Data Storage

- **In-Memory Only**: All session data is stored in server memory (RAM)
- **Temporary**: Sessions are automatically cleared when:
  - The server restarts
  - A session is explicitly deleted
  - A session is inactive for an extended period
- **No Database**: We do not use persistent databases for user data
- **No Backups**: Session data is not backed up or archived

## Data Security

- **Simulation Only**: Since this is a paper trading simulation with no real money, there is no financial risk
- **No Sensitive Data**: We do not store sensitive personal or financial information
- **Standard Security**: We follow standard web security practices (HTTPS, CORS protection)

## Third-Party Services

- **Hosting**: The service may be hosted on platforms like Railway, Render, or similar cloud providers
- **No Data Sharing**: We do not share your session data with hosting providers beyond what is necessary for service operation

## Your Rights

- **Delete Session**: You can delete your session at any time using the `/session` DELETE endpoint
- **No Data Retention**: Since data is not persisted, there is no data to retrieve or delete after session expiration
- **Transparency**: All API endpoints and data structures are documented in the OpenAPI specification

## Children's Privacy

This service is intended for educational purposes. We do not knowingly collect data from children under 13. Since we do not collect personal information, this is not applicable.

## Changes to This Policy

We may update this privacy policy from time to time. The "Last Updated" date at the top indicates when changes were made.

## Contact

For questions about this privacy policy, please open an issue on GitHub:
https://github.com/DecentralizedJM/mudrex-futures-API-papertrading-py-sdk/issues

## Disclaimer

**This is a paper trading simulation service.**
- No real money is involved
- No real trades are executed
- All data is temporary and simulation-only
- This service is for educational and testing purposes only

---

**By using this service, you acknowledge that:**
1. This is a simulation with no real financial transactions
2. All session data is temporary and may be lost at any time
3. No personal or financial data is collected or stored
4. You use this service at your own discretion
