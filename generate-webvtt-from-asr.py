#!/usr/bin/env python3
"""
Generate WebVTT from an input ASR result
"""

import json
import os
import sys


def format_time_cue(t):
    """
    Return a time in seconds in the HH:MM:SS.sss format used in WebVTT
    """

    return "%02d:%02d:%02d.%0.03d" % (
        t // 3600,
        (t % 3600) // 60,
        int(t % 60),
        (t * 1000) % 1000,
    )


def get_lines_from_asr(asr_file):
    asr = json.load(asr_file)

    items = asr["results"]["items"]

    if not items:
        raise RuntimeError("Found no items in %s" % asr_file.name)

    text_accumulator = ""
    current_block_start = current_block_end = 0.0

    for item in items:
        alternatives = item["alternatives"]

        if not alternatives:
            print("Skipping empty item?", item, file=sys.stderr)
            continue
        elif len(alternatives) > 1:
            print(
                "Unexpected multiple alternatives, using the first",
                item,
                file=sys.stderr,
            )

        if "start_time" in item:
            item_start_time = float(item["start_time"])
            item_end_time = float(item["end_time"])

        if item["type"] != "punctuation" and text_accumulator:
            text_accumulator += " "

        if (item_start_time - current_block_end) > 1.0:
            yield current_block_start, current_block_end, text_accumulator
            text_accumulator = ""
            current_block_start = item_start_time

        text_accumulator += item["alternatives"][0]["content"]
        current_block_end = item_end_time

    yield item_start_time, item_end_time, text_accumulator


def convert_asr_to_webvtt(asr_file, webvtt_file):
    print("WEBVTT", file=webvtt_file)
    print(file=webvtt_file)

    for i, (begin_time, end_time, text) in enumerate(get_lines_from_asr(asr_file), 1):
        print(i, file=webvtt_file)
        print(
            "%s --> %s" % (format_time_cue(begin_time), format_time_cue(end_time)),
            file=webvtt_file,
        )
        print(text, file=webvtt_file)
        print(file=webvtt_file)


if __name__ == "__main__":
    for input_filename in sys.argv[1:]:
        output_filename = os.path.join(
            "webvtt", os.path.basename(input_filename).replace("json", "vtt")
        )

        if os.path.exists(output_filename):
            continue

        input_file = open(input_filename, mode="r")
        output_file = open(output_filename, mode="w", encoding="utf-8")

        print(input_filename, "➡️", output_filename)

        try:
            convert_asr_to_webvtt(input_file, output_file)
        except Exception as exc:
            print(f"Failed to convert {input_filename}: {exc}", file=sys.stderr)
            os.unlink(output_filename)
        finally:
            input_file.close()
            output_file.close()
