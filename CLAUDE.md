Preview debounce is down to 90ms, so stepping should feel much snappier.
Before OpenCV tries to play a URL, the app does a short HTTP Range check. Missing/non-video URLs get rejected faster and should avoid most of those OpenCV “couldn’t read stream” failures.
Missing videos are now cached in unavailable_videos.json.
Added “Smart skip known missing videos” in the Explorer tab.
When a preview discovers a missing URL from button navigation, it marks it missing and jumps to the next candidate automatically.
Future clicks skip already-known missing URLs without rechecking them.
