#!/usr/bin/env python -u
"""Download completed AWS Transcribe jobs"""

import json
import os
import sys
import time

import boto3
import botocore
import requests

transcribe = boto3.client("transcribe")


def get_completed_jobs():
    next_token = ""
    # boto3 will throw an error if you provide an empty NextToken but it doesn't
    # have a no-value placeholder so we'll abuse kwargs:
    kwargs = {}

    while True:
        try:
            response = transcribe.list_transcription_jobs(Status="COMPLETED", **kwargs)
        except botocore.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] == "ThrottlingException":
                print("Rate-limiting encountered; will retry in 5 seconds…")
                time.sleep(5)
                continue
            else:
                print("Error while listing jobs:", exc, file=sys.stderr)
                raise

        for summary in response["TranscriptionJobSummaries"]:
            yield summary["TranscriptionJobName"]

        next_token = response.get("NextToken")
        if not next_token:
            break
        else:
            kwargs["NextToken"] = next_token


def download_completed_jobs(results_directory):
    for job_name in get_completed_jobs():
        output_name = os.path.join(results_directory, "%s.json" % job_name)

        if os.path.exists(output_name):
            continue

        results = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        transcript_url = results["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        print(f"Retrieving {job_name}")

        resp = requests.get(transcript_url)
        if not resp.ok:
            print(
                f"{job_name}: HTTP {resp.status_code} {resp.reason} {transcript_url}",
                file=sys.stderr,
            )
            continue

        with open(output_name, "w+") as output_file:
            json.dump(resp.json(), output_file)


if __name__ == "__main__":
    # FIXME: add some command-line parsing:
    base_dir = os.path.realpath("results")

    download_completed_jobs(base_dir)
