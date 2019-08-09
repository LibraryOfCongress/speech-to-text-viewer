.PHONY: download index webvtt upload

all: download index webvtt

download:
	pipenv run python download-transcripts.py

index:
	pipenv run python index-transcripts.py *.tsv

webvtt:
	pipenv run python generate-webvtt-from-asr.py results/*.json

upload:
	aws s3 sync --acl public-read --exclude=.* --exclude=\*.py --exclude=\*.tsv --exclude=package.json --exclude=node_modules\* --exclude=Makefile --exclude=Pipfile\* --exclude=yarn.lock ./ s3://speechtotextviewer/
