# Step 6: the video

```
python3 S/scripts/motion.py
```

Builds `out/<handle>-<year>-year-in-review.mp4`: 1080x1920, H.264, 24 fps, 45-60 s, no sound. Each chapter is its
photos under a slow push-in with the words held sharp on top; the words slide in, the beats crossfade, and each
chapter's `line` is burned in as a caption. The first frame is already the finished opener, so the thumbnail
works. It takes about 20 s.

Music: only when the person gave a music file, `python3 S/scripts/motion.py --music <file>`. Never download or
invent music; the brief says the video is silent and they can add a sound when they post.
