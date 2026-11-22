# YouTube API audit form — answers used (22 Nov 2026)
Form: https://support.google.com/youtube/contact/yt_api_form

## Section 1
Complete a compliance audit to request for additional quota

## Section 2
Individual user · Organization legal name: self · Parent: self · Website: https://goodwillonlinetuition.com
Address: India, Thevara, Ernakulam, Kerala + PIN · Category: Education (or closest) · Size: Independent Developer/Sole Proprietor
Primary contact: own name + rainytp@gmail.com · Technical and Business contact: Same as Primary

## Section 3
Organization's work: (text below)
Goodwill Tuition Centre (Ernakulam, Kerala, India) teaches Accountancy and Cost Accounting online to CBSE Class 11-12 and university B.Com students. We publish our own short educational videos on our YouTube channel almost every day: solved textbook questions explained step by step. The API client is a small Python script that runs only on my own PC. It uploads our own finished videos to our own channel (videos.insert) with title, description, tags, category and privacy, and adds each video to the right playlist on our channel (playlists.list, playlistItems.insert). It saves the teacher time on manual uploads so we can keep publishing free lessons for students. The tool has no other users, no public interface, does not access other channels' data and does not store or share any YouTube data.
Audience: Internal Users · Monetization: Free service · Google rep: No · Learned from: Google developer documentation

## Section 4
API Client Name: Goodwill Video Uploader · Contains "YouTube": No · Primary URL: https://goodwillonlinetuition.com
Privacy Policy: https://www.goodwillonlinetuition.com/privacy-policy · Publicly accessible: No · Demo credentials: empty
Special instructions: Internal-only command-line tool that runs on the channel owner's own PC; there is no website, login page or demo account. An end-to-end screencast of the tool uploading a video to our own channel is linked in Section 6.
Acknowledgment: ticked

## Section 5
Projects: 1 · Project number: 440497871188 · Use case: Video Uploading & Account Management + Internal Company Tool · OAuth: Yes
Usage: Fewer than 1,000 requests per day · Endpoints: videos.insert, playlists.list, playlists.insert, playlistItems.insert, channels.list · Quota: No change / Default
Files: privacy screenshot (section 2 of the privacy page), homepage.png, tools/audit/terms-of-service.pdf, tools/audit/upload-script.pdf

## Still to do
Section 6, Section 7, submit. Then rename the OAuth app (Branding page) from "Goodwill YouTube Upload" to "Goodwill Video Uploader".
