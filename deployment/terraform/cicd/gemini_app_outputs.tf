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

output "gemini_app_console_urls" {
  description = "Console URLs for Gemini Enterprise Apps across environments"
  value = {
    for k, v in google_discovery_engine_chat_engine.hr_gemini_app :
    k => "https://console.cloud.google.com/gemini-enterprise/locations/global/engines/${v.engine_id}/overview/dashboard?project=${local.deploy_project_ids[k]}"
  }
}

output "gemini_app_ids" {
  description = "Full resource names of Gemini Enterprise Apps"
  value = {
    for k, v in google_discovery_engine_chat_engine.hr_gemini_app :
    k => v.name
  }
}
