import subprocess
import sys
import argparse
from ruamel.yaml import YAML
import json
yaml = YAML()

def init_argparse():
  parser = argparse.ArgumentParser(
    prog='sync_ps_ips',
    description='Store Heroku Private Space IP ranges in git and use this tool to sync to Heroku'
  )
  group = parser.add_mutually_exclusive_group(required=True)
  parser.add_argument(
    '-f',
    '--file',
    help='The file to read the IP configuration from.',
    type=str,
    default='sync_ps_ips.yaml'
  )
  group.add_argument(
    '-p',
    '--push',
    help='Push the local config to update Heroku Privace Space IP ranges.',
    action='store_true'
  )

  group.add_argument(
    '--delete-local-config-and-refresh',
    help=('This will first delete the local configuration. '
          'Then it will pull down the Heroku config and save it locally. '
          'Typically, this should only be used once as you will destroy local comments when using it. '
          'SPACE is the name of the private space to pull the config from.'),
    type=str,
    metavar='SPACE',
    dest='space'
  )
  
  return vars(parser.parse_args())

def get_heroku_config(space):
  heroku_cli_response = subprocess.run(['heroku', 'trusted-ips', space, '--json'], capture_output=True, text=True) 
  return json.loads(heroku_cli_response.stdout)

# Get command line args if any are present
args = init_argparse()

# This is our "refresh local config" case
if args['space']:
  heroku_ip_config = get_heroku_config(args['space'])

  with open(args['file'], 'w') as f:
    yaml.dump(heroku_ip_config, f)
  
  # No need to push config back after pulling down
  sys.exit()

if not args['push']:
  # Currently, this condition shouldn't happen, but if future args change,
  # We only want to run after here if told to push
  sys.exit()

# Load local configuration file
with open(args['file']) as f:
  git_ip_config = yaml.load(f)

# Fetch and parse heroku trusted-ips config
heroku_ip_config = get_heroku_config(git_ip_config['space']['name'])

# Loop over Heroku ips and remove any not present in local config
for heroku_rule in heroku_ip_config['rules']:
  for index, git_rule in enumerate(git_ip_config['rules']):
    match = False
    if heroku_rule['source'] == git_rule['source']:
      match = True
      break
  if not match:
    print(f"Deleting rule: {heroku_rule['source']}")
    # Call heroku trusted-ips:remove
    subprocess.run(['heroku', 'trusted-ips:remove', '--space', git_ip_config['space']['name'], heroku_rule['source']], capture_output=True, text=True)

# Loop over local config and add any missing from Heroku
for git_rule in git_ip_config['rules']:
  for heroku_rule in heroku_ip_config['rules']:
    match = False
    if heroku_rule['source'] == git_rule['source']: 
      match = True
      break
  if not match:
    print(f"Adding rule: {git_rule['source']}")
    # Call heroku trusted-ips:add
    subprocess.run(['heroku', 'trusted-ips:add', '--space', git_ip_config['space']['name'], git_rule['source']], capture_output=True, text=True)