# Run MIDI Maker on AWS Lambda (works from an iPad, Mac off)

The Lambda version is the same server in a container, behind the
[AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) with response streaming.
The page sends one request to `/api/convert`; the server streams progress lines (which keeps Safari from
timing out) and finishes with the MIDI file.

## 1. Memory quota (new AWS accounts)

New accounts often cap Lambda memory at 3008 MB. Demucs needs more, so request an increase first:
**Service Quotas → AWS services → AWS Lambda → "Function memory"** (or the Lambda console banner) → request 10240 MB.
It is free and usually approved quickly.

## 2. Build and push the image (AWS CloudShell, no local Docker needed)

Open **CloudShell** (the `>_` icon in the AWS console top bar). Pick the region you'll use for everything.

```bash
git clone https://github.com/Jodeit/midi_maker.git && cd midi_maker
REGION=$AWS_REGION; ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/midi-maker
aws ecr create-repository --repository-name midi-maker
aws ecr get-login-password | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker build -f Dockerfile.lambda -t $REPO:latest .
docker push $REPO:latest
```

The image is a few GB. If CloudShell runs out of disk during the build, build on any computer with Docker instead
(add `--platform linux/amd64` on Apple Silicon) and push the same way.

## 3. Create the function

1. **Lambda → Create function → Container image**, name `midi-maker`, browse to the `midi-maker:latest` image, architecture **x86_64**.
2. **Configuration → General configuration**: memory **10240 MB**, timeout **15 min**, ephemeral storage **4096 MB**.
3. **Configuration → Environment variables**: `MIDI_MAKER_KEY` = a long random string (this is your access key).
4. **Configuration → Function URL → Create**: auth type **NONE**, invoke mode **RESPONSE_STREAM**. Leave CORS off (the app sets its own headers).

## 4. Use it

On the iPad open (replace the values):

```
https://jodeit.github.io/midi_maker/?backend=<function URL without trailing slash>&key=<your key>&mode=stream
```

Paste a YouTube or Instagram link and tap **Make MIDI**. Keep the page open and the screen on while it works.
The first request after a quiet period is slower (the container has to start).

## Cost

Compute is billed in GB-seconds: memory (GB) × run time. At 10 GB, a 5-minute run is about 3,000 GB-seconds, so a
400,000 GB-second monthly free allowance covers roughly 130 such runs. Check AWS's current pricing and free-tier terms.

## Known limits

- **Downloads can be blocked.** YouTube and Instagram often refuse requests from cloud servers. If a link fails with a
  sign-in or bot error, there isn't an easy fix on Lambda: environment variables are limited to 4 KB total, too small for
  a cookies file. Fallback: run the app on a Mac and AirDrop the MIDI.
- Anyone with the Function URL and the key can run jobs on your account. Keep the key private and rotate it
  (change `MIDI_MAKER_KEY`) if it leaks. Consider setting a reserved-concurrency limit of 1–2 as a cost guard.
