AUDIO EQUIPMENT TRACKER
=======================
A personal catalogue of second-hand audio listings, built only from screenshots
on your own computer. It never opens, logs into or reads Facebook.

START
-----
Double-click "Start Tracker.bat".
- A black window opens. Keep it open while you use the catalogue.
- New screenshots are read automatically and the catalogue opens in your browser
  (http://127.0.0.1:8765/).
- Press "Scan for new screenshots" on the page after more screenshots arrive.
- To stop, close the black window.

SETTINGS
--------
settings.ini (open with Notepad):
- screenshot_folder  where your screenshots arrive (read-only; nothing is moved,
                     renamed or deleted)
- port               web page port (default 8765)

WHERE YOUR DATA IS
------------------
data\tracker.db      the one database file (items, price history, raw OCR text)
data\thumbs\         small copies of screenshots for the cards
data\backups\        backups made with the Backup button
data\exports\        JSON exports
data\tracker.log     error log (in plain English)

BACKUP
------
Press "Backup" on the page. A copy is saved as
data\backups\tracker_YYYY-MM-DD_HHMMSS.db
To restore: close the tracker, copy a backup over data\tracker.db
(rename it to tracker.db), and start again.
"Export JSON" saves everything (all items, prices, raw OCR text) to data\exports\.
For extra safety, copy the data folder to a pen drive or Google Drive now and then.

HOW IT DECIDES
--------------
- Price: accepted only with ₹ / Rs / INR (or "Free"). If unclear it is left blank
  and the item is marked "Needs checking" - a price is never guessed.
- Repeat screenshot of the same listing: matched by the listing photo plus title
  and seller. Its price goes into the item's price history (a line is added only
  when the price changes). Unsure matches appear under "Possible duplicates".
- Deal score: an offline rule (not AI) using your target price, the new price,
  and the price drop. Hover over the badge to see why.

PORTER TRANSPORT ESTIMATE
-------------------------
Each card shows the estimated Porter fare from the listing's town to your home
(settings.ini [transport] home = Puthiyakavu, Tripunithura) and the TOTAL cost
(asking price + transport). Target price and deal score use the total cost.
- Distance: town centre to home x 1.3 for road bends. Unknown town: type the km.
- Two-wheeler fare is learned from your real fares (settings.ini two_wheeler_fares)
  plus every "Porter fare" you type on a card - so it improves as you use it.
- Three-wheeler / mini truck use a rough multiplier until you type one real fare.

TEST
----
py tests\test_pipeline.py     (uses made-up sample screenshots and a temporary
                               folder - your real data is not touched)
