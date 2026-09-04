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

output "gemini_app_console_url" {
  description = "Console URL for Gemini Enterprise App overview and management"
  value       = "https://console.cloud.google.com/gemini-enterprise/locations/global/engines/${google_discovery_engine_chat_engine.hr_gemini_app.engine_id}/overview/dashboard?project=${var.project_id}"
}

output "gemini_app_id" {
  description = "Full resource name of Gemini Enterprise App"
  value       = google_discovery_engine_chat_engine.hr_gemini_app.name
}

output "gemini_app_engine_id" {
  description = "Engine ID of the Gemini Enterprise App"
  value       = google_discovery_engine_chat_engine.hr_gemini_app.engine_id
}

output "gemini_app_dialogflow_agent" {
  description = "Dialogflow Agent associated with the Gemini Enterprise App"
  value       = google_discovery_engine_chat_engine.hr_gemini_app.chat_engine_metadata[0].dialogflow_agent
}

output "agent_runtime_console_url" {
  description = "Vertex AI Agent Runtime Console URL"
  value       = "https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/${var.region}/agent-engines/${split("/", google_vertex_ai_reasoning_engine.app.name)[5]}?project=${var.project_id}"
}
