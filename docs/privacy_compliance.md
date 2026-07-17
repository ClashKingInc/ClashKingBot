# Privacy Compliance Notes

ClashKing Bot operates inside Discord servers and can connect Discord identities to Clash of Clans player tags, rosters, reminders, tickets, strikes, roles, and server configuration. Those links are personal data for global privacy regimes.

## Data handled here

- Discord user IDs, usernames/display names, avatars, guild IDs, channel IDs, role IDs, and server configuration.
- Clash of Clans player tags, clan tags, API-token verification results, account links, rosters, reminders, tickets, strikes, and application records.
- Uploaded attachments/transcripts stored through the configured CDN for ticketing and support workflows.
- Command usage and operational statistics.

## User rights process

For verified requests, operators must be able to:

- Export Discord-linked records, including linked player tags, reminders, roster entries, tickets owned by the user, strike records, profile/settings entries, and command/account-link metadata.
- Delete or anonymize Discord-linked records where there is no overriding security, audit, or legal reason to retain them.
- Unlink Clash of Clans player tags from the requesting Discord user through the link client and local collections.
- Remove CDN ticket transcripts or attachments owned by the requester when they are no longer required for moderation or legal obligations.

## Collection limits

- Do not store Clash of Clans API tokens after verification.
- Do not expose Discord OAuth/client secrets, bot tokens, CDN keys, or database credentials in logs or command output.
- Keep moderation/audit records access-restricted to server operators with a valid need.
- Avoid sending personal data in public channels; use ephemeral responses or direct messages for account-link and privacy workflows where possible.

## Global deployment checklist

- GDPR/UK GDPR/LGPD/PIPEDA/APPI/PIPL/PDPA: access, deletion, correction, portability, minimization, retention, and security.
- CCPA/CPRA: disclosure, deletion/correction, and no sale/share for behavioral advertising.
- COPPA/children rules: do not knowingly collect children-specific data; rely on Discord/App Store/Google Play age gates and remove data if a child-data request is verified.
- ePrivacy and push messaging: only send notification/reminder messages that users or server administrators configured, and honor opt-outs promptly.
