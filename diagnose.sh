#!/bin/bash
# ┌───────────────────────────────────────────────────────────────────────────┐
# │ Configuration                                                             │
# └───────────────────────────────────────────────────────────────────────────┘
#
# The complete path of the CRCON folder
# - If not set (ie : CRCON_folder_path=""), it will try to find and use
#   any "hll_rcon_tool" folder on disk.
# - If your CRCON folder name isn't 'hll_rcon_tool', you must set it here.
# - Some Ubuntu distros disable 'root' user,
#   your CRCON could then be found in "/home/ubuntu/hll_rcon_tool".
# default : "/root/hll_rcon_tool"
CRCON_folder_path="/root/hll_rcon_tool"

#
# └───────────────────────────────────────────────────────────────────────────┘

is_CRCON_configured() {
  printf "%s└ \033[34m?\033[0m Testing folder : \033[33m%s\033[0m\n" "$2" "$1"
  if [ -f "$1/compose.yaml" ] && [ -f "$1/.env" ]; then
    printf "%s  └ \033[32mV\033[0m A configured CRCON install has been found in \033[33m%s\033[0m\n" "$2" "$1"
  else
    missing_env=0
    missing_compose=0
    wrong_compose_name=0
    deprecated_compose=0
    if [ ! -f "$1/.env" ]; then
      missing_env=1
      printf "%s  └ \033[31mX\033[0m Missing file : '\033[37m.env\033[0m'\n" "$2"
    fi
    if [ ! -f "$1/compose.yaml" ]; then
      missing_compose=1
      printf "%s  └ \033[31mX\033[0m Missing file : '\033[37mcompose.yaml\033[0m'\n" "$2"
      if [ -f "$1/compose.yml" ]; then
        wrong_compose_name=1
        printf "%s    └ \033[31m!\033[0m Wrongly named file found : '\033[37mcompose.yml\033[0m'\n" "$2"
      fi
      if [ -f "$1/docker-compose.yml" ]; then
        deprecated_compose=1
        printf "%s    └ \033[31m!\033[0m Deprecated file found : '\033[37mdocker-compose.yml\033[0m'\n" "$2"
      fi
    fi
    printf "\n\033[32mWhat to do\033[0m :\n"
    if [ $missing_env = 1 ]; then
      printf "\n - Follow the install procedure to create a '\033[37m.env\033[0m' file\n"
    fi
    if [ $missing_compose = 1 ]; then
      printf "\n - Follow the install procedure to create a '\033[37mcompose.yaml\033[0m' file\n"
      if [ $wrong_compose_name = 1 ]; then
        printf "\n   If your CRCON starts normally using '\033[37mcompose.yml\033[0m'\n"
        printf "   you should rename this file using this command :\n"
        printf "   \033[36mmv %s/compose.yml %s/compose.yaml\033[0m\n" "$1" "$1"
      fi
      if [ $deprecated_compose = 1 ]; then
        printf "\n   '\033[37mdocker-compose.yml\033[0m' was used by the deprecated (jul. 2023) 'docker-compose' command\n"
        printf "   You should delete it and use a '\033[37mcompose.yaml\033[0m' file\n"
      fi
    fi
    printf "\n"
    exit
  fi
}

clear
printf "┌─────────────────────────────────────────────────────────────────────────────┐\n"
printf "│ Generate a CRCON diagnose file                                              │\n"
printf "└─────────────────────────────────────────────────────────────────────────────┘\n\n"

this_script_dir=$(dirname -- "$( readlink -f -- "$0"; )";)
this_script_name=${0##*/}

# User must have root permissions
if [ "$(id -u)" -ne 0 ]; then
  printf "\033[31mX\033[0m This \033[37m%s\033[0m script must be run with full permissions\n\n" "$this_script_name"
  printf "\033[32mWhat to do\033[0m : you must elevate your permissions using 'sudo' :\n"
  printf "\033[36msudo sh ./%s\033[0m\n\n" "$this_script_name"
  exit
else
  printf "\033[32mV\033[0m You have 'root' permissions.\n"
fi

# Check CRCON folder path
if [ -n "$CRCON_folder_path" ]; then
  printf "\033[32mV\033[0m CRCON folder path has been set in config : \033[33m%s\033[0m\n" "$CRCON_folder_path"
  is_CRCON_configured "$CRCON_folder_path" ""
  crcon_dir="$CRCON_folder_path"
else
  printf "\033[31mX\033[0m You didn't set any CRCON folder path in config\n"
  printf "└ \033[34m?\033[0m Trying to detect a \033[33mhll_rcon_tool\033[0m folder\n"
  detected_dir=$(find / -name "hll_rcon_tool" 2>/dev/null)
  if [ -n "$detected_dir" ]; then
    is_CRCON_configured "$detected_dir" "  "
    crcon_dir="$detected_dir"
  else
    printf "  └ \033[31mX\033[0m No \033[33mhll_rcon_tool\033[0m folder could be found\n"
    printf "    └ \033[34m?\033[0m Trying to detect a CRCON install in current folder\n"
    is_CRCON_configured "$this_script_dir" "      "
    crcon_dir="$this_script_dir"
  fi
fi

# This script has to be in the CRCON folder
if [ ! "$this_script_dir" = "$crcon_dir" ]; then
  printf "\033[31mX\033[0m This script is not located in the CRCON folder\n"
  printf "  Script location : \033[33m%s\033[0m\n" "$this_script_dir"
  printf "  Should be here : \033[33m%s\033[0m\n" "$crcon_dir"
  printf "  \033[32mTrying to fix...\033[0m\n"
  cp "$this_script_dir/$this_script_name" "$crcon_dir"
  if [ -f "$crcon_dir/$this_script_name" ]; then
    printf "  \033[32mV\033[0m \033[37m%s\033[0m has been copied in \033[33m%s\033[0m\n\n" "$this_script_name" "$crcon_dir"
    printf "\033[32mWhat to do\033[0m : enter the CRCON folder and relaunch the script using this command :\n"
    printf "\033[36mrm %s && cd %s && sudo sh ./%s\033[0m\n\n" "$this_script_dir/$this_script_name" "$crcon_dir" "$this_script_name"
    exit
  else
    printf "\033[31mX\033[0m \033[37m%s\033[0m couldn't be copied in \033[33m%s\033[0m\n\n" "$this_script_name" "$crcon_dir"
    printf "\033[32mWhat to do\033[0m : Find your CRCON folder, copy this script in it and relaunch it from there.\n\n"
    exit
  fi
else
  printf "\033[32mV\033[0m This script is located in the CRCON folder\n"
fi

# Script has to be launched from CRCON folder
current_dir=$(pwd | tr -d '\n')
if [ ! "$current_dir" = "$crcon_dir" ]; then
  printf "\033[31mX\033[0m This script should be run from the CRCON folder\n\n"
  printf "\033[32mWhat to do\033[0m : enter the CRCON folder and relaunch the script using this command :\n"
  printf "\033[36mcd %s && sudo sh ./%s\033[0m\n\n" "$crcon_dir" "$this_script_name"
  exit
else
  printf "\033[32mV\033[0m This script has been run from the CRCON folder\n"
fi

printf "\033[32mV Everything's fine\033[0m Let's create this diagnose file !\n\n"

SEPARATOR="\n───────────────────────────────────────────────────────────────────────────────\n"

printf "┌──────────────────────────────────────┐\n" > diagnose.log
printf "│ System resources                     │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ printf "# Number of CPU threads :$SEPARATOR"; nproc; } >> diagnose.log
{ printf "\n\n# Top 20 CPU processes (sort by live usage)$SEPARATOR"; ps aux --sort=-%cpu | head -n 20; } >> diagnose.log
{ printf "\n\n# Top 20 CPU processes (sort by total time)$SEPARATOR"; ps -aux --sort -time | head -n 20; } >> diagnose.log
{ printf "\n\n# RAM :$SEPARATOR"; free -h; } >> diagnose.log
{ printf "\n\n# Disk :$SEPARATOR"; df -h; } >> diagnose.log

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ Operating system                     │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ uname -a; cat /etc/os-release; } >> diagnose.log
apt update > /dev/nul
apt autoclean > /dev/nul
yes | apt autoremove > /dev/nul
{ printf "\n\n# Upgradable packages$SEPARATOR"; apt list --upgradable; } >> diagnose.log

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ Docker versions                      │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ printf "# Docker version$SEPARATOR"; docker version; } >> diagnose.log
{ printf "\n\n# Docker Compose plugin version$SEPARATOR"; docker compose version; } >> diagnose.log

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ CRCON install                        │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ printf "# Current folder$SEPARATOR"; pwd; } >> diagnose.log
{ printf "\n\n# Git status$SEPARATOR"; git status; } >> diagnose.log

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ Docker containers status             │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ printf "# Docker CRCON containers status$SEPARATOR"; docker compose ps; } >> diagnose.log

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ Docker containers logs (common)      │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ printf "# CRCON maintenance$SEPARATOR"; docker compose logs maintenance --tail 200; } >> diagnose.log
{ printf "\n\n# CRCON postgres$SEPARATOR"; docker compose logs postgres --tail 200; } >> diagnose.log
{ printf "\n\n# CRCON redis$SEPARATOR"; docker compose logs redis --tail 200; } >> diagnose.log

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ Docker containers logs (server 1)    │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
if grep -q "^HLL_HOST=[^[:space:]]" .env; then
    { printf "# CRCON backend_1$SEPARATOR"; docker compose logs backend_1 --tail 200; } >> diagnose.log
    { printf "\n\n# CRCON frontend_1$SEPARATOR"; docker compose logs frontend_1 --tail 200; } >> diagnose.log
    { printf "\n\n# CRCON supervisor_1$SEPARATOR"; docker compose logs supervisor_1 --tail 200; } >> diagnose.log
fi

# Docker containers logs - servers 2 to 10
for servernumber in $(seq 2 10); do
  server_name="HLL_HOST_$servernumber"
  if grep -q "^$server_name=[^[:space:]]" .env; then
    printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
    printf "│ Docker containers logs (server %s)    │\n" "$servernumber" >> diagnose.log
    printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
    { printf "# CRCON backend_$servernumber$SEPARATOR"; docker compose logs backend_$servernumber --tail 200; } >> diagnose.log
    { printf "\n\n# CRCON frontend_$servernumber$SEPARATOR"; docker compose logs frontend_$servernumber --tail 200; } >> diagnose.log
    { printf "\n\n# CRCON supervisor_$servernumber$SEPARATOR"; docker compose logs supervisor_$servernumber --tail 200; } >> diagnose.log
  fi
done

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ config/supervisord.conf file(s)      │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
for supervisord_file in config/supervisord*.conf; do
    { printf "# $supervisord_file$SEPARATOR"; cat $supervisord_file; } >> diagnose.log
done

printf "\n\n┌──────────────────────────────────────┐\n" >> diagnose.log
printf "│ config files                         │\n" >> diagnose.log
printf "└──────────────────────────────────────┘\n\n" >> diagnose.log
{ printf "# compose.yaml$SEPARATOR"; cat compose.yaml; } >> diagnose.log
{ printf "\n\n# .env$SEPARATOR"; cat .env; } >> diagnose.log

# Delete usernames and passwords
sed -i 's/\(HLL_DB_PASSWORD=\).*/\1(redacted)/; s/\(HLL_DB_PASSWORD_[0-9]*=\).*/\1(redacted)/' diagnose.log
sed -i 's/\(HLL_DB_URL=postgresql:\/\/.*:\)\(.*\)@\([a-zA-Z0-9._-]*:[0-9]*\/.*\)/\1(redacted)@\3/' diagnose.log
sed -i 's/\(RCONWEB_API_SECRET=\).*/\1(redacted)/; s/\(RCONWEB_API_SECRET_[0-9]*=\).*/\1(redacted)/' diagnose.log
sed -i 's/\(HLL_HOST=\).*/\1(redacted)/; s/\(HLL_HOST_[0-9]*=\).*/\1(redacted)/' diagnose.log
sed -i 's/\(HLL_PASSWORD=\).*/\1(redacted)/; s/\(HLL_PASSWORD_[0-9]*=\).*/\1(redacted)/' diagnose.log
sed -i 's/\(GTX_SERVER_NAME_CHANGE_USERNAME=\).*/\1(redacted)/; s/\(GTX_SERVER_NAME_CHANGE_USERNAME_[0-9]*=\).*/\1(redacted)/' diagnose.log
sed -i 's/\(GTX_SERVER_NAME_CHANGE_PASSWORD=\).*/\1(redacted)/; s/\(GTX_SERVER_NAME_CHANGE_PASSWORD_[0-9]*=\).*/\1(redacted)/' diagnose.log
sed -i "s/\([backend|supervisor]_[0-9]*-[0-9]*  | + '\[' \)\(.*\)\( == '' '\]'\)/\1(redacted)\3/" diagnose.log

clear
printf "┌─────────────────────────────────────────────────────────────────────────────┐\n"
printf "│ Generate a CRCON diagnose file                                              │\n"
printf "└─────────────────────────────────────────────────────────────────────────────┘\n\n"
printf "\033[32mV\033[0m The diagnose file has been created\n\n"
printf "\033[41;37m┌────────────────────────────────────────────────────────────┐\033[0m\n"
printf "\033[41;37m│ NEVER share this file on a public forum or Discord channel │\033[0m\n"
printf "\033[41;37m└────────────────────────────────────────────────────────────┘\033[0m\n"
printf "as it could contain some of your usernames and passwords.\n"
printf "They should have been automatically (redacted), but...\n\n"
printf "\033[32mWhat to do\033[0m :\n"
printf "1. Download \033[33m$crcon_dir\033[0m/\033[37mdiagnose.log\033[0m\n"
printf "2. Open the file in any text editor\n"
printf "3. Delete any sensitive data that could remain (use the search feature)\n"
printf "   - game server RCON credentials (username and password)\n"
printf "   - (GTX only) SFTP credentials (username and password)\n"
printf "   - CRCON database credentials (password)\n"
printf "   - CRCON 'RCONWEB_API_SECRET=' value (passwords scrambler string)\n"
printf "4. share\n\n"
