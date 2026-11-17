# Privacy

This plugin connects Dify to your Rollstack account. It sends the calls your Dify app makes to Rollstack and returns Rollstack's answers. It collects nothing for itself: it has no storage, writes no logs, and sends no analytics or data to anyone but Rollstack.

## What the plugin handles

| Data | Where it comes from | Where it goes |
| --- | --- | --- |
| Your Rollstack API key | You enter it in Dify, which stores it encrypted with the plugin's credentials | Sent to Rollstack as a bearer token with every call. The plugin never returns it, and never writes it to a log or an error message |
| What you pass to a tool: report ids and names, your messages to the slides agent, schedules, links to decks to import | Your Dify app, or the model that runs it | Sent to Rollstack to carry out the call |
| What Rollstack answers: reports and their settings, what slides show, the slides agent's replies, runs, schedules, export links | Rollstack | Returned to your Dify app, which may pass it on to the model and the users of that app |

Rollstack's answers can hold personal data of members of your Rollstack organization: the name and email address of a report's owner, of the members it is shared with, and of the people told when a run fails, and whatever your reports themselves show. A message you write to the slides agent can hold any personal data you put in it.

The plugin itself collects no direct identifiers, no device or location data, and nothing about how you use it.

## Where data goes

- **Rollstack** (`api.rollstack.com`) is the only service the plugin calls, over HTTPS. Rollstack handles what it receives under its privacy policy: https://www.rollstack.com/legal/privacy-policy. Your key acts as the Rollstack user who created it, so a call can read or change only what that user can in Rollstack.
- **Dify** runs the plugin and stores the API key, your app's inputs and the tool results, under Dify's own terms and privacy policy, or under yours when you host Dify yourself.

No other third party receives data from the plugin.

## Retention and removal

The plugin keeps nothing between calls. To stop it from reaching your Rollstack account, remove the key from the plugin in Dify, or revoke it in Rollstack under Settings → Connected apps, where every key is listed. A link from the export tool lets anyone who has it download the file for 15 minutes; after that it stops working.

To access or delete data held by Rollstack, see its privacy policy above.

## Contact

support@rollstack.com
