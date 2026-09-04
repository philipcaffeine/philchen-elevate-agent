# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Service Identities required for Discovery Engine and Dialogflow
resource "google_project_service_identity" "discoveryengine_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "discoveryengine.googleapis.com"

  depends_on = [google_project_service.services]
}

resource "google_project_service_identity" "dialogflow_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "dialogflow.googleapis.com"

  depends_on = [google_project_service.services]
}

# Discovery Engine Data Store for Altostrat HR Policy
resource "google_discovery_engine_data_store" "hr_policy_datastore" {
  provider          = google-beta
  project           = var.project_id
  location          = "global"
  collection_id     = "default_collection"
  data_store_id     = "hr-policy-datastore"
  display_name      = "HR Policy Data Store"
  industry_vertical = "GENERIC"
  content_config    = "NO_CONTENT"
  solution_types    = ["SOLUTION_TYPE_CHAT"]

  depends_on = [
    google_project_service.services,
    google_project_service_identity.discoveryengine_sa,
    google_project_service_identity.dialogflow_sa
  ]
}

# Discovery Engine Chat Engine / Gemini App
resource "google_discovery_engine_chat_engine" "hr_gemini_app" {
  provider       = google-beta
  project        = var.project_id
  location       = "global"
  collection_id  = "default_collection"
  engine_id      = "altostrat-hr-gemini-app"
  display_name   = "Altostrat HR Gemini App"
  data_store_ids = [google_discovery_engine_data_store.hr_policy_datastore.data_store_id]
  app_type       = "APP_TYPE_INTRANET"

  chat_engine_config {
    agent_creation_config {
      default_language_code = "en"
      time_zone             = "Asia/Singapore"
    }
  }

  depends_on = [
    google_project_service.services,
    google_discovery_engine_data_store.hr_policy_datastore
  ]
}

# Register the Agent Runtime Reasoning Engine into the Gemini App
resource "null_resource" "publish_agent_to_gemini_app" {
  triggers = {
    agent_runtime_id = google_vertex_ai_reasoning_engine.app.name
    gemini_app_id    = google_discovery_engine_chat_engine.hr_gemini_app.name
  }

  provisioner "local-exec" {
    command = <<-EOT
      python3 -c "
import urllib.request, json, subprocess

token = subprocess.check_output(['gcloud', 'auth', 'print-access-token']).decode().strip()
project_num = subprocess.check_output(['gcloud', 'projects', 'describe', '${var.project_id}', '--format=value(projectNumber)']).decode().strip()

url = f'https://discoveryengine.googleapis.com/v1alpha/projects/{project_num}/locations/global/collections/default_collection/engines/altostrat-hr-gemini-app/assistants/default_assistant/agents'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'x-goog-user-project': '${var.project_id}'
}
payload = {
    'displayName': 'Altostrat HR Policy Agent',
    'description': 'Enterprise HR Virtual Assistant for Policy Q&A, WorkWeek HCM, and ServiceImmediately ITSM',
    'icon': {'uri': 'https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg'},
    'adk_agent_definition': {
        'tool_settings': {'tool_description': 'Answers HR policy queries, leave balance inquiries, and ITSM requests'},
        'provisioned_reasoning_engine': {'reasoning_engine': '${google_vertex_ai_reasoning_engine.app.name}'}
    }
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        print('Successfully registered agent with Gemini App:', resp.read().decode('utf-8'))
except Exception as e:
    print('Notice on publish agent to Gemini App:', e)
"
    EOT
  }

  depends_on = [
    google_vertex_ai_reasoning_engine.app,
    google_discovery_engine_chat_engine.hr_gemini_app
  ]
}
