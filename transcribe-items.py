#!/usr/bin/env python -u
"""Queue files listed in a manifest for AWS Transcribe"""

import argparse
import fileinput
import os
import sys
import tempfile
import time
from urllib.parse import urljoin, urlparse

import boto3
import botocore
import requests

SUPPORTED_FILE_TYPES = ("mp3", "mp4", "wav", "flac")

SUPPORTED_LANGUAGES = {"english": "en-US", "spanish": "es-US"}

s3 = boto3.client("s3")
transcribe = boto3.client("transcribe")


def transcribe_item(job_name, s3_url, media_format="wav", language_code="en-US"):
    return transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_url},
        MediaFormat=media_format,
        LanguageCode=language_code,
        Settings={"VocabularyName": "LCCoreTerms"},
    )


def upload_audio_to_s3(audio_url, bucket_name, dest_key):
    try:
        s3.head_object(Bucket=bucket_name, Key=dest_key)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise
    else:
        print(f"{dest_key} already exists; won't repeat upload", file=sys.stderr)
        return

    with tempfile.NamedTemporaryFile(mode="w+b") as local_temp:
        r = requests.get(audio_url, stream=True, allow_redirects=True)
        r.raise_for_status()
        content_type = r.headers["Content-Type"]

        for chunk in r.iter_content(chunk_size=256 * 1024):
            local_temp.write(chunk)
        local_temp.flush()
        local_temp.seek(0)

        s3.upload_fileobj(
            local_temp, bucket_name, dest_key, ExtraArgs={"ContentType": content_type}
        )


def main(bucket_name, files):
    for line in fileinput.input(files):
        if line.count("\t") != 5:
            print("Skipping malformed line:", repr(line), file=sys.stderr)
            continue

        item_id, language, title, url, media_master_url, media_stream_url, = map(
            str.strip, line.split("\t", 5)
        )

        # FIXME: add some configuration management
        if os.path.exists(os.path.join("results", "%s.json" % item_id)):
            print("Skipping completed item", item_id)
            continue

        if language not in SUPPORTED_LANGUAGES:
            print(
                "Transcribe currently does not support %s" % language, file=sys.stderr
            )
            continue
        lang = SUPPORTED_LANGUAGES[language]

        parsed_audio_url = urlparse(media_master_url)
        _, file_ext = os.path.splitext(parsed_audio_url.path)
        file_ext = file_ext.strip(".")

        if file_ext not in SUPPORTED_FILE_TYPES:
            print("Transcribe does not support %s files" % file_ext, file=sys.stderr)
            continue

        try:
            existing_job = transcribe.get_transcription_job(
                TranscriptionJobName=item_id
            )
            print(
                "Not reprocessing existing job %s: %s"
                % (item_id, existing_job["TranscriptionJob"]["TranscriptionJobStatus"])
            )
            continue
        except botocore.exceptions.ClientError:
            # Unfortunately the AWS response doesn't give a better option to
            # disambiguate error conditions than scraping error messages but
            # we'll punt any other error to the start job error path
            pass

        s3_path = f"{item_id}.{file_ext}"

        print(f"Uploading {item_id} “{title}” to {s3_path}…")

        try:
            upload_audio_to_s3(media_master_url, bucket_name, s3_path)
        except Exception as exc:
            print(f"Unable to upload {media_master_url}: {exc}", file=sys.stderr)
            continue

        s3_url = urljoin(s3.meta.endpoint_url, "%s/%s" % (bucket_name, s3_path))

        print(f"Transcribing {item_id} from {s3_url}")

        for i in range(0, 30):
            try:
                transcribe_item(
                    item_id, s3_url, media_format=file_ext, language_code=lang
                )
                break
            except botocore.exceptions.ClientError as exc:
                if exc.response["Error"]["Code"] == "400":
                    print("Rate-limiting…")
                    time.sleep(1 + (5 * i))
                    continue
                else:
                    print(
                        f"Unexpected API response for {item_id}: {exc}", file=sys.stderr
                    )
                    break
            except Exception as exc:
                print(f"Unable to transcribe {item_id}: {exc}", file=sys.stderr)
                continue

        time.sleep(
            0.5
        )  # FIXME: develop a more comprehensive solution for AWS throttling


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument("--bucket", help="S3 bucket name which Transcribe can access")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    main(args.bucket, args.files)
