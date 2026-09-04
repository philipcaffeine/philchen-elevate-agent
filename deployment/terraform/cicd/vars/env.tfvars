# Project name used for resource naming
project_name = "altostrat-hr-agent"

# Your Production Google Cloud project id
prod_project_id = "philchen-project-elevate"

# Your Staging / Test Google Cloud project id
staging_project_id = "philchen-project-elevate"

# Your Google Cloud project ID that will be used to host the Cloud Build pipelines.
cicd_runner_project_id = "philchen-project-elevate"
# Name of the host connection you created in Cloud Build
host_connection_name = "git-philchen-elevate-agent"
github_pat_secret_id = "github_pat_token"

repository_owner = "philipcaffeine"

# Name of the repository you added to Cloud Build
repository_name = "philchen-elevate-agent"

# The Google Cloud region you will use to deploy the infrastructure
region = "asia-southeast1"
