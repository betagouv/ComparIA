import google.auth
import google.auth.transport.requests
import openai

# Programmatically get an access token
# creds, project = google.auth.default()
creds, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)
# Note: the credential lives for 1 hour by default (https://cloud.google.com/docs/authentication/token-types#at-lifetime); after expiration, it must be refreshed.

# Pass the Vertex endpoint and authentication to the OpenAI SDK
PROJECT = project
client = openai.OpenAI(
    base_url = f'https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{PROJECT}/locations/us-central1/endpoints/openapi',
    api_key = creds.token)

# print(client.models.list())