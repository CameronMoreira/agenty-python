#!/bin/bash

usage() {
>&2 cat << EOF
Deploys an agent team running in Docker.

Usage: $0
   [ -l | --with-group-work-log ] Activates the group work log.
   [ -o | --with-oversight-officer ] Activates the oversight officer.
   [ -s | --with-scenario_server ] Activates the scenario server.
   [ -R | --remote-repo ] Remote repository (either a bare repo, if directory, or a URL to clone).
   [ -T | --team-config ] Team configuration file (default: ./team-config.json).
   [ -h | --help ] Show help.
EOF
exit 1
}

TEAM_CONFIG="./team-config.json"
PROFILES=(agent)
REMOTE_REPO=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -l | --with-group-work-log)
      PROFILES+=("group_work_log")
      shift
      ;;
    -o | --with-oversight-officer)
      PROFILES+=("oversight_officer")
      shift
      ;;
    -s | --with-scenario-server)
          PROFILES+=("scenario_server")
          shift
          ;;
    -R | --remote-repo)
      REMOTE_REPO=$2
      shift 2
      ;;
    -T | --team-config)
      TEAM_CONFIG=$2
      shift 2
      ;;
    -h | --help)
      usage
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      >&2 echo Unsupported option: $1
      usage
      ;;
  esac
done


>&2 echo "============================================================"
>&2 echo "$(realpath $0)"
>&2 echo "PROFILES=(${PROFILES[@]})"
>&2 echo "REMOTE_REPO=${REMOTE_REPO}"
>&2 echo "TEAM_CONFIG=${TEAM_CONFIG}"


# Generate a unique run ID for this simulation
RUN_ID="run_$(date +%Y%m%d_%H%M%S)_${RANDOM}"
export RUN_ID
echo "Generated unique run ID: ${RUN_ID}"

# Undeploy the existing Docker containers, before volume creation
docker compose -f "$(dirname "$0")/../docker-compose.yaml" --profile "*" down

# Force remove the entire project to reset port assignment state
>&2 echo "Removing entire agents project to reset port assignment..."
docker compose -f "$(dirname "$0")/../docker-compose.yaml" --profile "*" down --remove-orphans --volumes >/dev/null 2>&1

# Force remove any existing agent containers to ensure clean port assignment
>&2 echo "Removing any existing agent containers..."
docker ps -a --filter "name=agents-agent" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null

# Kill any processes using ports 8081-8088 to ensure they're available
>&2 echo "Clearing ports 8081-8083..."
for port in {8081..8083}; do
  # Kill any host processes using the port (rare when running inside Docker but
  # helpful when debugging locally)
  if lsof -ti:$port >/dev/null 2>&1; then
    lsof -ti:$port | xargs -r kill -9
    >&2 echo "Killed host process using port $port"
  fi
  # Stop any docker containers that still expose the port (e.g., from a
  # previous interrupted run) so that the upcoming compose can bind 8081/8082
  container_ids=$(docker ps -q --filter "publish=$port")
  if [ -n "$container_ids" ]; then
    docker rm -f $container_ids >/dev/null 2>&1
    >&2 echo "Removed Docker containers binding port $port"
  fi
done

# Wait a moment for ports to be fully released
sleep 2

# Remove previous volume if it exists
if docker volume inspect agents_git_remote &>/dev/null; then
  docker volume rm agents_git_remote
fi

# Copy the team's task to the .env file
team_task=$(jq -r '(.task | gsub("\n"; " "))' $TEAM_CONFIG)
if grep -q '^INITIAL_GROUP_CHAT_MESSAGE=' "$(dirname "$0")/../.env"; then
  sed -i '' "s|^INITIAL_GROUP_CHAT_MESSAGE=.*|INITIAL_GROUP_CHAT_MESSAGE=\"$team_task\"|" "$(dirname "$0")/../.env"
else
  echo "INITIAL_GROUP_CHAT_MESSAGE=\"$team_task\"" >> "$(dirname "$0")/../.env"
fi

# Retrieve the agent count from the team configuration
agent_count=$(jq '.agents | length' $TEAM_CONFIG)
# Make the count available to Docker Compose so that services (e.g., scenario_server)
# can read it via the AGENT_COUNT environment variable.
export AGENT_COUNT=$agent_count
if [ "$agent_count" -lt 1 ]; then
  echo "Error: At least 1 agent is required."
  exit 1
fi

# Set the number of agents to deploy equal to the agent count in the team configuration
# (This allows running a single-agent setup as well as multi-agent setups.)
deploy_count=$agent_count

# Warn the user if the agent count exceeds the number of statically
# exposed host ports in docker-compose.yaml (currently 3 → 8081-8083).
max_supported_agents=3
if [ "$agent_count" -gt "$max_supported_agents" ]; then
  >&2 echo "Warning: Team config has $agent_count agents, but docker-compose.yaml only maps $max_supported_agents ports (8081-8083). Only the first $max_supported_agents agents will be accessible on the host."
fi

# Launch the Docker containers with the specified profiles and the desired number of agents
docker compose -f "$(dirname "$0")/../docker-compose.yaml" $(printf -- '--profile %s ' "${PROFILES[@]}") up \
  -d --scale agent=$deploy_count --build --force-recreate
