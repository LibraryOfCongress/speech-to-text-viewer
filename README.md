# Speech-to-Text Result Viewer

This is a little tooling around [AWS Transcribe](https://aws.amazon.com/transcribe/)
to allow us to evaluate the service quality.

See http://speechtotextviewer.s3-website.us-east-2.amazonaws.com/ for the current public release.

## Getting Started

1. Have Python 3.7 and [Pipenv](https://pipenv.org) installed
1. Have your environment [configured with the credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) for the AWS account which you intend to use. If you are using multiple accounts, either set [AWS_PROFILE](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) or use a tool such as `aws-vault` to prefix the transcription and download commands.
1. `pipenv install --python 3.7`
1. Prepare a tab-separated manifest file with the following fields in order:

    - identifier
    - language
    - Title
    - Page to view more information about the file (this will be the more information link)
    - High-quality original master URL (if the URL starts with `s3://` it will be passed in directly with no checks; otherwise it will be uploaded to the specified S3 bucket)
    - Streamable audio URL (this will be used by the embedded player)

    Here's an example manifest entry which will be uploaded to S3 before processing:

    ```tsv
    afc1941004_sr01    english    "Man-on-the-Street," Washington, D.C., December 8, 1941    https://www.loc.gov/item/afc1941004_sr01/    http://cdn.loc.gov/master/afc/afc1941004/afc1941004_sr01a/afc1941004_sr01a.wav    http://cdn.loc.gov/service/afc/afc1941004/afc1941004_sr01a/afc1941004_sr01a.mp3
    ```

    Here's an example manifest entry using a pre-existing S3 object which will be passed directly to Transcribe:

    ```tsv
    afc1941004_sr01a	english	"Man-on-the-Street," Washington, D.C., December 8, 1941	https://www.loc.gov/item/afc1941004_sr01/	s3://my-source-bucket/afc/afc1941004/afc1941004_sr01a/afc1941004_sr01a.mp3	https://cdn.loc.gov/service/afc/afc1941004/afc1941004_sr01a/afc1941004_sr01a.mp3
    ```

1. Submit the items for transcription. Plese note that this is the point where you will incur charges for the service.

    ```shell
    $ pipenv run python transcribe-items.py my-items.tsv
    Uploading afc1941004_sr01 “"Man-on-the-Street," Washington, D.C., December 8, 1941” to …
    Transcribing afc1941004_sr01 from …
    …
    ```

1. Type `make` to download the results, which may take a number of minutes to become available. The process is repeatable and will not reprocess transcriptions which have already been downloaded.

1. Once at least a single item has been downloaded, you can load the viewer from the local directory (e.g. `pipenv run python -m http.server`)

1. Uploading to a remote server is as simple as uploading contents of this working directory. `make upload` will do this once you change the target bucket name for the S3 sync command.
