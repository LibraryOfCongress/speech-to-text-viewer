#!/usr/bin/env python3

import fileinput
import json
import os

items = {}

for line in fileinput.input():
    fields = list(i.strip() for i in line.split("\t"))

    if len(fields) == 5:
        item_id, language, title, item_url, media_master_url = fields
        media_stream_url = media_master_url
    else:
        item_id, language, title, item_url, media_master_url, media_stream_url = fields

    if not os.path.exists("results/%s.json" % item_id):
        continue

    items[item_id] = {
        "language": language,
        "title": title,
        "item_url": item_url,
        "media_master_url": media_master_url,
        "media_stream_url": media_stream_url,
    }

with open("index.json", "w") as f:
    json.dump(items, f)
